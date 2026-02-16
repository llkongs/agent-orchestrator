"""
Agent Delivery Protocol - Schema Definitions & Validators

Provides machine-verifiable validation for DELIVERY.yaml and REVIEW.yaml.

Usage:
    from delivery_schema import validate_delivery, validate_review

    errors = validate_delivery("path/to/DELIVERY.yaml")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
    else:
        print("PASS")
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "1.1"

VALID_STATUSES = {"complete", "partial", "blocked"}
VALID_DELIVERABLE_TYPES = {"source", "test", "config", "doc", "script", "schema"}
VALID_LANGUAGES = {
    "python", "yaml", "markdown", "bash", "toml", "json", "dockerfile", "text",
}
VALID_EXPORT_TYPES = {
    "dataclass", "enum", "abc", "function", "interface_impl", "constant",
}
VALID_CHECK_RESULTS = {"pass", "fail", "warn"}
VALID_KNOWN_ISSUE_SEVERITIES = {"P0", "P1", "P2", "P3"}

VALID_VERDICTS = {"pass", "conditional_pass", "fail"}
VALID_ISSUE_SEVERITIES = {"P0", "P1", "P2", "P3"}
VALID_ISSUE_CATEGORIES = {
    "security", "correctness", "performance", "style", "testing",
}

# v1.1: Anti-hallucination constants
VALID_VERIFICATION_STEP_STATUSES = {"success", "failure", "skipped"}
VALID_GOLDEN_DATASET_STATUSES = {"success", "failure"}


# ---------------------------------------------------------------------------
# Dataclass Schemas
# ---------------------------------------------------------------------------

@dataclass
class DeliverableItem:
    path: str
    type: str  # source | test | config | doc | script | schema
    description: str
    checksum: str  # sha256:<hex>
    loc: int
    language: str
    implements: Optional[str] = None


@dataclass
class ExportItem:
    name: str
    type: str  # dataclass | enum | abc | function | interface_impl | constant
    module: str
    description: str


@dataclass
class DependencyItem:
    agent: str
    file: str
    usage: str


@dataclass
class CoverageModule:
    module: str
    stmts: int
    coverage_pct: float


@dataclass
class TestResults:
    runner: str
    command: str
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    coverage_pct: float
    coverage_by_module: list[CoverageModule] = field(default_factory=list)


@dataclass
class QualityCheck:
    check: str
    result: str  # pass | fail | warn
    details: str
    command: Optional[str] = None


@dataclass
class KnownIssue:
    id: str
    severity: str  # P0 | P1 | P2 | P3
    description: str
    planned_fix: Optional[str] = None


@dataclass
class VerificationStep:
    """v1.1: Anti-hallucination - atomic validation step."""
    step: str
    command: str
    status: str  # success | failure | skipped
    stdout_hash: str  # sha256:<hex>
    metrics: Optional[dict] = None
    duration_seconds: Optional[float] = None


@dataclass
class GoldenDataset:
    """v1.1: Anti-hallucination - regression test against known-good outputs."""
    name: str
    description: str
    test_count: int
    passed: int
    failed: int
    status: str  # success | failure
    result_hash: str  # sha256:<hex>


@dataclass
class DeliveryManifest:
    version: str
    agent_id: str
    agent_name: str
    task_id: str
    timestamp: str
    status: str
    deliverables: list[DeliverableItem]
    exports: list[ExportItem]
    dependencies: list[DependencyItem]
    test_results: TestResults
    quality_checks: list[QualityCheck]
    verification_steps: list[VerificationStep]  # v1.1 required
    known_issues: list[KnownIssue] = field(default_factory=list)
    golden_dataset: Optional[list[GoldenDataset]] = None  # v1.1 optional


# --- REVIEW.yaml schema ---

@dataclass
class ReviewTarget:
    agent: str
    delivery: str
    task_id: str


@dataclass
class ReviewIssue:
    id: str
    severity: str  # P0 | P1 | P2 | P3
    category: str  # security | correctness | performance | style | testing
    file: str
    description: str
    expected: str
    actual: str
    fix_required: bool
    line: Optional[int] = None
    fix_deadline: Optional[str] = None


@dataclass
class DeliveryVerification:
    claim: str
    verified: bool
    method: str
    actual_result: str


@dataclass
class AdditionalTest:
    path: str
    test_count: int
    all_passed: bool
    description: Optional[str] = None


@dataclass
class ReviewSummary:
    total_issues: int
    p0_count: int
    p1_count: int
    p2_count: int
    p3_count: int
    blocking: bool
    recommendation: str


@dataclass
class IndependentTestResults:
    """v1.1: Anti-hallucination - QA's own test run results."""
    command: str
    total: int
    passed: int
    failed: int
    coverage_pct: float
    stdout_hash: str  # sha256:<hex>


