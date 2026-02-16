# Pipeline Engine Implementation Guide

> Version: 2.0
> Date: 2026-02-16
> Author: ARCH-001
> For: ENG-001 (Engineer)
> References: `architect/architecture.md`, `specs/pipelines/schema.yaml`, `specs/integration-contract.md`
>
> Migration from v1.0:
>   - Step -> Slot (slot_type replaces role/agent_prompt)
>   - Added DataFlowEdge and data_flow[] to Pipeline
>   - Added Module 6: slot_registry.py (NEW)
>   - Renamed StepStatus -> SlotStatus, StepState -> SlotState, etc.
>   - from_step -> from_slot in ArtifactRef
>   - step_completed -> slot_completed in ConditionType
>   - Pipeline.steps -> Pipeline.slots + Pipeline.data_flow

---

## Overview

This guide tells you exactly what to implement, in what order, with what interfaces. The pipeline engine is a Python package at `engineer/src/pipeline/` that loads, validates, and orchestrates YAML pipeline definitions.

**Important**: The pipeline engine is a standalone tool module. It does NOT import from or depend on the trading system modules (`risk/`, `execution/`, `strategy/`, etc.). It only depends on `yaml` (stdlib-compatible via PyYAML) and standard library.

**Key concept**: Pipelines define typed **slots** (not agent roles). Each slot has a `slot_type` that references a SlotType definition. Agent assignment is handled externally via `SlotAssignment` objects. This separation means swapping an agent never requires changing the pipeline definition.

---

## Module 1: `pipeline/models.py` -- Data Models

**Priority**: P1 (implement first, all other modules depend on this)
**Estimated LOC**: ~200

### What to implement

All data models as frozen or regular dataclasses. These are pure data containers with no logic.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SlotStatus(StrEnum):
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
    LOADED = "loaded"
    VALIDATED = "validated"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class ArtifactType(StrEnum):
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
    FILE_EXISTS = "file_exists"
    GATE_PASS = "gate_pass"
    APPROVAL = "approval"
    ARTIFACT_VALID = "artifact_valid"
    SLOT_COMPLETED = "slot_completed"
    CUSTOM = "custom"


class PostConditionType(StrEnum):
    DELIVERY_VALID = "delivery_valid"
    REVIEW_VALID = "review_valid"
    TESTS_PASS = "tests_pass"
    GATE_PASS = "gate_pass"
    CHECKSUM_MATCH = "checksum_match"
    CUSTOM = "custom"


class ValidationLevel(StrEnum):
    CHECKSUM = "checksum"
    SCHEMA = "schema"
    EXISTS = "exists"
    NONE = "none"


@dataclass(frozen=True)
class Parameter:
    name: str
    type: str
    description: str
    default: Any = None
    required: bool = False


@dataclass(frozen=True)
class ArtifactRef:
    name: str
    from_slot: str        # Changed from from_step
    artifact: str
    required: bool = True


@dataclass(frozen=True)
class ArtifactOutput:
    name: str
    type: str
    path: str | None = None
    validation: str = "exists"


@dataclass(frozen=True)
class Gate:
    check: str
    type: str
    target: str


@dataclass
class SlotTask:
    objective: str
    context_files: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)


@dataclass
class ExecutionConfig:
    timeout_hours: float = 4.0
    retry_on_fail: bool = True
    max_retries: int = 2
    parallel_group: str | None = None


@dataclass
class Slot:
    id: str
    slot_type: str              # References SlotType.id -- NOT an agent ID
    name: str
    inputs: list[ArtifactRef] = field(default_factory=list)
    outputs: list[ArtifactOutput] = field(default_factory=list)
    pre_conditions: list[Gate] = field(default_factory=list)
    post_conditions: list[Gate] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    task: SlotTask | None = None
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)


@dataclass(frozen=True)
class DataFlowEdge:
    from_slot: str
    to_slot: str
    artifact: str
    required: bool = True


@dataclass
class Pipeline:
    id: str
    name: str
    version: str
    description: str
    created_by: str
    created_at: str
    parameters: list[Parameter] = field(default_factory=list)
    slots: list[Slot] = field(default_factory=list)
    data_flow: list[DataFlowEdge] = field(default_factory=list)


@dataclass
class GateCheckResult:
    condition: str          # Human-readable condition description
    passed: bool
    evidence: str           # What was actually found
    checked_at: str         # ISO 8601 timestamp


@dataclass
class SlotState:
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
    pipeline_id: str
    pipeline_version: str
    pipeline_definition_hash: str
    status: PipelineStatus = PipelineStatus.LOADED
    started_at: str | None = None
    completed_at: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    slots: dict[str, SlotState] = field(default_factory=dict)


# --- Slot system models ---

@dataclass(frozen=True)
class SlotTypeDefinition:
    id: str
    name: str
    category: str
    description: str
    input_schema: dict
    output_schema: dict
    required_capabilities: list[str]
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentCapabilities:
    agent_id: str
    capabilities: list[str]
    compatible_slot_types: list[str]


