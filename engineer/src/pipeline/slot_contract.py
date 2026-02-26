"""Slot execution contracts -- structured input/output for agent slots.

Generates slot-input.yaml with everything an agent needs to execute,
and validates slot outputs after execution completes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pipeline.models import (
    Pipeline,
    PipelineState,
    Slot,
    SlotStatus,
)


@dataclass(frozen=True)
class SlotInput:
    """Structured input contract for an agent filling a slot."""

    slot_id: str
    slot_type: str
    task_objective: str
    context_files: list[str]
    constraints: list[str]
    input_artifacts: dict[str, str]  # name -> path
    required_outputs: list[dict[str, Any]]  # [{name, type, path, validation}]
    kpis: list[str]
    generated_at: str


@dataclass(frozen=True)
class SlotOutputValidation:
    """Result of validating a slot's outputs against its contract."""

    slot_id: str
    valid: bool
    missing_outputs: list[str]
    invalid_outputs: list[str]
    validated_at: str


class SlotContractManager:
    """Manages slot input generation and output validation."""

    def __init__(self, project_root: str, contracts_dir: str | None = None) -> None:
        """
        Args:
            project_root: Root directory for resolving paths.
            contracts_dir: Directory to write slot-input.yaml files.
                Defaults to project_root/state/contracts/.
        """
        self._project_root = Path(project_root)
        if contracts_dir:
            self._contracts_dir = Path(contracts_dir)
        else:
            self._contracts_dir = self._project_root / "state" / "contracts"

    def generate_slot_input(
        self,
        slot: Slot,
        pipeline: Pipeline,
        state: PipelineState,
    ) -> SlotInput:
        """Generate a SlotInput contract for an agent.

        Collects:
        - Task objective and constraints from slot.task
        - Input artifacts from upstream completed slots
        - Required outputs from slot.outputs
        - KPIs from slot.task

        Args:
            slot: The slot to generate input for.
            pipeline: Pipeline definition.
            state: Current pipeline state.

        Returns:
            SlotInput with all information the agent needs.
        """
        now = datetime.now(timezone.utc).isoformat()

        task_objective = ""
        context_files: list[str] = []
        constraints: list[str] = []
        kpis: list[str] = []

        if slot.task:
            task_objective = slot.task.objective
            context_files = list(slot.task.context_files)
            constraints = list(slot.task.constraints)
            kpis = list(slot.task.kpis)

        # Collect input artifacts from upstream slots
        input_artifacts: dict[str, str] = {}
        for inp in slot.inputs:
            src_slot_state = state.slots.get(inp.from_slot)
            if src_slot_state and src_slot_state.status in (
                SlotStatus.COMPLETED, SlotStatus.SKIPPED
            ):
                # Find output path from the pipeline slot definition
                for ps in pipeline.slots:
                    if ps.id == inp.from_slot:
                        for out in ps.outputs:
                            if out.name == inp.artifact:
                                input_artifacts[inp.name] = out.path or ""
                        break

        # Required outputs
        required_outputs: list[dict[str, Any]] = []
        for out in slot.outputs:
            required_outputs.append({
                "name": out.name,
                "type": out.type,
                "path": out.path or "",
                "validation": out.validation,
            })

        return SlotInput(
            slot_id=slot.id,
            slot_type=slot.slot_type,
            task_objective=task_objective,
            context_files=context_files,
            constraints=constraints,
            input_artifacts=input_artifacts,
            required_outputs=required_outputs,
            kpis=kpis,
            generated_at=now,
        )

    def write_slot_input(self, slot_input: SlotInput) -> str:
        """Write a SlotInput to a YAML file.

        File is written to contracts_dir/{slot_id}-input.yaml

        Returns:
            Path to the written file.
        """
        self._contracts_dir.mkdir(parents=True, exist_ok=True)
        path = self._contracts_dir / f"{slot_input.slot_id}-input.yaml"

        data = {
            "slot_id": slot_input.slot_id,
            "slot_type": slot_input.slot_type,
            "task_objective": slot_input.task_objective,
            "context_files": slot_input.context_files,
            "constraints": slot_input.constraints,
            "input_artifacts": slot_input.input_artifacts,
            "required_outputs": slot_input.required_outputs,
            "kpis": slot_input.kpis,
            "generated_at": slot_input.generated_at,
        }

        path.write_text(
            yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        return str(path)

    def validate_slot_output(
        self, slot: Slot
    ) -> SlotOutputValidation:
        """Validate that a slot produced all declared outputs.

        Checks:
        1. Each output with a path: file must exist at project_root/path
        2. Each output without a path: skipped (no validation possible)

        Returns:
            SlotOutputValidation with pass/fail and details.
        """
        now = datetime.now(timezone.utc).isoformat()
        missing: list[str] = []
        invalid: list[str] = []

        for out in slot.outputs:
            if not out.path:
                continue
            full_path = self._project_root / out.path
            if not full_path.exists():
                missing.append(out.name)
            elif out.validation == "schema":
                # Schema validation: check it's valid YAML
                try:
                    yaml.safe_load(full_path.read_text(encoding="utf-8"))
                except Exception:
                    invalid.append(out.name)

        return SlotOutputValidation(
            slot_id=slot.id,
            valid=len(missing) == 0 and len(invalid) == 0,
            missing_outputs=missing,
            invalid_outputs=invalid,
            validated_at=now,
        )
