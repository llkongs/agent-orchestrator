# Integration Contract

> Version: 1.0.0
> Date: 2026-02-16
> Author: ARCH-001 (Pipeline Architect)
> Status: ACTIVE
> References:
>   - `architect/architecture.md` -- System architecture
>   - `specs/pipelines/implementation-guide.md` -- Module implementation specs
>   - `specs/delivery-protocol.md` -- Delivery protocol

This document defines the interface contracts between all modules in the pipeline engine. The Engineer MUST implement these interfaces exactly as specified. Any deviation requires Architect approval.

---

## 1. Module Map

```
src/pipeline/
  __init__.py           # Public API (Module 9)
  models.py             # Module 1: Data Models
  loader.py             # Module 2: YAML Loading
  validator.py          # Module 3: DAG Validation
  state.py              # Module 4: State Tracking
  slot_registry.py      # Module 5: SlotType Registry
  gate_checker.py       # Module 6: Condition Evaluation
  runner.py             # Module 7: Pipeline Orchestration
  nl_matcher.py         # Module 8: Template Matching
```

### Dependency Rules

```
models.py          imports: (nothing -- zero deps)
loader.py          imports: models
validator.py       imports: models
state.py           imports: models
slot_registry.py   imports: models
gate_checker.py    imports: models
runner.py          imports: models, loader, validator, state, slot_registry, gate_checker
nl_matcher.py      imports: models, loader
__init__.py        imports: all of the above (re-exports)
```

**Absolute constraint**: No module in `src/pipeline/` imports from outside `src/pipeline/` except Python stdlib and PyYAML.

---

## 2. Module 1: `models.py` -- Data Models

### Exports

#### Enums

```python
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
    SLOT_COMPLETED = "slot_completed"
    APPROVAL = "approval"
    ARTIFACT_VALID = "artifact_valid"
    DELIVERY_VALID = "delivery_valid"
    REVIEW_VALID = "review_valid"
    TESTS_PASS = "tests_pass"
    CUSTOM = "custom"


class ValidationLevel(StrEnum):
    CHECKSUM = "checksum"
    SCHEMA = "schema"
    EXISTS = "exists"
    NONE = "none"
```

#### Frozen Dataclasses (immutable after creation)

```python
@dataclass(frozen=True)
class Parameter:
    name: str
    type: str               # "string" | "int" | "bool" | "list"
    description: str
    default: Any = None
    required: bool = False


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to an input artifact from an upstream slot."""
    name: str
    from_slot: str          # Slot ID or "external"
    artifact: str           # Artifact name from producer's outputs
    required: bool = True


@dataclass(frozen=True)
class ArtifactOutput:
    """Declaration of an output artifact produced by a slot."""
    name: str
    type: str               # ArtifactType value
    path: str | None = None
    validation: str = "exists"  # ValidationLevel value


@dataclass(frozen=True)
class Gate:
    """A pre-condition or post-condition on a slot."""
    check: str              # Human-readable description
    type: str               # ConditionType value
    target: str             # Evaluation target (file path, slot ID, expression)


@dataclass(frozen=True)
class DataFlowEdge:
    """An edge in the pipeline DAG connecting slot outputs to inputs."""
    from_slot: str
    to_slot: str
    artifact: str           # Artifact name
    required: bool = True


@dataclass(frozen=True)
class GateCheckResult:
    """Result of evaluating a single gate condition."""
    condition: str          # Human-readable condition description
    passed: bool
    evidence: str           # What was actually found
    checked_at: str         # ISO 8601 timestamp
```

#### Mutable Dataclasses

```python
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
    slot_type: str          # References SlotTypeDefinition.id
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
```

#### State Dataclasses

```python
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
    definition_hash: str    # sha256 of pipeline YAML content
    status: PipelineStatus = PipelineStatus.LOADED
    started_at: str | None = None
    completed_at: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    slots: dict[str, SlotState] = field(default_factory=dict)
```

#### Slot System Dataclasses