@dataclass(frozen=True)
class CapabilityMatch:
    agent_id: str
    slot_type_id: str
    matched_capabilities: list[str]
    missing_capabilities: list[str]
    is_compatible: bool


@dataclass(frozen=True)
class SlotAssignment:
    slot_id: str
    slot_type: str
    agent_id: str
    agent_prompt: str
    reason: str = ""
```

### Tests

File: `tests/test_pipeline/test_models.py`

- Test all enum values are correct strings
- Test dataclass creation with defaults
- Test frozen dataclasses are immutable (Parameter, ArtifactRef, Gate, DataFlowEdge, etc.)
- Test Pipeline and Slot creation with all fields
- Test DataFlowEdge creation
- Test SlotTypeDefinition, AgentCapabilities, CapabilityMatch, SlotAssignment creation
- Test PipelineState serialization round-trip (to/from dict)

---

## Module 2: `pipeline/loader.py` -- YAML Loading

**Priority**: P1
**Estimated LOC**: ~150
**Depends on**: `models.py`

### Interface

```python
class PipelineLoadError(Exception):
    """Raised when pipeline YAML is malformed or missing required fields."""


class PipelineParameterError(Exception):
    """Raised when a required parameter is not provided."""


class PipelineLoader:
    def load(self, yaml_path: str) -> Pipeline:
        """Parse YAML file into Pipeline object.

        Reads the YAML file, extracts the `pipeline:` top-level key,
        and hydrates all nested objects (Slot, ArtifactRef, DataFlowEdge, etc.).

        Raises PipelineLoadError if:
        - File does not exist
        - YAML is malformed
        - Required top-level fields are missing
        - Slot is missing required fields (id, slot_type, name)
        """

    def resolve(self, pipeline: Pipeline, params: dict[str, Any]) -> Pipeline:
        """Replace {parameter} placeholders with concrete values.

        Walks all string fields in the Pipeline and its Slots,
        replacing any `{param_name}` with the corresponding value
        from `params`. Missing required parameters raise an error.

        Does NOT modify the input Pipeline (returns a new one).
        """

    def load_and_resolve(
        self, yaml_path: str, params: dict[str, Any]
    ) -> Pipeline:
        """Convenience: load() then resolve()."""
```

### Implementation notes

1. Use `yaml.safe_load()` (never `yaml.load()`)
2. The YAML has a top-level wrapper key `pipeline:` -- extract the dict under it
3. Parse `slots:` list into `Slot` objects (NOT `steps:`)
4. Parse `data_flow:` list into `DataFlowEdge` objects
5. Parameter resolution: use `re.sub(r'\{(\w+)\}', replacer, string)` to find placeholders
6. For parameter type checking: `int` params should be converted from string, `bool` from "true"/"false"
7. Return new dataclass instances (don't mutate)

### Tests

File: `tests/test_pipeline/test_loader.py`

- `test_load_valid_pipeline` -- load `standard-feature.yaml`, verify all fields including slot_type and data_flow
- `test_load_missing_file` -- raises PipelineLoadError
- `test_load_malformed_yaml` -- raises PipelineLoadError
- `test_load_missing_required_field` -- missing `id` raises error
- `test_load_slot_missing_slot_type` -- raises PipelineLoadError
- `test_load_data_flow_edges` -- data_flow parsed correctly
- `test_resolve_parameters` -- `{feature_name}` replaced correctly in slots and data_flow paths
- `test_resolve_missing_required_param` -- raises PipelineParameterError
- `test_resolve_default_param` -- default used when not provided
- `test_load_and_resolve` -- end-to-end convenience method

---

## Module 3: `pipeline/validator.py` -- Validation

**Priority**: P1
**Estimated LOC**: ~250
**Depends on**: `models.py`, `slot_registry.py` (optional, for slot type checks)

### Interface

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]       # Blocking issues
    warnings: list[str]     # Non-blocking advisories


class PipelineCycleError(Exception):
    """Raised when dependency graph has a cycle."""


class PipelineValidator:
    def __init__(self, project_root: str):
        """
        Args:
            project_root: Root directory of the project
                          (for checking file existence).
        """

    def validate(self, pipeline: Pipeline) -> ValidationResult:
        """Run all validation checks.

        Checks performed:
        1. unique_slot_ids -- no duplicate slot IDs
        2. valid_dependencies -- all depends_on reference existing slots
        3. dag_acyclic -- no dependency cycles (considers both depends_on and required data_flow edges)
        4. io_compatible -- every data_flow edge has matching producer output
        5. slot_type_exists -- all slot_type references exist in registry (when registry provided)
        6. implementer_has_delivery -- implementer slots have delivery post-condition
        7. reviewer_has_review -- reviewer slots have review post-condition
        8. terminal_slot -- at least one slot has no dependents
        9. valid_data_flow -- all data_flow from_slot/to_slot exist
        10. data_flow_artifact_match -- data_flow artifact names match producer outputs

        Returns ValidationResult with collected errors and warnings.
        """

    def check_dag(self, pipeline: Pipeline) -> list[str]:
        """Check for dependency cycles using Kahn's algorithm.

        Builds the full dependency graph from:
        - Explicit depends_on edges
        - Required data_flow edges (required=true creates an implicit dependency)

        Returns list of error messages. Empty list = no cycles.
        """

    def topological_sort(self, pipeline: Pipeline) -> list[str]:
        """Return slot IDs in valid execution order.

        Raises PipelineCycleError if cycle detected.
        """

    def check_io_compatibility(self, pipeline: Pipeline) -> list[str]:
        """Verify every data_flow edge has a matching producer output."""

    def check_slot_types(
        self, pipeline: Pipeline, slot_types_dir: str
    ) -> list[str]:
        """Verify all slot_type references exist as .yaml files in slot_types_dir."""
```

