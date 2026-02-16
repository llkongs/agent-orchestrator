# Agent Orchestrator -- Project Architecture

> Version: 1.0.0
> Date: 2026-02-16
> Author: ARCH-001 (Pipeline Architect)
> Status: ACTIVE
> References:
>   - `specs/research/pluggable-pipeline-research.md` -- Industry research
>   - `specs/pipelines/schema.yaml` -- Pipeline schema (prior design, superseded by this doc)
>   - `specs/pipelines/implementation-guide.md` -- Module specs (prior design, superseded)
>   - `specs/delivery-protocol.md` -- Delivery/review protocol (unchanged)

---

## 1. System Vision

**Agent Orchestrator** is a pluggable, Lego-like universal pipeline engine for multi-agent development workflows.

The core insight: **Topology and personnel are orthogonal concerns.** An Architect designs a pipeline as a DAG of typed *slots* connected by data flow edges. An HR agent fills each slot with a compatible agent by matching capabilities. Swapping an agent never requires changing the pipeline definition. Swapping the pipeline never requires changing the agents.

Mental model: Unix pipes. Each slot has a standardized input and output schema. Any agent that conforms to the slot's interface contract can be plugged in, just as any Unix command that reads stdin/writes stdout can replace another in a pipeline.

### 1.1 What This System IS

- A YAML-driven DAG workflow engine that validates, orchestrates, and tracks multi-agent pipelines.
- A slot-based architecture where pipeline definitions reference slot *types*, not specific agents.
- A protocol-driven system where every agent follows the same slot protocol: read input, execute, write output.
- A filesystem-based artifact passing system with typed message envelopes for schema enforcement.

### 1.2 What This System is NOT

- NOT an LLM inference engine. Agent execution happens externally (Claude Code CLI, Agent Teams).
- NOT a distributed system. All agents run on a single machine via Agent Teams.
- NOT a real-time streaming platform. Pipelines run at human timescales (minutes to hours per step).
- NOT a general-purpose workflow engine. It is purpose-built for multi-agent software development workflows.

### 1.3 Design Principles

1. **Interface-first**: Slot types define contracts (input/output schemas + capabilities). Agents are implementations.
2. **Validate early, fail fast**: DAG acyclicity, I/O compatibility, and capability matching are checked before execution begins.
3. **Explicit over implicit**: All state transitions, data flows, and conditions are declared in YAML. No hidden behaviors.
4. **Minimum viable schema**: Start with what is needed. Add fields only when a concrete use case demands them.
5. **Correctness > Simplicity > Extensibility > Performance > Elegance**.

---

## 2. Core Abstractions

### 2.1 Concept Map

```
Pipeline (top-level container)
  |
  +-- Slot[] (typed placeholders in the DAG)
  |     |
  |     +-- SlotType (interface contract: input_schema, output_schema, required_capabilities)
  |     +-- SlotAssignment (filled by HR: maps slot -> agent .md)
  |
  +-- DataFlow[] (edges in the DAG: from_slot -> to_slot, artifact name)
  |
  +-- Gate[] (pre/post conditions between slots)
  |
  +-- Parameter[] (user-supplied values resolved at instantiation)
  |
  +-- Execution (timeout, retry, parallel groups)

SlotType Registry (YAML files defining all available slot types)

Agent Definition (.md file with YAML front-matter declaring capabilities)

Artifact (typed file produced by a slot, consumed by downstream slots)

PipelineState (runtime tracking: per-slot status, timestamps, gate results)
```

### 2.2 Pipeline

The top-level container. A YAML file defining:

- **Identity**: id (kebab-case), name, version (semver), description
- **Parameters**: User-supplied values that get resolved into slot tasks and paths
- **Slots**: Ordered list of typed placeholders forming a DAG
- **Data flow**: Edges connecting slot outputs to slot inputs
- **Execution constraints**: Parallel groups, timeouts, retry policies

A Pipeline is a *template* (reusable across projects). A Pipeline *Instance* is a concrete run with resolved parameters and assigned agents.

### 2.3 Slot

A typed placeholder in the pipeline DAG. A slot says *what kind of work* needs to happen, not *who* does it.

Fields:

```python
@dataclass
class Slot:
    id: str                        # Unique within pipeline (kebab-case)
    slot_type: str                 # References a SlotType id
    name: str                      # Human-readable label
    task: SlotTask                 # What the agent must accomplish
    pre_conditions: list[Gate]     # Must pass before slot starts
    post_conditions: list[Gate]    # Must pass after slot completes
    execution: ExecutionConfig     # Timeout, retry, parallel group
```

Key constraint: **Slots never reference agent IDs or agent prompt paths.** Those are resolved at assignment time.

### 2.4 SlotType

The interface contract that defines what a slot expects and produces. Stored as YAML in `specs/pipelines/slot-types/`.

Fields:

```yaml
slot_type:
  id: "implementer"                     # kebab-case identifier
  name: "Code Implementer"              # Human-readable
  category: "engineering"               # Functional grouping
  description: "Writes production code and tests per a design specification"

  input_schema:
    type: object
    required: [design_doc]
    properties:
      design_doc:
        type: string
        description: "Path to the design document"
      integration_contract:
        type: string
        description: "Path to the integration contract"

  output_schema:
    type: object
    required: [delivery_yaml]
    properties:
      delivery_yaml:
        type: string
        description: "Path to DELIVERY.yaml"
      source_dir:
        type: string
        description: "Path to source code directory"
      test_dir:
        type: string
        description: "Path to test directory"

  required_capabilities:
    - python_development
    - test_writing
    - delivery_protocol

  constraints:
    - "Must follow integration contract interfaces"
    - "Must produce DELIVERY.yaml per delivery protocol"
```

Matching rule: **An agent can fill a slot iff `agent.capabilities SUPERSET_OF slot_type.required_capabilities`.**

### 2.5 SlotAssignment

The mapping from slots to agents, produced by HR and reviewed by CEO. Stored as YAML alongside the pipeline instance.

```yaml
assignments:
  - slot_id: "slot-implement"
    slot_type: "implementer"
    agent_id: "ENG-001"
    agent_prompt: "agents/02-engineer-agent.md"
    reason: "Primary engineer, familiar with codebase"
```

### 2.6 DataFlow

An edge in the pipeline DAG. Connects one slot's output artifact to another slot's input.

```yaml
data_flow:
  - from_slot: "slot-design"
    to_slot: "slot-implement"
    artifact: "design_doc"
    required: true
```

The engine uses data flow edges (plus explicit `depends_on` if needed) to compute execution order via topological sort.

### 2.7 Gate

A pre-condition or post-condition on a slot. Gates are evaluated by the GateChecker before/after slot execution.

Condition types:

| Type | Description | Target |
|------|-------------|--------|
| `file_exists` | File exists at path | Relative file path |
| `delivery_valid` | `validate_delivery()` passes | Path to DELIVERY.yaml |
| `review_valid` | `validate_review()` passes | Path to REVIEW.yaml |
| `slot_completed` | Another slot has completed | Slot ID |
| `approval` | Human approval received | Approval identifier |
| `artifact_valid` | Artifact exists and passes validation | Artifact path |
| `tests_pass` | Test suite passes | Test directory path |
| `custom` | Custom expression (yaml_field or command) | Expression string |

### 2.8 Artifact

A typed file produced by one slot and consumed by downstream slots. Artifacts are the data that flows through the pipeline.

Artifact types: `design_doc`, `code`, `test_code`, `delivery_yaml`, `review_yaml`, `config`, `research`, `audit_report`, `agent_prompt`, `approval`, `deployment`, `slot_output`.

Each slot writes its artifacts to a designated output directory. The engine validates artifacts against the slot type's output_schema before passing them downstream.

### 2.9 PipelineState

Runtime tracking for a pipeline instance. Persisted as YAML in `state/active/`.

```python
@dataclass
class PipelineState:
    pipeline_id: str
    pipeline_version: str
    definition_hash: str           # sha256 of pipeline YAML for integrity
    status: PipelineStatus         # loaded|validated|running|paused|completed|failed|aborted
    started_at: str | None
    completed_at: str | None
    parameters: dict[str, Any]     # Resolved parameter values
    slots: dict[str, SlotState]    # Per-slot state
```

Slot state machine:

```
PENDING --> BLOCKED --> READY --> PRE_CHECK --> IN_PROGRESS --> POST_CHECK --> COMPLETED
                                     |              |               |
                                     v              v               v
                                   FAILED        FAILED          FAILED
                                                    |
                                                    v
                                                 RETRYING --> PRE_CHECK (loop)
                                                    |
                                                    v (max retries)
                                                  FAILED

                           Any state --> SKIPPED (CEO decision)
```

Pipeline state machine:

```
LOADED --> VALIDATED --> RUNNING --> COMPLETED
              |            |
              v            +---> PAUSED --> RUNNING (resume)
           FAILED          |
                           +---> FAILED
                           |
                           +---> ABORTED (CEO decision)
```

---

## 3. Module Decomposition

The engine is a Python package at `src/pipeline/` with the following modules:

```
src/pipeline/
  __init__.py           # Public API exports
  models.py             # Data models (dataclasses + enums)
  loader.py             # YAML loading + parameter resolution
  validator.py          # DAG validation + I/O compatibility
  gate_checker.py       # Pre/post condition evaluation
  state.py              # State tracking + persistence
  slot_registry.py      # SlotType loading + agent matching
  runner.py             # Pipeline orchestration
  nl_matcher.py         # Natural language -> template matching
```