```python
@dataclass(frozen=True)
class SlotTypeDefinition:
    """Interface contract for a slot type. Loaded from YAML."""
    id: str
    name: str
    category: str
    description: str
    input_schema: dict      # JSON-Schema-like object
    output_schema: dict     # JSON-Schema-like object
    required_capabilities: list[str]
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentCapabilities:
    """Capability metadata parsed from agent .md front-matter."""
    agent_id: str
    version: str
    capabilities: list[str]
    compatible_slot_types: list[str]
    prompt_path: str        # Path to the agent .md file


@dataclass(frozen=True)
class CapabilityMatch:
    """Result of matching an agent to a slot type."""
    agent_id: str
    prompt_path: str
    matched_capabilities: list[str]     # Capabilities that matched
    missing_capabilities: list[str]     # Required but not present
    is_compatible: bool                 # True if missing is empty


@dataclass
class SlotAssignment:
    """Maps a slot to a specific agent."""
    slot_id: str
    slot_type: str
    agent_id: str
    agent_prompt: str
    reason: str = ""
```

### Consumed by

All other modules import from `models.py`.

---

## 3. Module 2: `loader.py` -- YAML Loading

### Exports

```python
class PipelineLoadError(Exception):
    """Raised when pipeline YAML is malformed or missing required fields."""


class PipelineParameterError(Exception):
    """Raised when a required parameter is not provided."""


class PipelineLoader:
    def load(self, yaml_path: str) -> Pipeline:
        """Parse YAML file into Pipeline object.

        Reads the file, extracts the `pipeline:` top-level key (or bare
        fields if no wrapper key), and hydrates all nested objects.

        Args:
            yaml_path: Absolute or relative path to the pipeline YAML.

        Returns:
            Pipeline object with all fields populated.

        Raises:
            PipelineLoadError: File not found, YAML malformed, or required
                               fields missing (id, name, version, description,
                               created_by, created_at).
        """

    def resolve(self, pipeline: Pipeline, params: dict[str, Any]) -> Pipeline:
        """Replace {parameter} placeholders with concrete values.

        Walks all string fields in the Pipeline and its nested objects,
        replacing `{param_name}` with the corresponding value from params.

        Args:
            pipeline: The Pipeline to resolve (not modified).
            params: Parameter name -> value mapping.

        Returns:
            New Pipeline instance with placeholders replaced.

        Raises:
            PipelineParameterError: A required parameter has no value and
                                    no default.
        """

    def load_and_resolve(
        self, yaml_path: str, params: dict[str, Any]
    ) -> Pipeline:
        """Convenience: load() then resolve().

        Args:
            yaml_path: Path to pipeline YAML.
            params: Parameter values.

        Returns:
            Resolved Pipeline object.

        Raises:
            PipelineLoadError: Loading failed.
            PipelineParameterError: Parameter resolution failed.
        """
```

### Implementation Constraints

- Always use `yaml.safe_load()` (never `yaml.load()`)
- Handle both `pipeline:` wrapper key and bare pipeline fields
- Parameter resolution: `re.sub(r'\{(\w+)\}', replacer, value)` for all strings
- Type conversion for params: `int("42")`, `bool("true"/"false")`
- Return new dataclass instances (never mutate input)

### Consumed by

- `runner.py`: loads pipeline definitions
- `nl_matcher.py`: loads template metadata

---

## 4. Module 3: `validator.py` -- DAG Validation

### Exports