### Implementation notes

1. **Kahn's algorithm** for topological sort -- but now operates on the union of `depends_on` edges and `required` data_flow edges:
   ```
   # Build adjacency from depends_on
   for each slot:
       for each dep in slot.depends_on:
           add edge dep -> slot.id

   # Build adjacency from required data_flow
   for each edge in pipeline.data_flow:
       if edge.required:
           add edge edge.from_slot -> edge.to_slot

   # Deduplicate edges, then run Kahn's
   ```
2. For I/O compatibility: build a map of `{slot_id: {artifact_name: ArtifactOutput}}`, then verify each `data_flow` edge's artifact exists in the producer
3. For slot type checking: scan `slot_types_dir` for `.yaml` files, extract their `slot_type.id`, build a set, check each slot's `slot_type` is in the set

### Tests

File: `tests/test_pipeline/test_validator.py`

- `test_valid_pipeline` -- standard-feature validates clean
- `test_duplicate_slot_ids` -- error detected
- `test_dependency_cycle` -- A depends on B, B depends on A
- `test_dependency_cycle_via_data_flow` -- cycle detected through data_flow edges
- `test_missing_dependency_target` -- depends_on references non-existent slot
- `test_io_incompatibility` -- data_flow references non-existent artifact
- `test_topological_sort_linear` -- A -> B -> C -> [A, B, C]
- `test_topological_sort_parallel` -- A -> B, A -> C, B+C -> D
- `test_implementer_without_delivery` -- warning generated
- `test_no_terminal_slot` -- warning generated
- `test_invalid_data_flow_slot` -- data_flow references non-existent slot ID
- `test_check_slot_types` -- missing slot type detected

---

## Module 4: `pipeline/gate_checker.py` -- Condition Evaluation

**Priority**: P1
**Estimated LOC**: ~180
**Depends on**: `models.py`

### Interface

```python
class GateChecker:
    def __init__(self, project_root: str):
        """
        Args:
            project_root: Root directory for resolving file paths.
        """

    def check_pre_conditions(
        self, slot: Slot, pipeline_state: PipelineState
    ) -> list[GateCheckResult]:
        """Evaluate all pre-conditions for a slot.

        Dispatches each condition to the appropriate checker
        based on condition.type.

        Returns list of GateCheckResult (one per condition).
        """

    def check_post_conditions(
        self, slot: Slot, pipeline_state: PipelineState
    ) -> list[GateCheckResult]:
        """Evaluate all post-conditions for a slot."""

    def all_passed(self, results: list[GateCheckResult]) -> bool:
        """Return True if all results passed."""

    # --- Individual checkers ---

    def check_file_exists(self, target: str) -> GateCheckResult:
        """Check if file exists at project_root/target."""

    def check_slot_completed(
        self, target: str, state: PipelineState
    ) -> GateCheckResult:
        """Check if slot with given ID has status COMPLETED."""

    def check_delivery_valid(self, target: str) -> GateCheckResult:
        """Run validate_delivery() on target DELIVERY.yaml.

        Import and call the validation function from
        specs/delivery-schema.py.

        If the import or validation fails, return GateCheckResult
        with passed=False and the error in evidence.
        """

    def check_review_valid(self, target: str) -> GateCheckResult:
        """Run validate_review() on target REVIEW.yaml."""

    def evaluate_custom(self, target: str) -> GateCheckResult:
        """Evaluate custom expression.

        Supported formats:
        - "yaml_field:<file>:<field_path> <op> <value>"
          e.g., "yaml_field:qa/REVIEW.yaml:verdict != fail"
        - "command:<shell_command>"
          e.g., "command:ssh trading-vm systemctl is-active trading"

        For yaml_field: parse the YAML, navigate the field path,
        compare with operator and value.

        For command: run subprocess, pass=exit code 0, fail=non-zero.

        SECURITY: Never use shell=True with untrusted input.
        Only allow commands from a whitelist or pre-approved patterns.
        """
```