@dataclass
class IndependentQualityCheck:
    """v1.1: Anti-hallucination - QA's own quality check results."""
    check: str
    command: str
    result: str  # pass | fail | warn
    details: str
    stdout_hash: str  # sha256:<hex>


@dataclass
class IndependentMetrics:
    """v1.1: Anti-hallucination - QA independent reproduction of metrics."""
    test_results: IndependentTestResults
    quality_checks: list[IndependentQualityCheck]


@dataclass
class CrossValidation:
    """v1.1: Anti-hallucination - comparison of Producer vs QA metrics."""
    test_count_match: bool
    test_pass_match: bool
    coverage_delta: float
    coverage_threshold: float
    suspicious: bool
    details: str


@dataclass
class ReviewManifest:
    version: str
    agent_id: str
    agent_name: str
    timestamp: str
    target: ReviewTarget
    delivery_checksum: str  # sha256:<hex> of the DELIVERY.yaml being reviewed
    verdict: str  # pass | conditional_pass | fail
    issues: list[ReviewIssue]
    delivery_verification: list[DeliveryVerification]
    additional_tests: list[AdditionalTest]
    independent_metrics: IndependentMetrics  # v1.1 required
    cross_validation: CrossValidation  # v1.1 required
    summary: ReviewSummary


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require(data: dict, key: str, errors: list[str], prefix: str = "") -> bool:
    """Check that key exists and is not None."""
    label = f"{prefix}.{key}" if prefix else key
    if key not in data or data[key] is None:
        errors.append(f"Missing required field: {label}")
        return False
    return True


def _require_enum(
    data: dict,
    key: str,
    allowed: set[str],
    errors: list[str],
    prefix: str = "",
) -> None:
    label = f"{prefix}.{key}" if prefix else key
    if _require(data, key, errors, prefix):
        val = data[key]
        if val not in allowed:
            errors.append(
                f"Invalid value for {label}: '{val}' "
                f"(allowed: {sorted(allowed)})"
            )


def _require_type(
    data: dict,
    key: str,
    expected_type: type,
    errors: list[str],
    prefix: str = "",
) -> None:
    label = f"{prefix}.{key}" if prefix else key
    if _require(data, key, errors, prefix):
        if not isinstance(data[key], expected_type):
            errors.append(
                f"Field {label} must be {expected_type.__name__}, "
                f"got {type(data[key]).__name__}"
            )


def _validate_iso_timestamp(value: str, field_name: str, errors: list[str]) -> None:
    """Validate ISO 8601 timestamp format."""
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        datetime.fromisoformat(value)
    except (ValueError, AttributeError):
        errors.append(f"Invalid ISO 8601 timestamp in {field_name}: '{value}'")


def _validate_checksum(checksum: str, field_name: str, errors: list[str]) -> None:
    """Validate checksum format is sha256:<64 hex chars>."""
    if not isinstance(checksum, str):
        errors.append(f"{field_name}: checksum must be string")
        return
    if not checksum.startswith("sha256:"):
        errors.append(f"{field_name}: checksum must start with 'sha256:'")
        return
    hex_part = checksum[7:]
    if len(hex_part) != 64:
        errors.append(f"{field_name}: sha256 hash must be 64 hex characters")
        return
    try:
        int(hex_part, 16)
    except ValueError:
        errors.append(f"{field_name}: invalid hex in checksum")


# ---------------------------------------------------------------------------
# DELIVERY.yaml validation
# ---------------------------------------------------------------------------