```python
@dataclass
class ValidationResult:
    """Result of pipeline validation."""
    is_valid: bool
    errors: list[str]       # Blocking issues (pipeline cannot run)
    warnings: list[str]     # Non-blocking advisories


class PipelineCycleError(Exception):
    """Raised when dependency graph has a cycle."""


class PipelineValidator:
    def __init__(self, project_root: str):
        """
        Args:
            project_root: Root directory for file existence checks.
        """

    def validate(self, pipeline: Pipeline) -> ValidationResult:
        """Run all validation checks on a pipeline.

        Checks performed (in order):
        1. unique_slot_ids     -- No duplicate slot IDs
        2. valid_dependencies  -- All depends_on reference existing slots
        3. dag_acyclic         -- No dependency cycles
        4. io_compatible       -- Every data_flow input has a matching output
        5. terminal_slot       -- At least one slot has no dependents

        Returns:
            ValidationResult with collected errors and warnings.
        """

    def check_dag(self, slots: list[Slot]) -> list[str]:
        """Check for dependency cycles using Kahn's algorithm.

        Args:
            slots: List of Slot objects.

        Returns:
            List of error messages. Empty = no cycles.
        """

    def topological_sort(self, slots: list[Slot]) -> list[str]:
        """Return slot IDs in valid execution order.

        Uses Kahn's algorithm. Slots with no dependencies come first.
        Among slots at the same level, order is stable (insertion order).

        Args:
            slots: List of Slot objects.

        Returns:
            List of slot IDs in topological order.

        Raises:
            PipelineCycleError: Dependency cycle detected.
        """

    def check_io_compatibility(self, pipeline: Pipeline) -> list[str]:
        """Verify every data_flow edge has a matching producer output.

        For each DataFlowEdge:
        - from_slot must exist
        - to_slot must exist
        - from_slot must have an output with matching artifact name

        Returns:
            List of error messages. Empty = all compatible.
        """

    def check_slot_types(
        self, pipeline: Pipeline, registry: "SlotRegistry"
    ) -> list[str]:
        """Verify all slot_type references exist in the registry.

        Args:
            pipeline: Pipeline to check.
            registry: SlotRegistry with loaded slot types.

        Returns:
            List of error messages for missing slot types.
        """
```

### Implementation Constraints

- Kahn's algorithm for topological sort (see `architect/architecture.md` Section 3.2)
- Build adjacency map from both `depends_on` and `data_flow` edges
- `check_slot_types` accepts a `SlotRegistry` instance (imported at call site, not at module level, to avoid circular imports)

### Consumed by

- `runner.py`: validates before execution

---

## 5. Module 4: `state.py` -- State Tracking

### Exports

```python
class PipelineStateTracker:
    def __init__(self, state_dir: str):
        """
        Args:
            state_dir: Directory for state YAML files (e.g., state/active/).
        """

    def init_state(
        self, pipeline: Pipeline, params: dict[str, Any]
    ) -> PipelineState:
        """Create initial state for a pipeline run.

        - Sets all slots to PENDING
        - Computes definition_hash (sha256 of pipeline YAML serialization)
        - Stores resolved parameter values
        - Saves state file to state_dir
        - Returns the new state

        File name: {pipeline.id}-{ISO-timestamp}.state.yaml
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
        """Update a slot's status and persist.

        Timestamp behavior:
        - started_at set when status changes to IN_PROGRESS
        - completed_at set when status changes to COMPLETED/FAILED/SKIPPED

        Args:
            state: Current pipeline state (modified in place AND saved).
            slot_id: Which slot to update.
            status: New status.
            error: Error message (for FAILED status).
            agent_id: Agent assigned to this slot.
            agent_prompt: Path to agent .md file.
            pre_check_results: Results of pre-condition evaluation.
            post_check_results: Results of post-condition evaluation.

        Returns:
            Updated PipelineState.

        Raises:
            KeyError: slot_id not found in state.
        """

    def get_ready_slots(
        self, pipeline: Pipeline, state: PipelineState
    ) -> list[str]:
        """Find slots whose dependencies are all met.

        A slot is ready when:
        1. Its status is PENDING or BLOCKED
        2. All slots in its depends_on are COMPLETED
        3. All data_flow source slots are COMPLETED

        Args:
            pipeline: Pipeline definition (for dependency info).
            state: Current state (for slot statuses).

        Returns:
            List of slot IDs that are ready to execute.
        """

    def is_complete(self, state: PipelineState) -> bool:
        """True if all slots are in a terminal state (COMPLETED/SKIPPED/FAILED)."""

    def get_status_summary(self, state: PipelineState) -> dict:
        """Human-readable summary.

        Returns:
            {
                "pipeline_id": str,
                "status": str,
                "progress": "3/7 slots completed",
                "completed": [slot_ids...],
                "in_progress": [slot_ids...],
                "ready": [slot_ids...],
                "blocked": [slot_ids...],
                "pending": [slot_ids...],
                "failed": [slot_ids...],
                "skipped": [slot_ids...],
            }
        """

    def save(self, state: PipelineState) -> str:
        """Persist state to YAML file. Returns file path.

        Writes atomically: write to temp file, then os.rename().
        Uses yaml.safe_dump(default_flow_style=False).
        """

    def load(self, state_path: str) -> PipelineState:
        """Load state from YAML file.

        Returns:
            PipelineState hydrated from YAML.

        Raises:
            FileNotFoundError: state_path does not exist.
            yaml.YAMLError: YAML is malformed.
        """

    def archive(self, state: PipelineState) -> str:
        """Move state file from active/ to archive/. Returns new path."""
```