### Implementation notes

1. All file paths resolved relative to `project_root`
2. `check_delivery_valid` and `check_review_valid` need to import from `specs/delivery-schema.py` -- use `importlib` or `exec` with the schema file. Alternatively, if the schema is complex to import, just check file existence + YAML parsability as a fallback
3. `evaluate_custom` with `yaml_field:` -- parse nested field paths with `.` separator: `verdict` reads `data['verdict']`, `test_results.coverage_pct` reads `data['test_results']['coverage_pct']`
4. Timestamps in GateCheckResult should use `datetime.now(timezone.utc).isoformat()`
5. All checkers should never raise -- they return GateCheckResult with passed=False on any error

### Tests

File: `tests/test_pipeline/test_gate_checker.py`

- `test_check_file_exists_present` -- file exists, PASS
- `test_check_file_exists_missing` -- file missing, FAIL
- `test_check_slot_completed` -- slot in state with COMPLETED, PASS
- `test_check_slot_not_completed` -- slot in state with IN_PROGRESS, FAIL
- `test_evaluate_custom_yaml_field` -- read YAML field and compare
- `test_evaluate_custom_yaml_field_nested` -- nested field path
- `test_all_passed_true` -- all results passed
- `test_all_passed_false` -- one result failed
- `test_check_delivery_valid` (integration test, can be skipped if schema import is complex)

---

## Module 5: `pipeline/state.py` -- State Tracking

**Priority**: P1
**Estimated LOC**: ~170
**Depends on**: `models.py`

### Interface

```python
class PipelineStateTracker:
    def __init__(self, state_dir: str):
        """
        Args:
            state_dir: Directory for state files.
                       Typically state/active/
        """

    def init_state(
        self, pipeline: Pipeline, params: dict[str, Any]
    ) -> PipelineState:
        """Create initial state for a pipeline run.

        - Sets all slots to PENDING
        - Computes pipeline_definition_hash (sha256 of pipeline YAML)
        - Saves state file to state_dir
        - Returns the new state

        File name: {pipeline.id}-{timestamp}.state.yaml
        """

    def update_slot(
        self,
        state: PipelineState,
        slot_id: str,
        status: SlotStatus,
        *,
        error: str | None = None,
        agent_id: str | None = None,
        agent_prompt: str | None = None,
        pre_check_results: list[GateCheckResult] | None = None,
        post_check_results: list[GateCheckResult] | None = None,
    ) -> PipelineState:
        """Update a slot's status and auto-save.

        Also updates timestamps:
        - started_at when status changes to IN_PROGRESS
        - completed_at when status changes to COMPLETED/FAILED/SKIPPED
        """

    def get_ready_slots(
        self,
        pipeline: Pipeline,
        state: PipelineState,
    ) -> list[str]:
        """Find slots whose dependencies are all met.

        A slot is ready when:
        1. Its current status is PENDING or BLOCKED
        2. All slots in its depends_on list have status COMPLETED
        3. All required data_flow source slots are COMPLETED
        """

    def is_complete(self, state: PipelineState) -> bool:
        """True if all slots are COMPLETED, SKIPPED, or FAILED."""

    def get_status_summary(self, state: PipelineState) -> dict:
        """Human-readable summary.

        Returns:
        {
            "pipeline_id": str,
            "status": str,
            "progress": "3/7 slots completed",
            "completed": [...slot_ids...],
            "in_progress": [...],
            "blocked": [...],
            "pending": [...],
            "failed": [...],
        }
        """

    def save(self, state: PipelineState) -> str:
        """Persist state to YAML file. Returns file path."""

    def load(self, state_path: str) -> PipelineState:
        """Load state from YAML file."""

    def archive(self, state: PipelineState) -> str:
        """Move state file from active/ to archive/. Returns new path."""
```

### Implementation notes

1. State files use `yaml.safe_dump()` with `default_flow_style=False`
2. `pipeline_definition_hash`: compute sha256 of the pipeline YAML content (not the state file)
3. `get_ready_slots` builds the full dependency graph from `Pipeline.slots[].depends_on` AND `Pipeline.data_flow` (required edges only)
4. `save()` should write atomically (write to temp file, then rename)
5. `archive()` moves file from `state_dir` to `state_dir/../archive/`
6. `SlotState` now includes `agent_id` and `agent_prompt` (set when slot is assigned)

### Tests

File: `tests/test_pipeline/test_state.py`

- `test_init_state` -- all slots PENDING, file created
- `test_update_slot_status` -- status changes, timestamps set
- `test_get_ready_slots_initial` -- slots with no deps are ready
- `test_get_ready_slots_after_completion` -- dependent slots become ready
- `test_get_ready_slots_blocked_by_data_flow` -- slot blocked by required data_flow source
- `test_get_ready_slots_not_blocked_by_optional_data_flow` -- optional data_flow does not block
- `test_is_complete` -- all completed/skipped
- `test_save_load_roundtrip` -- save then load produces identical state
- `test_get_status_summary` -- correct counts