### 3.1 Module Dependency Graph

```
models.py (zero deps -- foundation)
    ^
    |
    +--- loader.py (depends on models)
    |
    +--- validator.py (depends on models)
    |
    +--- state.py (depends on models)
    |
    +--- slot_registry.py (depends on models)
    |
    +--- gate_checker.py (depends on models, state)
    |
    +--- nl_matcher.py (depends on models, loader)
    |
    +--- runner.py (depends on ALL above)
```

### 3.2 Module Responsibilities

#### Module 1: `models.py` -- Data Models (~200 LOC)

Pure data containers. No logic beyond construction and serialization.

Defines:
- **Enums**: `SlotStatus`, `PipelineStatus`, `ArtifactType`, `ConditionType`, `PostConditionType`, `ValidationLevel`
- **Frozen dataclasses**: `Parameter`, `ArtifactRef`, `ArtifactOutput`, `Gate`
- **Mutable dataclasses**: `SlotTask`, `ExecutionConfig`, `Slot`, `DataFlowEdge`, `Pipeline`
- **State dataclasses**: `GateCheckResult`, `SlotState`, `PipelineState`
- **Slot system**: `SlotTypeDefinition`, `SlotAssignment`, `CapabilityMatch`

Key design choice: Slots replace the prior "Step" concept. The `Slot` dataclass has a `slot_type` field (string referencing a SlotType id) instead of `role` and `agent_prompt`. Agent assignment is resolved separately.

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
```

#### Module 2: `loader.py` -- YAML Loading (~150 LOC)

Loads pipeline YAML files and hydrates them into `Pipeline` objects. Resolves `{parameter}` placeholders.

Interface:

```python
class PipelineLoadError(Exception): ...
class PipelineParameterError(Exception): ...

class PipelineLoader:
    def load(self, yaml_path: str) -> Pipeline:
        """Parse YAML into Pipeline object."""

    def resolve(self, pipeline: Pipeline, params: dict[str, Any]) -> Pipeline:
        """Replace {param} placeholders. Returns new Pipeline (immutable transform)."""

    def load_and_resolve(self, yaml_path: str, params: dict[str, Any]) -> Pipeline:
        """Convenience: load() then resolve()."""
```

Implementation notes:
- Always `yaml.safe_load()` (never `yaml.load()`)
- Handle both `pipeline:` wrapper key and bare pipeline fields
- Parameter resolution via `re.sub(r'\{(\w+)\}', replacer, string)`
- Return new dataclass instances (pure function)

#### Module 3: `validator.py` -- DAG Validation (~220 LOC)

Validates pipeline structural correctness.

Interface:

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]

class PipelineCycleError(Exception): ...

class PipelineValidator:
    def __init__(self, project_root: str): ...

    def validate(self, pipeline: Pipeline) -> ValidationResult:
        """Run all validation checks."""

    def check_dag(self, slots: list[Slot]) -> list[str]:
        """Check for dependency cycles (Kahn's algorithm)."""

    def topological_sort(self, slots: list[Slot]) -> list[str]:
        """Return slot IDs in execution order. Raises on cycle."""

    def check_io_compatibility(self, pipeline: Pipeline) -> list[str]:
        """Verify every data_flow edge has matching producer output."""

    def check_slot_types(self, pipeline: Pipeline, registry: SlotRegistry) -> list[str]:
        """Verify all slot_type references exist in the registry."""
```