### Implementation Constraints

- State files written with `yaml.safe_dump(default_flow_style=False)`
- `definition_hash`: sha256 of `yaml.safe_dump(pipeline.__dict__)` -- deterministic
- Atomic writes: write to `{path}.tmp`, then `os.rename()`
- `get_ready_slots` must consider BOTH `depends_on` AND `data_flow` source slots
- `archive()` moves file from `state_dir` to `state_dir/../archive/`

### Consumed by

- `runner.py`: all state operations go through StateTracker
- `gate_checker.py`: reads state for `slot_completed` checks

---

## 6. Module 5: `slot_registry.py` -- SlotType Registry

### Exports

```python
class SlotTypeNotFoundError(Exception):
    """Raised when a requested slot type does not exist in the registry."""


class SlotManifest:
    """List of slots and their required capabilities, for HR to fill."""
    pipeline_id: str
    slots: list[dict]       # [{slot_id, slot_type, required_capabilities}]


class SlotRegistry:
    def __init__(self, slot_types_dir: str, agents_dir: str):
        """
        Args:
            slot_types_dir: Directory containing SlotType YAML files
                            (e.g., specs/pipelines/slot-types/).
            agents_dir: Directory containing agent .md files
                        (e.g., agents/).
        """

    def load_slot_types(self) -> dict[str, SlotTypeDefinition]:
        """Load all .yaml files from slot_types_dir.

        Scans the directory, parses each YAML file, and constructs
        SlotTypeDefinition objects.

        Returns:
            Dict mapping slot type ID -> SlotTypeDefinition.

        Raises:
            yaml.YAMLError: A YAML file is malformed.
            KeyError: A YAML file is missing required fields.
        """

    def load_agent_capabilities(self) -> dict[str, AgentCapabilities]:
        """Parse YAML front-matter from all agent .md files.

        Front-matter is the YAML block between --- delimiters at the
        start of the file. Extracts agent_id, version, capabilities,
        and compatible_slot_types.

        Returns:
            Dict mapping agent_id -> AgentCapabilities.
        """

    def get_slot_type(self, slot_type_id: str) -> SlotTypeDefinition:
        """Look up a slot type by ID.

        Args:
            slot_type_id: The slot type ID (e.g., "designer").

        Returns:
            SlotTypeDefinition.

        Raises:
            SlotTypeNotFoundError: ID not found in registry.
        """

    def find_compatible_agents(
        self, slot_type_id: str
    ) -> list[CapabilityMatch]:
        """Find all agents whose capabilities satisfy a slot type.

        Matching rule:
            agent.capabilities SUPERSET_OF slot_type.required_capabilities

        Args:
            slot_type_id: The slot type to match against.

        Returns:
            List of CapabilityMatch objects, sorted by number of
            matched capabilities (descending). Includes both compatible
            and incompatible agents (check is_compatible field).
        """

    def validate_assignment(
        self, slot_type_id: str, agent_id: str
    ) -> CapabilityMatch:
        """Check if a specific agent can fill a specific slot type.

        Args:
            slot_type_id: The slot type.
            agent_id: The agent to check.

        Returns:
            CapabilityMatch with is_compatible=True/False.

        Raises:
            SlotTypeNotFoundError: slot_type_id not found.
            KeyError: agent_id not found.
        """

    def generate_slot_manifest(self, pipeline: Pipeline) -> SlotManifest:
        """Generate a slot manifest for HR to fill.

        Lists all slots in the pipeline with their type and required
        capabilities.

        Args:
            pipeline: Pipeline definition.

        Returns:
            SlotManifest object.
        """
```