---

## Module 6: `pipeline/slot_registry.py` -- Slot Type & Capability Registry (NEW)

**Priority**: P1
**Estimated LOC**: ~180
**Depends on**: `models.py`

### Interface

```python
class SlotRegistryError(Exception):
    """Raised on registry loading or matching errors."""


class SlotRegistry:
    def __init__(self, slot_types_dir: str, agents_dir: str):
        """
        Args:
            slot_types_dir: Path to specs/pipelines/slot-types/
            agents_dir: Path to agents/ directory containing agent .md files
        """

    def load_slot_types(self) -> dict[str, SlotTypeDefinition]:
        """Load all .yaml files from slot_types_dir.

        Each file must have a top-level `slot_type:` key.
        Returns dict mapping slot_type.id -> SlotTypeDefinition.

        Raises SlotRegistryError if:
        - Directory does not exist
        - YAML is malformed
        - Duplicate slot type IDs found
        """

    def load_agent_capabilities(self) -> dict[str, AgentCapabilities]:
        """Load capability declarations from agent .md files.

        Parses YAML front-matter (between --- markers) from each agent
        prompt file. Extracts `capabilities` and `compatible_slot_types`
        fields.

        Returns dict mapping agent_id -> AgentCapabilities.
        """

    def get_slot_type(self, slot_type_id: str) -> SlotTypeDefinition:
        """Retrieve a specific slot type by ID.

        Raises KeyError if not found.
        """

    def find_compatible_agents(
        self, slot_type_id: str
    ) -> list[CapabilityMatch]:
        """Find all agents whose capabilities are a superset of
        the slot type's required_capabilities.

        Returns list of CapabilityMatch sorted by number of
        matched capabilities (best match first).
        """

    def validate_assignment(
        self, slot_type_id: str, agent_id: str
    ) -> CapabilityMatch:
        """Check if a specific agent can fill a specific slot type.

        Returns CapabilityMatch with is_compatible=True/False and
        details of matched/missing capabilities.
        """

    def generate_slot_manifest(
        self, pipeline: Pipeline
    ) -> dict[str, list[CapabilityMatch]]:
        """For each slot in the pipeline, list compatible agents.

        Returns dict mapping slot_id -> list[CapabilityMatch].
        Used by HR to make assignment decisions.
        """
```

### Implementation notes

1. **YAML front-matter parsing**: Agent .md files start with `---\n...\n---`. Use `yaml.safe_load()` on the content between the first pair of `---` markers
2. **Capability matching**: `agent.capabilities SUPERSET_OF slot_type.required_capabilities`
   ```python
   agent_caps = set(agent.capabilities)
   required = set(slot_type.required_capabilities)
   is_compatible = required.issubset(agent_caps)
   missing = list(required - agent_caps)
   matched = list(required & agent_caps)
   ```
3. Slot types are loaded once and cached. Call `load_slot_types()` in `__init__` or lazily on first access
4. Agent capabilities are also loaded once and cached
5. `compatible_slot_types` in agent front-matter is advisory (HR declares it). The engine validates it against actual capability matching

### Tests

File: `tests/test_pipeline/test_slot_registry.py`

- `test_load_slot_types` -- loads all .yaml files, verifies IDs
- `test_load_slot_types_empty_dir` -- empty dir returns empty dict
- `test_load_slot_types_malformed` -- raises SlotRegistryError
- `test_load_agent_capabilities` -- parses front-matter correctly
- `test_find_compatible_agents` -- returns matching agents sorted
- `test_find_compatible_agents_no_match` -- returns empty list
- `test_validate_assignment_compatible` -- all caps met, is_compatible=True
- `test_validate_assignment_incompatible` -- missing caps, is_compatible=False
- `test_generate_slot_manifest` -- correct mapping for multi-slot pipeline
- `test_get_slot_type_not_found` -- raises KeyError

---

## Module 7: `pipeline/nl_matcher.py` -- Template Matching

**Priority**: P2 (implement after core modules)
**Estimated LOC**: ~120
**Depends on**: `models.py`

### Interface