def validate_delivery(
    yaml_path: str,
    project_root: Optional[str] = None,
    verify_checksums: bool = False,
) -> list[str]:
    """Validate a DELIVERY.yaml file against the protocol schema.

    Args:
        yaml_path: Path to the DELIVERY.yaml file.
        project_root: Project root directory for file existence and checksum
                      verification. If None, file checks are skipped.
        verify_checksums: If True and project_root is set, recompute and
                          compare checksums of every deliverable file.

    Returns:
        List of error strings. Empty list = valid.
    """
    errors: list[str] = []

    # --- Load YAML ---
    path = Path(yaml_path)
    if not path.exists():
        return [f"File not found: {yaml_path}"]

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["DELIVERY.yaml must be a YAML mapping"]

    # --- Top-level required fields ---
    for key in ("version", "agent_id", "agent_name", "task_id", "timestamp", "status"):
        _require(data, key, errors)

    if data.get("version") and data["version"] != PROTOCOL_VERSION:
        errors.append(
            f"Unsupported protocol version: '{data['version']}' "
            f"(expected '{PROTOCOL_VERSION}')"
        )

    _validate_iso_timestamp(data.get("timestamp", ""), "timestamp", errors)
    _require_enum(data, "status", VALID_STATUSES, errors)

    # --- deliverables ---
    deliverables = data.get("deliverables")
    if not deliverables or not isinstance(deliverables, list):
        errors.append("Missing or empty required field: deliverables")
    else:
        for i, item in enumerate(deliverables):
            pfx = f"deliverables[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "path", errors, pfx)
            _require_enum(item, "type", VALID_DELIVERABLE_TYPES, errors, pfx)
            _require(item, "description", errors, pfx)
            _require_type(item, "loc", int, errors, pfx)
            _require_enum(item, "language", VALID_LANGUAGES, errors, pfx)

            if "checksum" in item and item["checksum"] is not None:
                _validate_checksum(item["checksum"], pfx, errors)
            else:
                errors.append(f"Missing required field: {pfx}.checksum")

            # File existence check
            if project_root and item.get("path"):
                file_path = Path(project_root) / item["path"]
                if not file_path.exists():
                    errors.append(f"{pfx}: file not found: {file_path}")
                elif verify_checksums and item.get("checksum"):
                    actual = _compute_sha256(str(file_path))
                    expected = item["checksum"]
                    if actual != expected:
                        errors.append(
                            f"{pfx}: checksum mismatch for {item['path']}: "
                            f"expected {expected}, got {actual}"
                        )

    # --- exports ---
    exports = data.get("exports")
    if exports is None:
        errors.append("Missing required field: exports")
    elif isinstance(exports, list):
        for i, item in enumerate(exports):
            pfx = f"exports[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "name", errors, pfx)
            _require_enum(item, "type", VALID_EXPORT_TYPES, errors, pfx)
            _require(item, "module", errors, pfx)
            _require(item, "description", errors, pfx)

    # --- dependencies ---
    deps = data.get("dependencies")
    if deps is None:
        errors.append("Missing required field: dependencies")
    elif isinstance(deps, list):
        for i, item in enumerate(deps):
            pfx = f"dependencies[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "agent", errors, pfx)
            _require(item, "file", errors, pfx)
            _require(item, "usage", errors, pfx)

    # --- test_results ---
    tr = data.get("test_results")
    if not tr or not isinstance(tr, dict):
        errors.append("Missing or invalid required field: test_results")
    else:
        pfx = "test_results"
        _require(tr, "runner", errors, pfx)
        _require(tr, "command", errors, pfx)
        for int_field in ("total", "passed", "failed", "skipped", "errors"):
            _require_type(tr, int_field, int, errors, pfx)
        _require(tr, "coverage_pct", errors, pfx)

        # Consistency: total == passed + failed + skipped + errors
        if all(isinstance(tr.get(k), int) for k in ("total", "passed", "failed", "skipped", "errors")):
            computed = tr["passed"] + tr["failed"] + tr["skipped"] + tr["errors"]
            if tr["total"] != computed:
                errors.append(
                    f"test_results: total ({tr['total']}) != "
                    f"passed + failed + skipped + errors ({computed})"
                )

        # coverage_by_module
        cbm = tr.get("coverage_by_module")
        if cbm and isinstance(cbm, list):
            for i, mod in enumerate(cbm):
                mpfx = f"test_results.coverage_by_module[{i}]"
                if not isinstance(mod, dict):
                    errors.append(f"{mpfx}: must be a mapping")
                    continue
                _require(mod, "module", errors, mpfx)
                _require_type(mod, "stmts", int, errors, mpfx)
                _require(mod, "coverage_pct", errors, mpfx)

    # --- quality_checks ---
    qc = data.get("quality_checks")
    if qc is None:
        errors.append("Missing required field: quality_checks")
    elif isinstance(qc, list):
        for i, item in enumerate(qc):
            pfx = f"quality_checks[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "check", errors, pfx)
            _require_enum(item, "result", VALID_CHECK_RESULTS, errors, pfx)
            _require(item, "details", errors, pfx)

    # --- known_issues (optional but validated if present) ---
    ki = data.get("known_issues")
    if ki and isinstance(ki, list):
        for i, item in enumerate(ki):
            pfx = f"known_issues[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "id", errors, pfx)
            _require_enum(item, "severity", VALID_KNOWN_ISSUE_SEVERITIES, errors, pfx)
            _require(item, "description", errors, pfx)

    # --- verification_steps (v1.1 required - anti-hallucination) ---
    vs = data.get("verification_steps")
    if not vs or not isinstance(vs, list):
        errors.append("Missing or empty required field: verification_steps")
    else:
        has_failure = False
        pytest_step_passed = None
        for i, item in enumerate(vs):
            pfx = f"verification_steps[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "step", errors, pfx)
            _require(item, "command", errors, pfx)
            _require_enum(
                item, "status", VALID_VERIFICATION_STEP_STATUSES, errors, pfx,
            )

            # stdout_hash validation
            if "stdout_hash" in item and item["stdout_hash"] is not None:
                _validate_checksum(item["stdout_hash"], f"{pfx}.stdout_hash", errors)
            else:
                errors.append(f"Missing required field: {pfx}.stdout_hash")

            if item.get("status") == "failure":
                has_failure = True

            # Track pytest step metrics for cross-check with test_results
            if item.get("step") == "pytest" and isinstance(item.get("metrics"), dict):
                pytest_step_passed = item["metrics"].get("tests_passed")

        # Consistency: any failure step -> status cannot be "complete"
        status = data.get("status")
        if has_failure and status == "complete":
            errors.append(
                "verification_steps contains failure but status is 'complete'"
            )

        # Consistency: pytest step metrics vs test_results
        if (
            pytest_step_passed is not None
            and isinstance(tr, dict)
            and isinstance(tr.get("passed"), int)
        ):
            if pytest_step_passed != tr["passed"]:
                errors.append(
                    f"verification_steps pytest metrics mismatch with test_results: "
                    f"step.metrics.tests_passed={pytest_step_passed} vs "
                    f"test_results.passed={tr['passed']}"
                )

    # --- golden_dataset (v1.1 optional - anti-hallucination) ---
    gd = data.get("golden_dataset")
    if gd is not None:
        if not isinstance(gd, list):
            errors.append("golden_dataset must be a list")
        else:
            gd_has_failure = False
            for i, item in enumerate(gd):
                pfx = f"golden_dataset[{i}]"
                if not isinstance(item, dict):
                    errors.append(f"{pfx}: must be a mapping")
                    continue
                _require(item, "name", errors, pfx)
                _require(item, "description", errors, pfx)
                _require_type(item, "test_count", int, errors, pfx)
                _require_type(item, "passed", int, errors, pfx)
                _require_type(item, "failed", int, errors, pfx)
                _require_enum(
                    item, "status", VALID_GOLDEN_DATASET_STATUSES, errors, pfx,
                )

                # result_hash validation
                if "result_hash" in item and item["result_hash"] is not None:
                    _validate_checksum(
                        item["result_hash"], f"{pfx}.result_hash", errors,
                    )
                else:
                    errors.append(f"Missing required field: {pfx}.result_hash")

                # Consistency: passed + failed == test_count
                if (
                    isinstance(item.get("test_count"), int)
                    and isinstance(item.get("passed"), int)
                    and isinstance(item.get("failed"), int)
                ):
                    computed = item["passed"] + item["failed"]
                    if item["test_count"] != computed:
                        errors.append(
                            f"{pfx}: test_count ({item['test_count']}) != "
                            f"passed + failed ({computed})"
                        )

                # Consistency: failed > 0 -> status must be failure
                if (
                    isinstance(item.get("failed"), int)
                    and item["failed"] > 0
                    and item.get("status") == "success"
                ):
                    errors.append(
                        f"{pfx}: failed > 0 but status is 'success' "
                        f"(must be 'failure')"
                    )

                if item.get("status") == "failure":
                    gd_has_failure = True

            # Consistency: golden_dataset failure -> status cannot be "complete"
            status = data.get("status")
            if gd_has_failure and status == "complete":
                errors.append(
                    "golden_dataset contains failure but status is 'complete'"
                )

    return errors