### Implementation Constraints

- YAML front-matter parsing: read file, find content between first `---` and second `---`, pass to `yaml.safe_load()`
- `load_slot_types()` and `load_agent_capabilities()` should be called once at init and cached
- Capability matching is set containment: `set(required) <= set(agent_caps)`
- `find_compatible_agents()` returns ALL agents with match info (not just compatible ones) so callers can see what is missing

### Consumed by

- `validator.py`: `check_slot_types()` calls `get_slot_type()`
- `runner.py`: uses registry for slot type lookups and assignment validation

---

## 7. Module 6: `gate_checker.py` -- Condition Evaluation

### Exports

```python
class GateChecker:
    def __init__(self, project_root: str):
        """
        Args:
            project_root: Root directory for resolving relative file paths.
        """

    def check_pre_conditions(
        self, slot: Slot, pipeline_state: PipelineState
    ) -> list[GateCheckResult]:
        """Evaluate all pre-conditions for a slot.

        Dispatches each Gate to the appropriate checker based on gate.type.

        Args:
            slot: The slot whose pre-conditions to check.
            pipeline_state: Current pipeline state.

        Returns:
            List of GateCheckResult (one per condition).
            Never raises -- errors become passed=False results.
        """

    def check_post_conditions(
        self, slot: Slot, pipeline_state: PipelineState
    ) -> list[GateCheckResult]:
        """Evaluate all post-conditions for a slot.

        Same dispatch logic as check_pre_conditions.
        """

    def all_passed(self, results: list[GateCheckResult]) -> bool:
        """Return True if every result in the list has passed=True.

        Returns True for an empty list (no conditions = vacuously true).
        """

    # --- Individual checkers ---

    def check_file_exists(self, target: str) -> GateCheckResult:
        """Check if file exists at project_root/target.

        Args:
            target: Relative file path.

        Returns:
            GateCheckResult with passed=True if file exists.
        """

    def check_slot_completed(
        self, target: str, state: PipelineState
    ) -> GateCheckResult:
        """Check if slot with given ID has status COMPLETED.

        Args:
            target: Slot ID to check.
            state: Current pipeline state.

        Returns:
            GateCheckResult with passed=True if slot is COMPLETED.
        """

    def check_delivery_valid(self, target: str) -> GateCheckResult:
        """Validate a DELIVERY.yaml file using delivery-schema.py.

        Attempts to import and call validate_delivery() from
        specs/delivery-schema.py. If import fails or validation
        returns errors, result is passed=False.

        Args:
            target: Relative path to DELIVERY.yaml.

        Returns:
            GateCheckResult.
        """

    def check_review_valid(self, target: str) -> GateCheckResult:
        """Validate a REVIEW.yaml file using delivery-schema.py.

        Same approach as check_delivery_valid but calls validate_review().

        Args:
            target: Relative path to REVIEW.yaml.

        Returns:
            GateCheckResult.
        """

    def check_tests_pass(self, target: str) -> GateCheckResult:
        """Check if tests in target directory pass.

        Runs: python -m pytest {target} --tb=no -q
        Pass = exit code 0.

        Args:
            target: Relative path to test directory.

        Returns:
            GateCheckResult with stdout summary in evidence.
        """

    def evaluate_custom(self, target: str) -> GateCheckResult:
        """Evaluate a custom expression.

        Supported formats:
        - "yaml_field:<file>:<field_path> <op> <value>"
          e.g., "yaml_field:qa/REVIEW.yaml:verdict != fail"
          Parses YAML, navigates dot-separated field path, compares.
          Operators: ==, !=, >, <, >=, <=

        - "command:<shell_command>"
          e.g., "command:python -m pytest tests/ --tb=no -q"
          Runs subprocess, pass=exit code 0.
          SECURITY: Uses subprocess.run() with shell=False (split args).

        Args:
            target: Expression string.

        Returns:
            GateCheckResult. Never raises.
        """
```