```python
@dataclass(frozen=True)
class TemplateMatch:
    template_id: str
    template_path: str
    confidence: float           # 0.0 - 1.0
    matched_keywords: list[str]
    description: str
    suggested_params: dict[str, Any]


class NLMatcher:
    def __init__(self, templates_dir: str):
        """Load template registry.

        Scans templates_dir for .yaml files and builds
        keyword/pattern index from each template's metadata.
        """

    def match(self, nl_input: str) -> list[TemplateMatch]:
        """Find matching templates for a natural language input.

        Algorithm:
        1. Tokenize input (split on spaces, punctuation)
        2. For each template, count keyword matches
        3. Score = matched_keywords / total_keywords * base_weight
        4. Apply regex pattern matching for bonus score
        5. Sort by score descending
        6. Return top candidates with confidence > 0.1

        Returns empty list if no match found.
        """

    def extract_params(
        self, nl_input: str, template: TemplateMatch
    ) -> dict[str, Any]:
        """Extract parameter values from natural language.

        Pattern-based extraction:
        - "BTC/USDT" -> target_symbol parameter
        - Chinese/English feature names -> feature_name/strategy_name
        - "phase5" or "阶段5" -> phase_id

        Returns dict of extracted params. Missing params keep defaults.
        """

    def generate_summary(
        self, match: TemplateMatch, params: dict[str, Any]
    ) -> str:
        """Generate human-readable pipeline summary for CEO review."""
```

### Implementation notes

1. Template registry is built by scanning `templates_dir` and reading each YAML's `pipeline.id`, `pipeline.name`, `pipeline.description`, and `pipeline.parameters`
2. Keywords can be extracted from the pipeline description and name
3. Hardcode a keyword map per template (see the TEMPLATE_REGISTRY in the architecture doc)
4. For symbol extraction: regex `r'[A-Z]{2,10}/[A-Z]{2,10}'` catches `BTC/USDT`
5. For phase extraction: regex `r'phase[-_]?(\d+)'` or `r'阶段\s*(\d+)'`

### Tests

File: `tests/test_pipeline/test_nl_matcher.py`

- `test_match_quant_strategy` -- "做量化策略优化" matches quant-strategy
- `test_match_security` -- "做安全加固" matches security-hardening
- `test_match_research` -- "调研XXX" matches research-task
- `test_match_hotfix` -- "紧急修复bug" matches hotfix
- `test_match_standard` -- "实现新功能XXX" matches standard-feature
- `test_no_match` -- "今天天气好" returns empty
- `test_extract_symbol` -- "BTC/USDT" extracted from input
- `test_extract_phase` -- "phase5" extracted from input
- `test_generate_summary` -- readable output with slots and params

---

## Module 8: `pipeline/runner.py` -- Orchestrator

**Priority**: P2
**Estimated LOC**: ~250
**Depends on**: `models.py`, `loader.py`, `validator.py`, `gate_checker.py`, `state.py`, `slot_registry.py`

### Interface

```python
class PipelineExecutionError(Exception):
    """Raised on unrecoverable pipeline execution errors."""


class PipelineRunner:
    def __init__(
        self,
        project_root: str,
        templates_dir: str,
        state_dir: str,
        slot_types_dir: str,
        agents_dir: str,
    ):
        """Initialize with paths. Creates internal loader, validator,
        state tracker, slot registry, and gate checker."""

    def prepare(
        self, yaml_path: str, params: dict[str, Any]
    ) -> tuple[Pipeline, PipelineState]:
        """Load, resolve, validate pipeline, and init state.

        Returns (pipeline, state) ready for execution.
        Raises on validation errors.
        """

    def get_next_slots(
        self, pipeline: Pipeline, state: PipelineState
    ) -> list[Slot]:
        """Get slots that are ready to execute.

        Returns Slot objects (not just IDs) for convenience.
        Groups parallel slots together.
        """

    def begin_slot(
        self,
        slot: Slot,
        pipeline: Pipeline,
        state: PipelineState,
        *,
        agent_id: str | None = None,
        agent_prompt: str | None = None,
    ) -> PipelineState:
        """Begin execution of a slot.

        1. Check pre-conditions
        2. Mark IN_PROGRESS with agent assignment
        3. Return updated state

        NOTE: Actual agent spawning is done by the team lead.
        This method handles bookkeeping and gate checking.
        """

    def complete_slot(
        self, slot_id: str, pipeline: Pipeline, state: PipelineState
    ) -> PipelineState:
        """Mark a slot as completed.

        1. Run post-conditions
        2. Mark COMPLETED or FAILED based on gate results
        3. Return updated state
        """

    def mark_slot_failed(
        self, slot_id: str, error: str, state: PipelineState
    ) -> PipelineState:
        """Manually mark a slot as failed."""

    def mark_slot_skipped(
        self, slot_id: str, state: PipelineState
    ) -> PipelineState:
        """Manually skip a slot (CEO decision)."""

    def get_summary(self, state: PipelineState) -> str:
        """Human-readable pipeline status for CEO."""

    def resume(self, state_path: str) -> tuple[Pipeline, PipelineState]:
        """Resume a pipeline from a saved state file."""
```

### Implementation notes

1. **Initial implementation is protocol-driven, not fully automated**. The runner manages state and gate checks. Actual agent execution is handled by the team lead (CEO or PMO) who:
   - Calls `get_next_slots()` to see what's ready
   - Uses `begin_slot()` to check pre-conditions and mark as IN_PROGRESS
   - Spawns agent teammates manually
   - Calls `complete_slot()` when the agent finishes
