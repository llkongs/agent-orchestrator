"""Data models for the pipeline engine.

Pure data containers using dataclasses and StrEnum. No logic beyond
construction and serialization. All other modules depend on this module;
this module has zero internal dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SlotStatus(StrEnum):
    """Runtime status of a slot in the pipeline."""

    PENDING = "pending"
    BLOCKED = "blocked"
    READY = "ready"
    PRE_CHECK = "pre_check"
    IN_PROGRESS = "in_progress"
    POST_CHECK = "post_check"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class PipelineStatus(StrEnum):
    """Runtime status of the entire pipeline."""

    LOADED = "loaded"
    VALIDATED = "validated"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class ArtifactType(StrEnum):
    """Classification of artifacts produced by slots."""

    DESIGN_DOC = "design_doc"
    CODE = "code"
    TEST_CODE = "test_code"
    DELIVERY_YAML = "delivery_yaml"
    REVIEW_YAML = "review_yaml"
    CONFIG = "config"
    RESEARCH = "research"
    AUDIT_REPORT = "audit_report"
    AGENT_PROMPT = "agent_prompt"
    APPROVAL = "approval"
    DEPLOYMENT = "deployment"
    SLOT_OUTPUT = "slot_output"


class ConditionType(StrEnum):
    """Types of pre-conditions and post-conditions on slots."""

    FILE_EXISTS = "file_exists"
    SLOT_COMPLETED = "slot_completed"
    APPROVAL = "approval"
    ARTIFACT_VALID = "artifact_valid"
    DELIVERY_VALID = "delivery_valid"
    REVIEW_VALID = "review_valid"
    TESTS_PASS = "tests_pass"
    CUSTOM = "custom"


class ValidationLevel(StrEnum):
    """How strictly an artifact should be validated."""

    CHECKSUM = "checksum"
    SCHEMA = "schema"
    EXISTS = "exists"
    NONE = "none"


# ---------------------------------------------------------------------------
# Frozen dataclasses (immutable after creation)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Parameter:
    """A user-supplied parameter for pipeline instantiation."""

    name: str
    type: str  # "string" | "int" | "bool" | "list"
    description: str
    default: Any = None
    required: bool = False


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to an input artifact from an upstream slot."""

    name: str
    from_slot: str  # Slot ID or "external"
    artifact: str  # Artifact name from producer's outputs
    required: bool = True


@dataclass(frozen=True)
class ArtifactOutput:
    """Declaration of an output artifact produced by a slot."""

    name: str
    type: str  # ArtifactType value
    path: str | None = None
    validation: str = "exists"  # ValidationLevel value


@dataclass(frozen=True)
class Gate:
    """A pre-condition or post-condition on a slot."""

    check: str  # Human-readable description
    type: str  # ConditionType value
    target: str  # Evaluation target (file path, slot ID, expression)


@dataclass(frozen=True)
class DataFlowEdge:
    """An edge in the pipeline DAG connecting slot outputs to inputs."""

    from_slot: str
    to_slot: str
    artifact: str  # Artifact name
    required: bool = True


@dataclass(frozen=True)
class GateCheckResult:
    """Result of evaluating a single gate condition."""

    condition: str  # Human-readable condition description
    passed: bool
    evidence: str  # What was actually found
    checked_at: str  # ISO 8601 timestamp


# ---------------------------------------------------------------------------
# Mutable dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SlotTask:
    """What the agent filling this slot must accomplish."""

    objective: str
    context_files: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)


@dataclass
class ExecutionConfig:
    """Execution constraints for a slot."""

    timeout_hours: float = 4.0
    retry_on_fail: bool = True
    max_retries: int = 2
    parallel_group: str | None = None


@dataclass
class Slot:
    """A typed placeholder in the pipeline DAG."""

    id: str
    slot_type: str  # References SlotTypeDefinition.id
    name: str
    inputs: list[ArtifactRef] = field(default_factory=list)
    outputs: list[ArtifactOutput] = field(default_factory=list)
    pre_conditions: list[Gate] = field(default_factory=list)
    post_conditions: list[Gate] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    task: SlotTask | None = None
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)


@dataclass
class Pipeline:
    """Top-level pipeline definition."""

    id: str
    name: str
    version: str
    description: str
    created_by: str
    created_at: str
    parameters: list[Parameter] = field(default_factory=list)
    slots: list[Slot] = field(default_factory=list)
    data_flow: list[DataFlowEdge] = field(default_factory=list)


# ---------------------------------------------------------------------------
# State dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SlotState:
    """Runtime state of a single slot."""

    slot_id: str
    status: SlotStatus = SlotStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0
    error: str | None = None
    agent_id: str | None = None
    agent_prompt: str | None = None
    pre_check_results: list[GateCheckResult] = field(default_factory=list)
    post_check_results: list[GateCheckResult] = field(default_factory=list)


@dataclass
class PipelineState:
    """Runtime state of an entire pipeline instance."""

    pipeline_id: str
    pipeline_version: str
    definition_hash: str  # sha256 of pipeline YAML content
    status: PipelineStatus = PipelineStatus.LOADED
    started_at: str | None = None
    completed_at: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    slots: dict[str, SlotState] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Slot system dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlotTypeDefinition:
    """Interface contract for a slot type. Loaded from YAML."""

    id: str
    name: str
    category: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_capabilities: list[str]
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentCapabilities:
    """Capability metadata parsed from agent .md front-matter."""

    agent_id: str
    version: str
    capabilities: list[str]
    compatible_slot_types: list[str]
    prompt_path: str  # Path to the agent .md file


@dataclass(frozen=True)
class CapabilityMatch:
    """Result of matching an agent to a slot type."""

    agent_id: str
    prompt_path: str
    matched_capabilities: list[str]  # Capabilities that matched
    missing_capabilities: list[str]  # Required but not present
    is_compatible: bool  # True if missing is empty


@dataclass
class SlotAssignment:
    """Maps a slot to a specific agent."""

    slot_id: str
    slot_type: str
    agent_id: str
    agent_prompt: str
    reason: str = ""