### Implementation Constraints

- **All checkers MUST return GateCheckResult, never raise exceptions.** Errors become `passed=False` with error details in `evidence`.
- File paths resolved as `Path(self.project_root) / target`
- Timestamps: `datetime.now(timezone.utc).isoformat()`
- `evaluate_custom` with `command:` MUST use `subprocess.run(shlex.split(cmd), ...)` with `shell=False`
- For `yaml_field:` parsing: split field path on `.`, navigate nested dicts

### Consumed by

- `runner.py`: calls `check_pre_conditions()` and `check_post_conditions()`

---

## 8. Module 7: `runner.py` -- Pipeline Orchestration

### Exports

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
        state tracker, slot registry, and gate checker.

        Args:
            project_root: Project root directory.
            templates_dir: Directory with pipeline template YAML files.
            state_dir: Directory for state files (state/active/).
            slot_types_dir: Directory with SlotType YAML files.
            agents_dir: Directory with agent .md files.
        """

    def prepare(
        self, yaml_path: str, params: dict[str, Any]
    ) -> tuple[Pipeline, PipelineState]:
        """Load, resolve, validate pipeline, and init state.

        Steps:
        1. loader.load_and_resolve(yaml_path, params)
        2. validator.validate(pipeline) -- raise on errors
        3. validator.check_slot_types(pipeline, registry) -- raise on errors
        4. state_tracker.init_state(pipeline, params)

        Returns:
            (pipeline, state) tuple ready for execution.

        Raises:
            PipelineLoadError: Loading failed.
            PipelineParameterError: Parameter resolution failed.
            PipelineExecutionError: Validation failed.
        """

    def get_next_slots(
        self, pipeline: Pipeline, state: PipelineState
    ) -> list[Slot]:
        """Get Slot objects that are ready to execute.

        Calls state_tracker.get_ready_slots() and resolves IDs to
        Slot objects from the Pipeline.

        Returns:
            List of Slot objects (not just IDs).
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
        """Start execution of a slot.

        Steps:
        1. Check pre-conditions via gate_checker
        2. If all pass: update status to IN_PROGRESS
        3. If any fail: update status to FAILED with error details

        Args:
            slot: The slot to start.
            pipeline: Pipeline definition.
            state: Current state (modified and saved).
            agent_id: Agent assigned to this slot.
            agent_prompt: Path to agent .md.

        Returns:
            Updated PipelineState.
        """

    def complete_slot(
        self, slot_id: str, pipeline: Pipeline, state: PipelineState
    ) -> PipelineState:
        """Mark a slot as completed after agent finishes.

        Steps:
        1. Find the Slot object by ID
        2. Check post-conditions via gate_checker
        3. If all pass: update status to COMPLETED
        4. If any fail: update status to FAILED

        Returns:
            Updated PipelineState.
        """

    def fail_slot(
        self, slot_id: str, error: str, state: PipelineState
    ) -> PipelineState:
        """Manually mark a slot as failed.

        Args:
            slot_id: Slot to fail.
            error: Error description.
            state: Current state.

        Returns:
            Updated PipelineState.
        """

    def skip_slot(
        self, slot_id: str, state: PipelineState
    ) -> PipelineState:
        """Skip a slot (CEO decision). Dependents are unblocked.

        Returns:
            Updated PipelineState.
        """

    def get_summary(self, state: PipelineState) -> str:
        """Human-readable pipeline status string.

        Format:
            Pipeline: {id} v{version}
            Status: {status}
            Progress: {completed}/{total} slots
            ---
            [COMPLETED] slot-design (designer)
            [IN_PROGRESS] slot-implement (implementer) -- agent: ENG-001
            [BLOCKED] slot-review (reviewer)
            ...
        """

    def resume(
        self, state_path: str
    ) -> tuple[Pipeline, PipelineState]:
        """Resume a pipeline from a saved state file.

        Steps:
        1. Load state from state_path
        2. Re-load pipeline YAML (path derived from state)
        3. Verify definition_hash matches
        4. Return (pipeline, state)

        Raises:
            PipelineExecutionError: Hash mismatch (pipeline was modified).
        """