2. `begin_slot()` takes optional `agent_id` and `agent_prompt` to record the assignment in SlotState
3. Future iterations can add automated agent spawning
4. `get_summary()` should produce clear, tabular output suitable for CEO review
5. `resume()` loads both the state file and re-loads the pipeline YAML to verify integrity (compare hashes)

### Tests

File: `tests/test_pipeline/test_runner.py`

- `test_prepare_valid_pipeline` -- loads and validates successfully
- `test_prepare_invalid_pipeline` -- raises on validation error
- `test_get_next_slots_initial` -- returns slots with no dependencies
- `test_get_next_slots_after_completion` -- dependent slots become available
- `test_begin_slot` -- pre-conditions checked, status set to IN_PROGRESS
- `test_begin_slot_with_agent` -- agent_id and agent_prompt recorded
- `test_complete_slot` -- post-conditions run, status set
- `test_mark_slot_failed` -- status set, error recorded
- `test_mark_slot_skipped` -- dependents unblocked
- `test_get_summary` -- readable output
- `test_resume_from_state` -- state loaded and execution continues

---

## Module 9: `pipeline/__init__.py` -- Public API

```python
"""Pipeline Engine for Agent Team Orchestration.

Usage:
    from src.pipeline import PipelineRunner

    runner = PipelineRunner(
        project_root="/path/to/agent-orchestrator",
        templates_dir="specs/pipelines/templates",
        state_dir="state/active",
        slot_types_dir="specs/pipelines/slot-types",
        agents_dir="agents",
    )

    # Prepare a pipeline
    pipeline, state = runner.prepare(
        yaml_path="specs/pipelines/templates/standard-feature.yaml",
        params={"feature_name": "kline-aggregator", "phase_id": "phase5"},
    )

    # Check what's ready
    next_slots = runner.get_next_slots(pipeline, state)

    # Begin a slot (with agent assignment)
    state = runner.begin_slot(
        next_slots[0], pipeline, state,
        agent_id="ENG-001",
        agent_prompt="agents/02-engineer-agent.md",
    )

    # After agent completes
    state = runner.complete_slot("architect-design", pipeline, state)

    # Check status
    print(runner.get_summary(state))
"""

from src.pipeline.models import (
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotStatus,
    DataFlowEdge,
    SlotTypeDefinition,
    SlotAssignment,
    CapabilityMatch,
)
from src.pipeline.runner import PipelineRunner
from src.pipeline.validator import PipelineValidator, ValidationResult
from src.pipeline.loader import PipelineLoader
from src.pipeline.gate_checker import GateChecker
from src.pipeline.state import PipelineStateTracker
from src.pipeline.slot_registry import SlotRegistry
from src.pipeline.nl_matcher import NLMatcher

__all__ = [
    "Pipeline",
    "PipelineState",
    "PipelineStatus",
    "Slot",
    "SlotStatus",
    "DataFlowEdge",
    "SlotTypeDefinition",
    "SlotAssignment",
    "CapabilityMatch",
    "PipelineRunner",
    "PipelineValidator",
    "ValidationResult",
    "PipelineLoader",
    "GateChecker",
    "PipelineStateTracker",
    "SlotRegistry",
    "NLMatcher",
]
```

---

## Test Strategy

### Test Organization

```
engineer/tests/test_pipeline/
├── __init__.py
├── conftest.py              # Shared fixtures (sample pipelines, temp dirs)
├── test_models.py           # ~20 tests
├── test_loader.py           # ~12 tests
├── test_validator.py        # ~14 tests
├── test_gate_checker.py     # ~10 tests
├── test_state.py            # ~12 tests
├── test_slot_registry.py    # ~12 tests (NEW)
├── test_nl_matcher.py       # ~10 tests
├── test_runner.py           # ~12 tests
└── fixtures/
    ├── valid-pipeline.yaml       # Minimal valid slot-based pipeline
    ├── invalid-cycle.yaml        # Pipeline with dependency cycle
    ├── invalid-io.yaml           # Pipeline with data_flow I/O mismatch
    ├── sample-delivery.yaml      # Sample DELIVERY.yaml for gate_checker tests
    ├── sample-slot-type.yaml     # Sample SlotType for registry tests
    └── sample-agent.md           # Sample agent with front-matter for registry tests
```

### Shared Fixtures (`conftest.py`)

