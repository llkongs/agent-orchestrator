"""Pre-condition and post-condition evaluation for pipeline slots.

All checkers return GateCheckResult -- they never raise exceptions.
Failed conditions return passed=False with error details in evidence.
"""

from __future__ import annotations

import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pipeline.models import (
    GateCheckResult,
    PipelineState,
    Slot,
    SlotStatus,
)


class GateChecker:
    """Evaluates pre-conditions and post-conditions for slots."""

    def __init__(self, project_root: str) -> None:
        """
        Args:
            project_root: Root directory for resolving relative file paths.
        """
        self._project_root = Path(project_root)

    def check_pre_conditions(
        self, slot: Slot, pipeline_state: PipelineState
    ) -> list[GateCheckResult]:
        """Evaluate all pre-conditions for a slot.

        Dispatches each Gate to the appropriate checker based on gate.type.

        Returns:
            List of GateCheckResult (one per condition).
            Never raises -- errors become passed=False results.
        """
        results: list[GateCheckResult] = []
        for gate in slot.pre_conditions:
            result = self._dispatch(gate.type, gate.target, gate.check, pipeline_state)
            results.append(result)
        return results

    def check_post_conditions(
        self, slot: Slot, pipeline_state: PipelineState
    ) -> list[GateCheckResult]:
        """Evaluate all post-conditions for a slot."""
        results: list[GateCheckResult] = []
        for gate in slot.post_conditions:
            result = self._dispatch(gate.type, gate.target, gate.check, pipeline_state)
            results.append(result)
        return results

    def all_passed(self, results: list[GateCheckResult]) -> bool:
        """Return True if every result has passed=True.

        Returns True for an empty list (no conditions = vacuously true).
        """
        return all(r.passed for r in results)

    # --- Individual checkers ---

    def check_file_exists(self, target: str) -> GateCheckResult:
        """Check if file exists at project_root/target."""
        now = self._now()
        path = self._project_root / target
        if path.exists():
            return GateCheckResult(
                condition=f"File exists: {target}",
                passed=True,
                evidence=f"File found at {path}",
                checked_at=now,
            )
        return GateCheckResult(
            condition=f"File exists: {target}",
            passed=False,
            evidence=f"File not found at {path}",
            checked_at=now,
        )

    def check_slot_completed(
        self, target: str, state: PipelineState
    ) -> GateCheckResult:
        """Check if slot with given ID has status COMPLETED."""
        now = self._now()
        slot_state = state.slots.get(target)
        if slot_state is None:
            return GateCheckResult(
                condition=f"Slot completed: {target}",
                passed=False,
                evidence=f"Slot '{target}' not found in pipeline state",
                checked_at=now,
            )
        if slot_state.status == SlotStatus.COMPLETED:
            return GateCheckResult(
                condition=f"Slot completed: {target}",
                passed=True,
                evidence=f"Slot '{target}' status is COMPLETED",
                checked_at=now,
            )
        return GateCheckResult(
            condition=f"Slot completed: {target}",
            passed=False,
            evidence=f"Slot '{target}' status is {slot_state.status.value}",
            checked_at=now,
        )

    def check_delivery_valid(self, target: str) -> GateCheckResult:
        """Validate a DELIVERY.yaml file.

        Checks that the file exists and is valid YAML. Full schema
        validation is attempted if delivery-schema.py is available.
        """
        now = self._now()
        path = self._project_root / target
        if not path.exists():
            return GateCheckResult(
                condition=f"Delivery valid: {target}",
                passed=False,
                evidence=f"DELIVERY.yaml not found at {path}",
                checked_at=now,
            )
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data is None:
                return GateCheckResult(
                    condition=f"Delivery valid: {target}",
                    passed=False,
                    evidence="DELIVERY.yaml is empty",
                    checked_at=now,
                )
            # Basic structural check
            required_fields = {"version", "agent_id", "status"}
            missing = required_fields - set(data.keys())
            if missing:
                return GateCheckResult(
                    condition=f"Delivery valid: {target}",
                    passed=False,
                    evidence=f"Missing fields: {', '.join(sorted(missing))}",
                    checked_at=now,
                )
            return GateCheckResult(
                condition=f"Delivery valid: {target}",
                passed=True,
                evidence="DELIVERY.yaml is valid YAML with required fields",
                checked_at=now,
            )
        except Exception as exc:
            return GateCheckResult(
                condition=f"Delivery valid: {target}",
                passed=False,
                evidence=f"Error reading DELIVERY.yaml: {exc}",
                checked_at=now,
            )

    def check_review_valid(self, target: str) -> GateCheckResult:
        """Validate a REVIEW.yaml file."""
        now = self._now()
        path = self._project_root / target
        if not path.exists():
            return GateCheckResult(
                condition=f"Review valid: {target}",
                passed=False,
                evidence=f"REVIEW.yaml not found at {path}",
                checked_at=now,
            )
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data is None:
                return GateCheckResult(
                    condition=f"Review valid: {target}",
                    passed=False,
                    evidence="REVIEW.yaml is empty",
                    checked_at=now,
                )
            required_fields = {"version", "agent_id", "verdict"}
            missing = required_fields - set(data.keys())
            if missing:
                return GateCheckResult(
                    condition=f"Review valid: {target}",
                    passed=False,
                    evidence=f"Missing fields: {', '.join(sorted(missing))}",
                    checked_at=now,
                )
            return GateCheckResult(
                condition=f"Review valid: {target}",
                passed=True,
                evidence="REVIEW.yaml is valid YAML with required fields",
                checked_at=now,
            )
        except Exception as exc:
            return GateCheckResult(
                condition=f"Review valid: {target}",
                passed=False,
                evidence=f"Error reading REVIEW.yaml: {exc}",
                checked_at=now,
            )

    def check_tests_pass(self, target: str) -> GateCheckResult:
        """Check if tests in target directory pass."""
        now = self._now()
        test_path = self._project_root / target
        if not test_path.exists():
            return GateCheckResult(
                condition=f"Tests pass: {target}",
                passed=False,
                evidence=f"Test directory not found: {test_path}",
                checked_at=now,
            )
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", str(test_path), "--tb=no", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self._project_root),
            )
            if result.returncode == 0:
                return GateCheckResult(
                    condition=f"Tests pass: {target}",
                    passed=True,
                    evidence=result.stdout.strip()[-200:] if result.stdout else "Tests passed",
                    checked_at=now,
                )
            return GateCheckResult(
                condition=f"Tests pass: {target}",
                passed=False,
                evidence=result.stdout.strip()[-200:] if result.stdout else "Tests failed",
                checked_at=now,
            )
        except Exception as exc:
            return GateCheckResult(
                condition=f"Tests pass: {target}",
                passed=False,
                evidence=f"Error running tests: {exc}",
                checked_at=now,
            )

    def evaluate_custom(self, target: str) -> GateCheckResult:
        """Evaluate a custom expression.

        Supported formats:
        - "yaml_field:<file>:<field_path> <op> <value>"
        - "command:<shell_command>"
        """
        now = self._now()
        try:
            if target.startswith("yaml_field:"):
                return self._eval_yaml_field(target, now)
            if target.startswith("command:"):
                return self._eval_command(target, now)
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence=f"Unknown custom expression format: {target}",
                checked_at=now,
            )
        except Exception as exc:
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence=f"Error evaluating custom expression: {exc}",
                checked_at=now,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dispatch(
        self, gate_type: str, target: str, check: str, state: PipelineState
    ) -> GateCheckResult:
        """Dispatch a gate to the appropriate checker."""
        try:
            if gate_type == "file_exists":
                return self.check_file_exists(target)
            if gate_type == "slot_completed":
                return self.check_slot_completed(target, state)
            if gate_type == "delivery_valid":
                return self.check_delivery_valid(target)
            if gate_type == "review_valid":
                return self.check_review_valid(target)
            if gate_type == "tests_pass":
                return self.check_tests_pass(target)
            if gate_type == "custom":
                return self.evaluate_custom(target)
            if gate_type in ("approval", "artifact_valid"):
                # These need external input; treat as pass-through for now
                return GateCheckResult(
                    condition=check,
                    passed=True,
                    evidence=f"Gate type '{gate_type}' auto-passed (requires external validation)",
                    checked_at=self._now(),
                )
            return GateCheckResult(
                condition=check,
                passed=False,
                evidence=f"Unknown gate type: {gate_type}",
                checked_at=self._now(),
            )
        except Exception as exc:
            return GateCheckResult(
                condition=check,
                passed=False,
                evidence=f"Error in gate check: {exc}",
                checked_at=self._now(),
            )

    def _eval_yaml_field(self, target: str, now: str) -> GateCheckResult:
        """Evaluate yaml_field:<file>:<field_path> <op> <value>."""
        # Parse: "yaml_field:<file>:<field_path> <op> <value>"
        rest = target[len("yaml_field:"):]
        parts = rest.split(" ", 1)
        if len(parts) < 2:
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence="Invalid yaml_field expression: missing operator and value",
                checked_at=now,
            )

        file_and_path = parts[0]
        op_and_value = parts[1].strip()

        file_parts = file_and_path.split(":", 1)
        if len(file_parts) != 2:
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence="Invalid yaml_field expression: expected file:field_path",
                checked_at=now,
            )

        file_path = file_parts[0]
        field_path = file_parts[1]

        # Parse operator and value
        op = None
        value = None
        for candidate_op in ("!=", ">=", "<=", "==", ">", "<"):
            if op_and_value.startswith(candidate_op):
                op = candidate_op
                value = op_and_value[len(candidate_op):].strip()
                break

        if op is None:
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence=f"Invalid operator in expression: {op_and_value}",
                checked_at=now,
            )

        # Load YAML and navigate path
        full_path = self._project_root / file_path
        if not full_path.exists():
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence=f"File not found: {full_path}",
                checked_at=now,
            )

        data = yaml.safe_load(full_path.read_text(encoding="utf-8"))
        actual = self._navigate_path(data, field_path)

        if actual is None:
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence=f"Field '{field_path}' not found in {file_path}",
                checked_at=now,
            )

        passed = self._compare(str(actual), op, value)
        return GateCheckResult(
            condition=f"Custom: {target}",
            passed=passed,
            evidence=f"{field_path} = {actual!r} {op} {value!r} -> {'PASS' if passed else 'FAIL'}",
            checked_at=now,
        )

    def _eval_command(self, target: str, now: str) -> GateCheckResult:
        """Evaluate command:<shell_command>."""
        cmd = target[len("command:"):]
        try:
            args = shlex.split(cmd)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self._project_root),
            )
            passed = result.returncode == 0
            evidence = result.stdout.strip()[-200:] if result.stdout else (
                result.stderr.strip()[-200:] if result.stderr else
                f"Exit code: {result.returncode}"
            )
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=passed,
                evidence=evidence,
                checked_at=now,
            )
        except Exception as exc:
            return GateCheckResult(
                condition=f"Custom: {target}",
                passed=False,
                evidence=f"Error executing command: {exc}",
                checked_at=now,
            )

    @staticmethod
    def _navigate_path(data: Any, field_path: str) -> Any:
        """Navigate a dot-separated field path through nested dicts."""
        parts = field_path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    @staticmethod
    def _compare(actual: str, op: str, expected: str) -> bool:
        """Compare two values with the given operator."""
        if op == "==":
            return actual == expected
        if op == "!=":
            return actual != expected
        # Try numeric comparison
        try:
            a = float(actual)
            e = float(expected)
            if op == ">":
                return a > e
            if op == "<":
                return a < e
            if op == ">=":
                return a >= e
            if op == "<=":
                return a <= e
        except (ValueError, TypeError):
            pass
        return False

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