Validation rules:
1. **Unique slot IDs** -- no duplicates
2. **Valid dependencies** -- all `depends_on` reference existing slot IDs
3. **DAG acyclicity** -- no dependency cycles (Kahn's algorithm)
4. **I/O compatibility** -- every data_flow input references an existing slot output
5. **Slot type existence** -- all `slot_type` references exist in the slot type registry
6. **Terminal slot** -- at least one slot has no dependents
7. **Post-condition rules** -- implement-category slots have `delivery_valid` post-condition; review-category slots have `review_valid` post-condition

#### Module 4: `gate_checker.py` -- Condition Evaluation (~200 LOC)

Evaluates pre-conditions and post-conditions for slots.

Interface:

```python
class GateChecker:
    def __init__(self, project_root: str): ...

    def check_pre_conditions(self, slot: Slot, state: PipelineState) -> list[GateCheckResult]: ...
    def check_post_conditions(self, slot: Slot, state: PipelineState) -> list[GateCheckResult]: ...
    def all_passed(self, results: list[GateCheckResult]) -> bool: ...

    # Individual checkers:
    def check_file_exists(self, target: str) -> GateCheckResult: ...
    def check_slot_completed(self, target: str, state: PipelineState) -> GateCheckResult: ...
    def check_delivery_valid(self, target: str) -> GateCheckResult: ...
    def check_review_valid(self, target: str) -> GateCheckResult: ...
    def evaluate_custom(self, target: str) -> GateCheckResult: ...
```

Design: All checkers return `GateCheckResult` (never raise). Failed conditions return `passed=False` with error in `evidence`.

Custom expressions:
- `yaml_field:<file>:<field_path> <op> <value>` -- parse YAML, navigate path, compare
- `command:<shell_command>` -- run subprocess, pass=exit 0 (SECURITY: whitelist only)

#### Module 5: `state.py` -- State Tracking (~180 LOC)

Manages pipeline runtime state: slot statuses, timestamps, gate results. Persists to YAML files.

Interface:

```python
class PipelineStateTracker:
    def __init__(self, state_dir: str): ...

    def init_state(self, pipeline: Pipeline, params: dict[str, Any]) -> PipelineState: ...
    def update_slot(self, state: PipelineState, slot_id: str, status: SlotStatus, **kwargs) -> PipelineState: ...
    def get_ready_slots(self, pipeline: Pipeline, state: PipelineState) -> list[str]: ...
    def is_complete(self, state: PipelineState) -> bool: ...
    def get_status_summary(self, state: PipelineState) -> dict: ...
    def save(self, state: PipelineState) -> str: ...
    def load(self, state_path: str) -> PipelineState: ...
    def archive(self, state: PipelineState) -> str: ...
```

State files: `{pipeline_id}-{timestamp}.state.yaml`, written atomically (temp + rename).

A slot is "ready" when: (1) its status is PENDING or BLOCKED, (2) all slots in `depends_on` are COMPLETED, and (3) all data_flow source slots are COMPLETED.

#### Module 6: `slot_registry.py` -- SlotType Loading + Agent Matching (~180 LOC)

**This is the key new module** that enables the pluggable slot architecture. Loads SlotType definitions, loads agent capability metadata, and matches agents to slots.

Interface:

```python
class SlotRegistry:
    def __init__(self, slot_types_dir: str, agents_dir: str): ...

    def load_slot_types(self) -> dict[str, SlotTypeDefinition]:
        """Load all .yaml files from slot_types_dir."""

    def load_agent_capabilities(self) -> dict[str, AgentCapabilities]:
        """Parse YAML front-matter from all agent .md files in agents_dir."""

    def get_slot_type(self, slot_type_id: str) -> SlotTypeDefinition:
        """Look up a slot type by ID. Raises if not found."""

    def find_compatible_agents(self, slot_type_id: str) -> list[CapabilityMatch]:
        """Find all agents whose capabilities satisfy the slot type."""

    def validate_assignment(self, slot_type_id: str, agent_id: str) -> bool:
        """Check if a specific agent can fill a specific slot type."""

    def generate_slot_manifest(self, pipeline: Pipeline) -> SlotManifest:
        """Generate the slot manifest for HR to fill."""
```

Matching algorithm:
```
agent.capabilities SUPERSET_OF slot_type.required_capabilities
```

This is a simple set containment check. An agent with `[a, b, c, d]` can fill a slot that requires `[a, b]`.

#### Module 7: `nl_matcher.py` -- Template Matching (~130 LOC)

Matches natural language CEO requests to pipeline templates. Keyword + pattern based (no LLM).

Interface:

```python
@dataclass(frozen=True)
class TemplateMatch:
    template_id: str
    template_path: str
    confidence: float
    matched_keywords: list[str]
    suggested_params: dict[str, Any]

class NLMatcher:
    def __init__(self, templates_dir: str): ...

    def match(self, nl_input: str) -> list[TemplateMatch]: ...
    def extract_params(self, nl_input: str, template: TemplateMatch) -> dict[str, Any]: ...
    def generate_summary(self, match: TemplateMatch, params: dict[str, Any]) -> str: ...
```

Supports Chinese and English input. Hardcoded keyword maps per template. Regex extraction for symbols (`BTC/USDT`), phase IDs, feature names.

#### Module 8: `runner.py` -- Pipeline Orchestrator (~220 LOC)

The main orchestrator. Ties all modules together. In the initial implementation, the runner manages state and gate checks; actual agent spawning is done by the team lead via Agent Teams.

Interface:

```python
class PipelineRunner:
    def __init__(self, project_root: str, templates_dir: str, state_dir: str): ...

    def prepare(self, yaml_path: str, params: dict[str, Any]) -> tuple[Pipeline, PipelineState]:
        """Load, resolve, validate, init state."""

    def get_next_slots(self, pipeline: Pipeline, state: PipelineState) -> list[Slot]:
        """Get slots ready to execute (deps met, pre-conditions checkable)."""

    def begin_slot(self, slot: Slot, pipeline: Pipeline, state: PipelineState) -> PipelineState:
        """Run pre-conditions, mark IN_PROGRESS."""

    def complete_slot(self, slot_id: str, state: PipelineState) -> PipelineState:
        """Run post-conditions, mark COMPLETED or FAILED."""

    def fail_slot(self, slot_id: str, error: str, state: PipelineState) -> PipelineState: ...
    def skip_slot(self, slot_id: str, state: PipelineState) -> PipelineState: ...

    def get_summary(self, state: PipelineState) -> str:
        """Human-readable status for CEO."""

    def resume(self, state_path: str) -> tuple[Pipeline, PipelineState]:
        """Resume from saved state. Verifies definition hash integrity."""
```

The runner is protocol-driven in v1: the team lead calls `get_next_slots()`, spawns agents, and calls `complete_slot()` when done. Future versions may automate agent spawning.

#### Module 9: `__init__.py` -- Public API

```python
from src.pipeline.models import Pipeline, PipelineState, PipelineStatus, Slot, SlotStatus
from src.pipeline.runner import PipelineRunner
from src.pipeline.validator import PipelineValidator, ValidationResult
from src.pipeline.loader import PipelineLoader
from src.pipeline.gate_checker import GateChecker
from src.pipeline.state import PipelineStateTracker
from src.pipeline.slot_registry import SlotRegistry
from src.pipeline.nl_matcher import NLMatcher
```

### 3.3 LOC Estimates

| Module | Estimated LOC | Priority |
|--------|--------------|----------|
| `models.py` | ~200 | P0 |
| `loader.py` | ~150 | P0 |
| `validator.py` | ~220 | P0 |
| `gate_checker.py` | ~200 | P0 |
| `state.py` | ~180 | P0 |
| `slot_registry.py` | ~180 | P0 |
| `runner.py` | ~220 | P1 |
| `nl_matcher.py` | ~130 | P2 |
| `__init__.py` | ~20 | P0 |
| **Total engine** | **~1500** | |

Plus:
- SlotType YAML definitions (5 core types): ~300 YAML
- Pipeline template updates (5 templates): ~200 YAML modifications
- Test suite: ~1000 LOC across ~90 tests

---

## 4. Interface Contracts Between Modules

### 4.1 Loader -> Validator

```python
# Loader produces Pipeline, Validator consumes it
pipeline: Pipeline = loader.load_and_resolve(yaml_path, params)
result: ValidationResult = validator.validate(pipeline)
```

The `Pipeline` dataclass is the shared contract. Loader guarantees all required fields are present (raises `PipelineLoadError` otherwise). Validator checks structural correctness.

### 4.2 Validator -> SlotRegistry

```python
# Validator calls SlotRegistry to check slot_type references
errors: list[str] = validator.check_slot_types(pipeline, registry)
```

The `SlotRegistry` exposes `get_slot_type(id) -> SlotTypeDefinition` which raises `KeyError` if the type does not exist.

### 4.3 Runner -> StateTracker

```python
# Runner delegates all state mutations to StateTracker
state = tracker.init_state(pipeline, params)
state = tracker.update_slot(state, slot_id, SlotStatus.IN_PROGRESS)
ready = tracker.get_ready_slots(pipeline, state)
```

State mutations always go through `PipelineStateTracker`. The runner never mutates `PipelineState` directly.

### 4.4 Runner -> GateChecker

```python
# Runner calls GateChecker before/after slot execution
pre_results = gate_checker.check_pre_conditions(slot, state)
if gate_checker.all_passed(pre_results):
    # proceed to execution
post_results = gate_checker.check_post_conditions(slot, state)
```

GateChecker returns `list[GateCheckResult]`. It never raises -- errors become `passed=False` results.

### 4.5 SlotRegistry -> Agent .md Files

SlotRegistry parses YAML front-matter from agent .md files:

```yaml
---
agent_id: "ENG-001"
version: "2.1"
capabilities:
  - python_development
  - test_writing
  - delivery_protocol
  - async_programming
compatible_slot_types:
  - implementer
  - deployer
---
```

The `compatible_slot_types` field is advisory (declared by HR). The engine validates it against `required_capabilities` matching.

### 4.6 Slot Protocol (Agent I/O Contract)

Every agent interacting with the pipeline follows this protocol:

```
1. READ  slot-input.yaml    (generated by engine, contains upstream artifacts + task)
2. READ  own .md prompt     (contains role identity + behavioral instructions)
3. EXEC  do work            (read context, produce artifacts)
4. WRITE slot-output.yaml   (conforms to slot type's output_schema)
5. WRITE DELIVERY.yaml      (for implementer/designer slots, per delivery protocol)
```

**slot-input.yaml** format:

```yaml
slot_id: "slot-implement"
slot_type: "implementer"
pipeline_id: "standard-feature-2026-02-16"
timestamp: "2026-02-16T10:00:00Z"

task:
  objective: "Implement kline-aggregator per architecture design"
  constraints: [...]
  deliverables: [...]

inputs:
  design_doc:
    from_slot: "slot-design"
    path: "state/active/artifacts/slot-design/design_doc.md"
  integration_contract:
    from_slot: "slot-design"
    path: "specs/integration-contract.md"

output_requirements:
  schema: "implementer_output_v1"
  required_fields: [delivery_yaml, source_dir, test_dir]
  output_path: "state/active/artifacts/slot-implement/"

agent_prompt: "agents/02-engineer-agent.md"
```

**slot-output.yaml** format:

```yaml
slot_id: "slot-implement"
slot_type: "implementer"
pipeline_id: "standard-feature-2026-02-16"
completed_at: "2026-02-16T18:30:00Z"
status: "completed"

output:
  delivery_yaml: "engineer/DELIVERY.yaml"
  source_dir: "engineer/src/"
  test_dir: "engineer/tests/"

metadata:
  agent_id: "ENG-001"
  execution_time_minutes: 510
```

---

## 5. Data Flow

### 5.1 Pipeline Lifecycle

```
                         YAML Templates
                              |
                              v
 CEO Request -----> NL Matcher -----> Template Selection
                                           |
                                           v
                                   Pipeline Loader
                                     (load + resolve params)
                                           |
                                           v
                                   Pipeline Validator
                                     (DAG check, I/O check, slot type check)
                                           |
                                           v
                                   Slot Registry
                                     (generate slot manifest)
                                           |
                                           v
                                   HR Fills Slots
                                     (slot-assignments.yaml)
                                           |
                                           v
                                   Pipeline Runner
                                     (init state, begin execution)
                                           |
                                           v
                              +--- get_next_slots() ---+
                              |                        |
                              v                        v
                     Slot A (ready)           Slot B (blocked)
                         |
                         v
                   GateChecker (pre-conditions)
                         |
                         v
                   Agent Execution (external: Agent Teams)
                         |
                         v
                   GateChecker (post-conditions)
                         |
                         v
                   State Update (COMPLETED)
                         |
                         v
                   Unblock downstream slots
                         |
                         v
                   Loop until all slots complete
                         |
                         v
                   Pipeline COMPLETED
                         |
                         v
                   State archived
```

### 5.2 Standard Feature Pipeline (DAG)

```
          [slot-design]
          (designer)
               |
               v
          [slot-implement]
          (implementer)
               |
               v
          [slot-review]
          (reviewer)
               |
               v
          [slot-approve]
          (approver)
               |
               v
          [slot-deploy]
          (deployer)
```

### 5.3 Quant Strategy Pipeline (DAG with Parallelism)

```
                    [slot-scope]
                    (designer)
                   /     |     \
                  v      v      v
    [slot-signal]  [slot-market]  (design_brief flows to all 3)
    (researcher)   (researcher)
                  \      |
                   v     v
               [slot-implement]
               (implementer)
                     |
                     v
               [slot-review]
               (reviewer)
                     |
                     v
               [slot-approve]
               (approver)
```

`slot-signal` and `slot-market` are both of type `researcher` but can be filled by different agents (e.g., SIG-001 and STRAT-001).

---

## 6. Extension Points

The architecture is designed for extension without breaking changes.

### 6.1 Adding a New SlotType

1. Create `specs/pipelines/slot-types/{new-type}.yaml` with the required fields
2. The SlotRegistry auto-discovers it on next load
3. HR produces agent .md files with matching capabilities
4. Pipeline templates can reference the new type immediately

No engine code changes required.

### 6.2 Adding a New Gate Type

1. Add the type string to the `ConditionType` or `PostConditionType` enum in `models.py`
2. Add a `check_{type}()` method to `GateChecker`
3. Register it in GateChecker's dispatcher

Requires a small engine code change (~10 lines).

### 6.3 Adding a New Artifact Type

1. Add the type string to the `ArtifactType` enum in `models.py`
2. No other changes needed (artifact types are metadata, not behavior)

### 6.4 Adding a New Pipeline Template

1. Create `specs/pipelines/templates/{template}.yaml` conforming to the schema
2. Add keyword entries to `NLMatcher` for auto-discovery
3. Validate with `PipelineValidator`

No engine code changes required.

### 6.5 Upgrading to Automated Agent Spawning

The `runner.py` `begin_slot()` method currently returns state for manual agent management. To automate:

1. Add an `AgentSpawner` interface in `runner.py`
2. Implement `ClaudeTeamSpawner` that calls Agent Teams API
3. Inject the spawner into `PipelineRunner`
4. `begin_slot()` calls `spawner.spawn(slot, assignment)` instead of returning

This is a backward-compatible addition.

---

## 7. Tech Stack and Constraints

### 7.1 Dependencies

**Required:**
- Python 3.11+ (dataclasses, StrEnum, `str | None` syntax)
- PyYAML (`yaml.safe_load`, `yaml.safe_dump`)

**Standard library only:**
- `dataclasses`, `enum`, `typing`, `pathlib`, `hashlib`, `re`, `datetime`, `collections`, `os`, `shutil`, `importlib`, `subprocess`

**Explicitly NOT used:**
- No external validation libraries (jsonschema, pydantic) -- keep it minimal
- No database -- YAML files on filesystem
- No async -- the engine itself is synchronous; agent execution is external
- No network -- all local filesystem

### 7.2 Constraints

1. The pipeline engine is a **standalone package**. It must NOT import from any project-specific modules (trading system, etc.).
2. All YAML operations use `yaml.safe_load()` / `yaml.safe_dump()`. Never `yaml.load()`.
3. State files are written atomically (write temp, rename).
4. No shell=True in subprocess calls within gate_checker.
5. Pipeline definitions are immutable once loaded. Parameter resolution returns a new Pipeline.

### 7.3 Compatibility with Prior Design

The existing `specs/pipelines/schema.yaml` and `specs/pipelines/implementation-guide.md` represent the prior design where steps reference `role: ARCH-001` directly. This architecture supersedes those designs with the slot-based approach.

Key changes from prior design:

| Concept | Prior | New |
|---------|-------|-----|
| Step | `Step` with `role` and `agent_prompt` | `Slot` with `slot_type` |
| Agent binding | Hardcoded in pipeline YAML | Resolved via `SlotAssignment` |
| Data flow | Implicit via `inputs[].from_step` | Explicit `data_flow[]` edges |
| New module | N/A | `slot_registry.py` |
| SlotType | N/A | YAML definitions in `slot-types/` |

The 5 existing pipeline templates will be converted to the new slot-based format. The `implementation-guide.md` will be updated to reflect the new module (`slot_registry.py`) and renamed fields.

---

## 8. Core SlotType Definitions

Five core slot types, sufficient for all 5 existing pipeline templates:

### 8.1 `designer`
- **Category**: architecture
- **Purpose**: Produces design documents, defines interfaces, scopes constraints
- **Required capabilities**: `system_design`, `interface_definition`, `technical_documentation`
- **Input**: requirements or research reports
- **Output**: design document path, interface changes list

### 8.2 `researcher`
- **Category**: research
- **Purpose**: Investigates topics, analyzes data, produces structured reports
- **Required capabilities**: `web_search`, `technical_analysis`, `structured_report_writing`
- **Input**: research brief, context artifacts
- **Output**: research report path, confidence level, key findings

### 8.3 `implementer`
- **Category**: engineering
- **Purpose**: Writes production code and tests per a design specification
- **Required capabilities**: `python_development`, `test_writing`, `delivery_protocol`
- **Input**: design document, integration contract
- **Output**: DELIVERY.yaml path, source directory, test directory

### 8.4 `reviewer`
- **Category**: quality
- **Purpose**: Independently verifies deliveries, produces REVIEW.yaml
- **Required capabilities**: `independent_testing`, `code_review`, `delivery_protocol`, `cross_validation`
- **Input**: DELIVERY.yaml, source code, tests
- **Output**: REVIEW.yaml path, verdict

### 8.5 `approver`
- **Category**: governance
- **Purpose**: Makes Go/No-Go decisions based on review results
- **Required capabilities**: `decision_making`
- **Input**: REVIEW.yaml or research reports
- **Output**: approval decision

Additional slot types can be added as needed (e.g., `auditor`, `deployer`, `signal-expert`). The 5 core types cover 100% of the existing pipeline templates.

---

## 9. Implementation Order

```
Phase 1: Foundation (P0)
  1. models.py + tests         -- Zero deps, everything builds on this
  2. loader.py + tests         -- Depends on models
  3. validator.py + tests      -- Depends on models
  4. state.py + tests          -- Depends on models
  5. slot_registry.py + tests  -- Depends on models
  6. gate_checker.py + tests   -- Depends on models, state

Phase 2: Integration (P1)
  7. runner.py + tests         -- Depends on all Phase 1 modules
  8. Convert 5 pipeline templates to slot-based format
  9. Create 5 core SlotType YAML definitions
  10. Update agent .md front-matter with capabilities

Phase 3: Polish (P2)
  11. nl_matcher.py + tests    -- Depends on models, loader
  12. __init__.py              -- Public API
  13. Integration tests (end-to-end pipeline runs)
```

Each module is independently testable after implementation.

---

## 10. Test Strategy

### 10.1 Test Organization

```
tests/test_pipeline/
  __init__.py
  conftest.py                  # Shared fixtures
  test_models.py               # ~20 tests
  test_loader.py               # ~10 tests
  test_validator.py            # ~15 tests
  test_gate_checker.py         # ~12 tests
  test_state.py                # ~12 tests
  test_slot_registry.py        # ~12 tests
  test_runner.py               # ~12 tests
  test_nl_matcher.py           # ~10 tests
  fixtures/
    valid-pipeline.yaml
    invalid-cycle.yaml
    invalid-io.yaml
    sample-delivery.yaml
    sample-slot-type.yaml
    sample-agent.md
```

### 10.2 Coverage Targets

| Module | Target |
|--------|--------|
| `models.py` | >= 95% |
| `loader.py` | >= 85% |
| `validator.py` | >= 90% |
| `gate_checker.py` | >= 85% |
| `state.py` | >= 90% |
| `slot_registry.py` | >= 90% |
| `runner.py` | >= 80% |
| `nl_matcher.py` | >= 80% |
| **Overall** | >= 85% |

### 10.3 Total Test Count Estimate: ~103 tests

---

## 11. Architectural Decisions Record

### ADR-1: Slots Replace Steps

**Context**: Prior design used "steps" with hardcoded `role` and `agent_prompt` fields. CEO vision requires topology/personnel separation.

**Decision**: Replace `Step` with `Slot` that has `slot_type` instead of `role`/`agent_prompt`. Agent binding happens via `SlotAssignment`.

**Rationale**: Enables the pluggable Lego-like architecture. Pipeline topology is stable; agent personnel is flexible.

**Consequence**: All 5 existing pipeline templates must be converted. Implementation guide must be updated.

### ADR-2: Explicit DataFlow Edges

**Context**: Prior design inferred data flow from `inputs[].from_step`. This was implicit and coupled input/output definitions.

**Decision**: Add explicit `data_flow[]` section to pipeline YAML, listing `{from_slot, to_slot, artifact, required}` edges.

**Rationale**: Makes the DAG visible and machine-parseable. Enables visualization. Separates dependency topology from artifact declarations.

**Consequence**: Slightly more verbose pipeline YAML, but clearer semantics. The `depends_on` field is still supported as a supplementary dependency mechanism.

### ADR-3: SlotType Registry as YAML Files

**Context**: Could define slot types in Python code, in a database, or as YAML files.

**Decision**: YAML files in `specs/pipelines/slot-types/`, one per type.

**Rationale**: YAML is human-readable, version-controllable, and matches the project's file-based philosophy. Adding a new slot type is creating a file, not writing code.

**Consequence**: No code changes needed to add slot types. Registry auto-discovers on load.

### ADR-4: Hybrid Artifact Passing (Filesystem + Typed Envelopes)

**Context**: Three options for inter-agent communication: filesystem, typed messages, or blackboard.

**Decision**: Filesystem artifacts (Pattern A) wrapped in typed envelopes (Pattern B) via slot-input.yaml / slot-output.yaml.

**Rationale**: No new infrastructure. Schema enforcement via typed YAML envelopes. Human-inspectable. Compatible with Claude Code CLI's file-based execution model.

**Consequence**: Each slot gets an artifact directory under `state/active/artifacts/{slot_id}/`.

### ADR-5: No Inheritance for SlotTypes

**Context**: Could use type hierarchy (e.g., `signal_researcher` IS-A `researcher`).

**Decision**: Use flat capability sets. A `signal_researcher` agent has `[web_search, technical_analysis, structured_report_writing, signal_processing]` -- it can fill any slot whose required_capabilities are a subset.

**Rationale**: Set containment is simpler than inheritance. Avoids diamond inheritance problems. A2A protocol uses flat capability lists.

**Consequence**: Some redundancy in capability declarations across agents. Acceptable trade-off for simplicity.

### ADR-6: Synchronous Engine, External Agent Execution

**Context**: Could make the engine async with agent execution built in.

**Decision**: Engine is synchronous Python. Agent execution (Claude Code CLI, Agent Teams) happens externally. Runner tracks state; team lead spawns agents.

**Rationale**: Keeps engine simple. Agent Teams API is the execution substrate. The engine is a state machine, not an execution engine.

**Consequence**: Initial version requires manual agent management by team lead. Automated spawning is a future enhancement (see Extension Points 6.5).

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **Pipeline** | A YAML-defined DAG of slots with data flow and execution constraints |
| **Slot** | A typed placeholder in the DAG that accepts any compatible agent |
| **SlotType** | Interface contract for a slot: input/output schemas + required capabilities |
| **SlotAssignment** | Mapping from slot to agent (produced by HR, reviewed by CEO) |
| **DataFlow** | An edge in the DAG: from_slot.output -> to_slot.input |
| **Gate** | A pre/post condition evaluated before/after slot execution |
| **Artifact** | A typed file produced by one slot and consumed by downstream slots |
| **PipelineState** | Runtime tracking of slot statuses, timestamps, and gate results |
| **SlotManifest** | List of required slot types for HR to fill |
| **Capability** | A discrete skill an agent declares (e.g., `python_development`) |
| **Slot Protocol** | The standardized agent interaction sequence: read input -> execute -> write output |