```python
import pytest
from pathlib import Path

@pytest.fixture
def project_root(tmp_path):
    """Create a minimal project structure for testing."""
    (tmp_path / "architect").mkdir()
    (tmp_path / "architect" / "integration-contract.md").write_text("# Contract")
    (tmp_path / "engineer" / "src").mkdir(parents=True)
    (tmp_path / "engineer" / "tests").mkdir(parents=True)
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "01-architect-agent.md").write_text(
        "---\nagent_id: ARCH-001\ncapabilities:\n  - system_design\ncompatible_slot_types:\n  - designer\n---\n# Architect"
    )
    (tmp_path / "agents" / "02-engineer-agent.md").write_text(
        "---\nagent_id: ENG-001\ncapabilities:\n  - python_development\n  - test_writing\n  - delivery_protocol\ncompatible_slot_types:\n  - implementer\n---\n# Engineer"
    )
    (tmp_path / "agents" / "03-qa-agent.md").write_text(
        "---\nagent_id: QA-001\ncapabilities:\n  - independent_testing\n  - code_review\n  - delivery_protocol\n  - cross_validation\ncompatible_slot_types:\n  - reviewer\n---\n# QA"
    )
    return tmp_path

@pytest.fixture
def slot_types_dir(tmp_path):
    """Create slot type definitions for testing."""
    d = tmp_path / "slot-types"
    d.mkdir()
    (d / "implementer.yaml").write_text(
        "slot_type:\n  id: implementer\n  name: Code Implementer\n  category: engineering\n"
        "  description: Writes code\n  input_schema: {}\n  output_schema: {}\n"
        "  required_capabilities:\n    - python_development\n    - test_writing\n    - delivery_protocol\n"
    )
    (d / "reviewer.yaml").write_text(
        "slot_type:\n  id: reviewer\n  name: Quality Reviewer\n  category: quality\n"
        "  description: Reviews code\n  input_schema: {}\n  output_schema: {}\n"
        "  required_capabilities:\n    - independent_testing\n    - code_review\n    - delivery_protocol\n    - cross_validation\n"
    )
    return d

@pytest.fixture
def templates_dir():
    """Path to actual pipeline templates."""
    return Path(__file__).parent.parent.parent.parent / "specs" / "pipelines" / "templates"

@pytest.fixture
def state_dir(tmp_path):
    """Temp directory for state files."""
    d = tmp_path / "active"
    d.mkdir()
    return d

@pytest.fixture
def sample_pipeline():
    """Minimal valid Pipeline object for unit tests."""
    from src.pipeline.models import (
        Pipeline, Slot, SlotTask, DataFlowEdge, ArtifactOutput,
    )
    return Pipeline(
        id="test-pipeline",
        name="Test Pipeline",
        version="1.0.0",
        description="Test",
        created_by="test",
        created_at="2026-01-01T00:00:00Z",
        slots=[
            Slot(
                id="slot-a",
                slot_type="designer",
                name="Slot A",
                outputs=[ArtifactOutput(name="design_doc", type="design_doc")],
                task=SlotTask(objective="Do A"),
            ),
            Slot(
                id="slot-b",
                slot_type="implementer",
                name="Slot B",
                depends_on=["slot-a"],
                task=SlotTask(objective="Do B"),
            ),
        ],
        data_flow=[
            DataFlowEdge(
                from_slot="slot-a",
                to_slot="slot-b",
                artifact="design_doc",
                required=True,
            ),
        ],
    )
```

### Coverage Target

- **Overall**: >= 85%
- **models.py**: >= 95% (pure data, easy to cover)
- **validator.py**: >= 90% (critical logic)
- **gate_checker.py**: >= 85%
- **state.py**: >= 90%
- **loader.py**: >= 85%
- **slot_registry.py**: >= 90% (NEW, critical for slot system)
- **runner.py**: >= 80%
- **nl_matcher.py**: >= 80%

---

## Implementation Order

Execute in this order to maintain build-ability at each slot:

```
1. models.py + test_models.py             (zero deps, foundation)
   |
2. loader.py + test_loader.py             (depends on models)
   |
3. validator.py + test_validator.py        (depends on models)
   |
4. state.py + test_state.py               (depends on models)
   |
5. gate_checker.py + test_gate_checker.py  (depends on models, state)
   |
6. slot_registry.py + test_slot_registry.py (depends on models) [NEW]
   |
7. runner.py + test_runner.py              (depends on all above)
   |
8. nl_matcher.py + test_nl_matcher.py      (depends on models, loader)
   |
9. __init__.py                             (public API exports)
```

Each module should be individually testable after implementation. Run tests after each module:

```bash
cd engineer && .venv/bin/python -m pytest tests/test_pipeline/test_<module>.py -v
```

---

## Dependency Constraints

The pipeline engine must NOT import from:
- `src/core/` (trading models)
- `src/risk/` (risk gateway)
- `src/execution/` (order execution)
- `src/strategy/` (strategies)
- `src/data_pipeline/` (market data)
- `src/monitoring/` (metrics)
- `src/app.py` (application)

It may import:
- `yaml` (PyYAML -- already in project dependencies)
- Python standard library (`dataclasses`, `enum`, `pathlib`, `hashlib`, `re`, `datetime`, `typing`, `collections`, `importlib`, `subprocess`)

This keeps the pipeline engine as an independent tool that can be used without the trading system.