```

### Implementation Constraints

- Runner is the only module that instantiates other modules (loader, validator, etc.)
- All state mutations go through `state_tracker` (never modify PipelineState directly)
- `get_summary()` output must be suitable for CEO review (clear, tabular)
- `resume()` must verify `definition_hash` to detect pipeline tampering

### Consumed by

- `__init__.py`: re-exports PipelineRunner as the main public API

---

## 9. Module 8: `nl_matcher.py` -- Template Matching

### Exports

```python
@dataclass(frozen=True)
class TemplateMatch:
    """Result of matching a natural language input to a template."""
    template_id: str
    template_path: str
    confidence: float       # 0.0 - 1.0
    matched_keywords: list[str]
    description: str
    suggested_params: dict[str, Any]


class NLMatcher:
    def __init__(self, templates_dir: str):
        """Load template registry.

        Scans templates_dir for .yaml files and builds keyword/pattern
        index from each template's metadata (id, name, description).

        Args:
            templates_dir: Directory with pipeline template YAML files.
        """

    def match(self, nl_input: str) -> list[TemplateMatch]:
        """Find matching templates for a natural language input.

        Algorithm:
        1. Tokenize input (split on whitespace + punctuation)
        2. For each template, count keyword matches
        3. Score = matched_keywords / total_keywords * weight
        4. Apply regex pattern bonuses
        5. Sort by score descending
        6. Return candidates with confidence > 0.1

        Supports Chinese and English input.

        Args:
            nl_input: Free-text request (e.g., "implement a new feature for X").

        Returns:
            List of TemplateMatch sorted by confidence (descending).
            Empty list if no match found.
        """

    def extract_params(
        self, nl_input: str, template: TemplateMatch
    ) -> dict[str, Any]:
        """Extract parameter values from natural language.

        Pattern-based extraction:
        - r'[A-Z]{2,10}/[A-Z]{2,10}' -> target_symbol
        - Feature/strategy names -> feature_name/strategy_name
        - r'phase[-_]?(\\d+)' or r'阶段\\s*(\\d+)' -> phase_id

        Args:
            nl_input: Original free-text request.
            template: The matched template.

        Returns:
            Dict of extracted params. Missing params keep defaults
            from the template's parameter definitions.
        """

    def generate_summary(
        self, match: TemplateMatch, params: dict[str, Any]
    ) -> str:
        """Generate human-readable pipeline summary for CEO review.

        Format:
            Template: {name} ({id})
            Parameters:
              - feature_name: kline-aggregator
              - phase_id: phase5
            Slots: design -> implement -> review -> approve -> deploy
            Confidence: 0.85
        """
```

### Implementation Constraints

- Template registry built by scanning `templates_dir` at init time
- Hardcoded keyword map per template (see architecture doc)
- No LLM calls -- pure keyword + regex matching
- Must handle Chinese characters in input (Unicode-aware tokenization)

### Consumed by

- `__init__.py`: re-exports NLMatcher

---

## 10. Module 9: `__init__.py` -- Public API

### Exports

```python
"""Pipeline Engine for Agent Team Orchestration.

Usage:
    from src.pipeline import PipelineRunner

    runner = PipelineRunner(
        project_root="/path/to/project",
        templates_dir="/path/to/specs/pipelines/templates",
        state_dir="/path/to/state/active",
        slot_types_dir="/path/to/specs/pipelines/slot-types",
        agents_dir="/path/to/agents",
    )

    pipeline, state = runner.prepare("templates/standard-feature.yaml", params)
    next_slots = runner.get_next_slots(pipeline, state)
    print(runner.get_summary(state))
"""