# ---------------------------------------------------------------------------
# REVIEW.yaml validation
# ---------------------------------------------------------------------------

def validate_review(yaml_path: str) -> list[str]:
    """Validate a REVIEW.yaml file against the protocol schema.

    Args:
        yaml_path: Path to the REVIEW.yaml file.

    Returns:
        List of error strings. Empty list = valid.
    """
    errors: list[str] = []

    path = Path(yaml_path)
    if not path.exists():
        return [f"File not found: {yaml_path}"]

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["REVIEW.yaml must be a YAML mapping"]

    # --- Top-level ---
    for key in ("version", "agent_id", "agent_name", "timestamp"):
        _require(data, key, errors)

    _validate_iso_timestamp(data.get("timestamp", ""), "timestamp", errors)
    _require_enum(data, "verdict", VALID_VERDICTS, errors)

    # --- delivery_checksum ---
    if "delivery_checksum" in data and data["delivery_checksum"] is not None:
        _validate_checksum(data["delivery_checksum"], "delivery_checksum", errors)
    else:
        errors.append("Missing required field: delivery_checksum")

    # --- target ---
    target = data.get("target")
    if not target or not isinstance(target, dict):
        errors.append("Missing or invalid required field: target")
    else:
        _require(target, "agent", errors, "target")
        _require(target, "delivery", errors, "target")
        _require(target, "task_id", errors, "target")

    # --- issues ---
    issues = data.get("issues")
    if issues is None:
        errors.append("Missing required field: issues")
    elif isinstance(issues, list):
        p0_count = 0
        p1_count = 0
        p2_count = 0
        max_severity = None  # track highest severity found
        has_p1_blocking = False
        for i, item in enumerate(issues):
            pfx = f"issues[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "id", errors, pfx)
            _require_enum(item, "severity", VALID_ISSUE_SEVERITIES, errors, pfx)
            _require_enum(item, "category", VALID_ISSUE_CATEGORIES, errors, pfx)
            _require(item, "file", errors, pfx)
            _require(item, "description", errors, pfx)
            _require(item, "expected", errors, pfx)
            _require(item, "actual", errors, pfx)
            _require_type(item, "fix_required", bool, errors, pfx)

            sev = item.get("severity")
            if sev == "P0":
                p0_count += 1
            elif sev == "P1":
                p1_count += 1
                if item.get("fix_required") is True:
                    has_p1_blocking = True
            elif sev == "P2":
                p2_count += 1

            # Track max severity (P0 > P1 > P2 > P3)
            sev_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(sev)
            if sev_rank is not None:
                if max_severity is None or sev_rank < max_severity:
                    max_severity = sev_rank

        # --- Verdict decision table enforcement ---
        # P0 exists            -> must be fail
        # P1 + fix_required    -> must be fail
        # P1 (no fix_required) -> must be conditional_pass
        # max severity P2      -> must be conditional_pass
        # max severity P3 or none -> must be pass
        verdict = data.get("verdict")
        if verdict in VALID_VERDICTS and max_severity is not None:
            if p0_count > 0 and verdict != "fail":
                errors.append(
                    f"Verdict decision table: P0 issues exist "
                    f"({p0_count}) but verdict is '{verdict}' (must be 'fail')"
                )
            elif p0_count == 0 and has_p1_blocking and verdict != "fail":
                errors.append(
                    f"Verdict decision table: P1 issues with fix_required=true "
                    f"but verdict is '{verdict}' (must be 'fail')"
                )
            elif (
                p0_count == 0
                and not has_p1_blocking
                and p1_count > 0
                and verdict not in ("conditional_pass", "fail")
            ):
                errors.append(
                    f"Verdict decision table: P1 issues present "
                    f"but verdict is '{verdict}' (must be 'conditional_pass')"
                )
            elif (
                p0_count == 0
                and p1_count == 0
                and p2_count > 0
                and verdict not in ("conditional_pass", "pass")
            ):
                errors.append(
                    f"Verdict decision table: max severity is P2 "
                    f"but verdict is '{verdict}' (must be 'conditional_pass' or 'pass')"
                )
        elif verdict in VALID_VERDICTS and max_severity is None:
            # No issues at all
            if len(issues) == 0 and verdict != "pass":
                errors.append(
                    f"Verdict decision table: no issues found "
                    f"but verdict is '{verdict}' (must be 'pass')"
                )

    # --- delivery_verification ---
    dv = data.get("delivery_verification")
    if dv is None:
        errors.append("Missing required field: delivery_verification")
    elif isinstance(dv, list):
        for i, item in enumerate(dv):
            pfx = f"delivery_verification[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "claim", errors, pfx)
            _require_type(item, "verified", bool, errors, pfx)
            _require(item, "method", errors, pfx)
            _require(item, "actual_result", errors, pfx)

    # --- additional_tests ---
    at = data.get("additional_tests")
    if at is None:
        errors.append("Missing required field: additional_tests")
    elif isinstance(at, list):
        for i, item in enumerate(at):
            pfx = f"additional_tests[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{pfx}: must be a mapping")
                continue
            _require(item, "path", errors, pfx)
            _require_type(item, "test_count", int, errors, pfx)
            _require_type(item, "all_passed", bool, errors, pfx)

    # --- summary ---
    summary = data.get("summary")
    if not summary or not isinstance(summary, dict):
        errors.append("Missing or invalid required field: summary")
    else:
        pfx = "summary"
        for int_field in ("total_issues", "p0_count", "p1_count", "p2_count", "p3_count"):
            _require_type(summary, int_field, int, errors, pfx)
        _require_type(summary, "blocking", bool, errors, pfx)
        _require(summary, "recommendation", errors, pfx)

        # Consistency: total_issues == p0 + p1 + p2 + p3
        counts = [summary.get(k) for k in ("p0_count", "p1_count", "p2_count", "p3_count")]
        if all(isinstance(c, int) for c in counts):
            computed = sum(counts)
            total = summary.get("total_issues")
            if isinstance(total, int) and total != computed:
                errors.append(
                    f"summary: total_issues ({total}) != "
                    f"p0 + p1 + p2 + p3 ({computed})"
                )

        # Consistency: blocking should match issues
        if isinstance(issues, list):
            actual_blocking = any(
                isinstance(it, dict) and it.get("fix_required") is True
                for it in issues
            )
            if isinstance(summary.get("blocking"), bool):
                if summary["blocking"] != actual_blocking:
                    errors.append(
                        f"summary.blocking ({summary['blocking']}) does not match "
                        f"issues fix_required state ({actual_blocking})"
                    )

    # --- independent_metrics (v1.1 required - anti-hallucination) ---
    im = data.get("independent_metrics")
    if not im or not isinstance(im, dict):
        errors.append("Missing or invalid required field: independent_metrics")
    else:
        # test_results sub-field
        im_tr = im.get("test_results")
        if not im_tr or not isinstance(im_tr, dict):
            errors.append(
                "Missing or invalid required field: "
                "independent_metrics.test_results"
            )
        else:
            im_pfx = "independent_metrics.test_results"
            _require(im_tr, "command", errors, im_pfx)
            _require_type(im_tr, "total", int, errors, im_pfx)
            _require_type(im_tr, "passed", int, errors, im_pfx)
            _require_type(im_tr, "failed", int, errors, im_pfx)
            _require(im_tr, "coverage_pct", errors, im_pfx)
            if "stdout_hash" in im_tr and im_tr["stdout_hash"] is not None:
                _validate_checksum(
                    im_tr["stdout_hash"],
                    f"{im_pfx}.stdout_hash",
                    errors,
                )
            else:
                errors.append(f"Missing required field: {im_pfx}.stdout_hash")

        # quality_checks sub-field
        im_qc = im.get("quality_checks")
        if im_qc is None:
            errors.append(
                "Missing required field: independent_metrics.quality_checks"
            )
        elif isinstance(im_qc, list):
            for i, item in enumerate(im_qc):
                pfx = f"independent_metrics.quality_checks[{i}]"
                if not isinstance(item, dict):
                    errors.append(f"{pfx}: must be a mapping")
                    continue
                _require(item, "check", errors, pfx)
                _require(item, "command", errors, pfx)
                _require_enum(item, "result", VALID_CHECK_RESULTS, errors, pfx)
                _require(item, "details", errors, pfx)
                if "stdout_hash" in item and item["stdout_hash"] is not None:
                    _validate_checksum(
                        item["stdout_hash"], f"{pfx}.stdout_hash", errors,
                    )
                else:
                    errors.append(f"Missing required field: {pfx}.stdout_hash")

    # --- cross_validation (v1.1 required - anti-hallucination) ---
    cv = data.get("cross_validation")
    if not cv or not isinstance(cv, dict):
        errors.append("Missing or invalid required field: cross_validation")
    else:
        cv_pfx = "cross_validation"
        _require_type(cv, "test_count_match", bool, errors, cv_pfx)
        _require_type(cv, "test_pass_match", bool, errors, cv_pfx)
        _require(cv, "coverage_delta", errors, cv_pfx)
        _require(cv, "coverage_threshold", errors, cv_pfx)
        _require_type(cv, "suspicious", bool, errors, cv_pfx)
        _require(cv, "details", errors, cv_pfx)

        # Consistency: suspicious must be true if any match fails or delta exceeds threshold
        if isinstance(cv.get("suspicious"), bool):
            should_be_suspicious = False

            if cv.get("test_count_match") is False:
                should_be_suspicious = True
            if cv.get("test_pass_match") is False:
                should_be_suspicious = True

            cov_delta = cv.get("coverage_delta")
            cov_thresh = cv.get("coverage_threshold")
            if (
                isinstance(cov_delta, (int, float))
                and isinstance(cov_thresh, (int, float))
                and abs(cov_delta) > cov_thresh
            ):
                should_be_suspicious = True

            if should_be_suspicious and not cv["suspicious"]:
                errors.append(
                    "cross_validation: suspicious should be true "
                    "(test count/pass mismatch or coverage delta exceeds threshold)"
                )

        # Consistency: suspicious == true -> verdict cannot be "pass"
        verdict = data.get("verdict")
        if (
            isinstance(cv.get("suspicious"), bool)
            and cv["suspicious"] is True
            and verdict == "pass"
        ):
            errors.append(
                "cross_validation suspicious but verdict is 'pass' "
                "(must be 'conditional_pass' or 'fail')"
            )

    return errors


# ---------------------------------------------------------------------------
# Utility: compute checksum
# ---------------------------------------------------------------------------

def _compute_sha256(file_path: str) -> str:
    """Compute sha256:<hex> for a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def compute_checksum(file_path: str) -> str:
    """Public helper to compute a checksum for use in DELIVERY.yaml.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        String in format "sha256:<64 hex chars>".
    """
    return _compute_sha256(file_path)


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def _main() -> None:
    import sys

    if len(sys.argv) < 3:
        print("Usage: python delivery-schema.py <delivery|review> <path.yaml> [project_root]")
        print("       python delivery-schema.py checksum <file_path>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "delivery":
        yaml_path = sys.argv[2]
        project_root = sys.argv[3] if len(sys.argv) > 3 else None
        verify = "--verify-checksums" in sys.argv
        errors = validate_delivery(yaml_path, project_root, verify)
    elif cmd == "review":
        yaml_path = sys.argv[2]
        errors = validate_review(yaml_path)
    elif cmd == "checksum":
        file_path = sys.argv[2]
        print(compute_checksum(file_path))
        sys.exit(0)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    if errors:
        print(f"FAIL: {len(errors)} validation error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS: Schema validation successful")
        sys.exit(0)


if __name__ == "__main__":
    _main()