from src.pipeline.models import (
    ArtifactOutput,
    ArtifactRef,
    ArtifactType,
    AgentCapabilities,
    CapabilityMatch,
    ConditionType,
    DataFlowEdge,
    ExecutionConfig,
    Gate,
    GateCheckResult,
    Parameter,
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotAssignment,
    SlotState,
    SlotStatus,
    SlotTask,
    SlotTypeDefinition,
    ValidationLevel,
)
from src.pipeline.loader import PipelineLoader, PipelineLoadError, PipelineParameterError
from src.pipeline.validator import PipelineValidator, PipelineCycleError, ValidationResult
from src.pipeline.state import PipelineStateTracker
from src.pipeline.slot_registry import SlotRegistry, SlotTypeNotFoundError
from src.pipeline.gate_checker import GateChecker
from src.pipeline.runner import PipelineRunner, PipelineExecutionError
from src.pipeline.nl_matcher import NLMatcher, TemplateMatch

__all__ = [
    # Models
    "ArtifactOutput", "ArtifactRef", "ArtifactType",
    "AgentCapabilities", "CapabilityMatch", "ConditionType",
    "DataFlowEdge", "ExecutionConfig", "Gate", "GateCheckResult",
    "Parameter", "Pipeline", "PipelineState", "PipelineStatus",
    "Slot", "SlotAssignment", "SlotState", "SlotStatus",
    "SlotTask", "SlotTypeDefinition", "ValidationLevel",
    # Loader
    "PipelineLoader", "PipelineLoadError", "PipelineParameterError",
    # Validator
    "PipelineValidator", "PipelineCycleError", "ValidationResult",
    # State
    "PipelineStateTracker",
    # Slot Registry
    "SlotRegistry", "SlotTypeNotFoundError",
    # Gate Checker
    "GateChecker",
    # Runner
    "PipelineRunner", "PipelineExecutionError",
    # NL Matcher
    "NLMatcher", "TemplateMatch",
]
```

---

## 11. Cross-Module Data Flow Summary

```
CEO Request
    |
    v
NLMatcher.match(nl_input)
    |  returns: TemplateMatch
    v
PipelineLoader.load_and_resolve(template_path, params)
    |  returns: Pipeline
    v
PipelineValidator.validate(pipeline)
    |  returns: ValidationResult
    |
PipelineValidator.check_slot_types(pipeline, registry)
    |  returns: list[str] errors
    v
SlotRegistry.generate_slot_manifest(pipeline)
    |  returns: SlotManifest (for HR)
    v
[HR fills slots -> SlotAssignment list]
    |
    v
PipelineStateTracker.init_state(pipeline, params)
    |  returns: PipelineState
    v
PipelineStateTracker.get_ready_slots(pipeline, state)
    |  returns: list[str] slot_ids
    v
GateChecker.check_pre_conditions(slot, state)
    |  returns: list[GateCheckResult]
    v
[Agent executes externally]
    |
    v
GateChecker.check_post_conditions(slot, state)
    |  returns: list[GateCheckResult]
    v
PipelineStateTracker.update_slot(state, slot_id, COMPLETED)
    |  returns: PipelineState
    v
[Loop: get_ready_slots -> execute -> complete until is_complete()]
    |
    v
PipelineStateTracker.archive(state)
```

---

## 12. Error Handling Contract

| Module | Exception | When |
|--------|-----------|------|
| `loader.py` | `PipelineLoadError` | File not found, YAML malformed, missing required fields |
| `loader.py` | `PipelineParameterError` | Required parameter missing, no default |
| `validator.py` | `PipelineCycleError` | Dependency cycle in `topological_sort()` |
| `slot_registry.py` | `SlotTypeNotFoundError` | Slot type ID not in registry |
| `runner.py` | `PipelineExecutionError` | Validation failed, hash mismatch on resume |
| `gate_checker.py` | *(never raises)* | All errors become `GateCheckResult(passed=False)` |
| `state.py` | `KeyError` | Slot ID not found in state |
| `state.py` | `FileNotFoundError` | State file not found on load |

**Rule**: Modules 1-5 raise exceptions for caller to handle. Module 6 (gate_checker) never raises -- it returns structured results. Module 7 (runner) catches internal exceptions and wraps them in `PipelineExecutionError` or propagates as-is.
