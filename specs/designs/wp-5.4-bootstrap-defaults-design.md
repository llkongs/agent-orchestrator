# WP-5.4: Bootstrap defaults/ Directory Design

> Author: ARCH-001
> Date: 2026-02-17
> Status: DESIGN COMPLETE
> For: ENG-001 (implementation)
> Context: Pipeline engine needs sensible default configurations for first-time setup

---

## 1. Problem Statement

When the pipeline engine is first used, it needs:
- Slot type definitions to exist on disk
- Default pipeline templates available
- Default configuration for the runner (timeouts, retry policies, observer settings)
- A known directory structure to be present

Currently there is no automated bootstrap -- the architect manually creates files. This design defines a `defaults/` directory that the pipeline engine can use to self-initialize.

---

## 2. Directory Structure

```
specs/pipelines/
├── defaults/                          # Bootstrap defaults (version-controlled)
│   ├── config.yaml                    # Pipeline engine configuration
│   ├── slot-types/                    # Default slot type definitions
│   │   ├── designer.yaml              # Architecture/design slot
│   │   ├── researcher.yaml            # Research/investigation slot
│   │   ├── implementer.yaml           # Engineering implementation slot
│   │   ├── reviewer.yaml              # QA review slot
│   │   ├── approver.yaml              # CEO/human approval slot
│   │   └── auditor.yaml               # Compliance audit slot (WP-5.2)
│   └── capabilities.yaml             # Capability registry (all known capabilities)
│
├── slot-types/                        # Active slot types (may be customized)
│   └── auditor.yaml                   # (from WP-5.2, can override defaults)
│
├── templates/                         # Pipeline templates (existing)
│   ├── standard-feature.yaml
│   ├── quant-strategy.yaml
│   ├── security-hardening.yaml
│   ├── research-task.yaml
│   └── hotfix.yaml
│
├── schema.yaml                        # Pipeline definition schema
└── implementation-guide.md            # Engineer's implementation reference

state/
├── active/                            # Running pipeline state files
│   └── audit/                         # Compliance audit outputs
└── archive/                           # Completed pipeline records
```

---

## 3. Bootstrap Configuration

### 3.1 `defaults/config.yaml`

```yaml
# Pipeline Engine Configuration
# Version: 1.0
# This file provides default settings for the pipeline engine.
# Override by passing config to PipelineRunner.__init__()

pipeline_engine:
  version: "1.0.0"

  # Directory paths (relative to project root)
  paths:
    templates: "specs/pipelines/templates"
    slot_types: "specs/pipelines/slot-types"
    defaults: "specs/pipelines/defaults"
    active_state: "state/active"
    archive: "state/archive"
    audit_output: "state/active/audit"

  # Execution defaults
  execution:
    default_timeout_hours: 4.0
    max_timeout_hours: 48.0
    default_max_retries: 2
    max_retries_limit: 5

  # Observer configuration
  observers:
    compliance:
      enabled: true                    # Always-on for audit trail
      log_dir: "state/active"
    metrics:
      enabled: false                   # Future: enable when metrics dashboard exists
    dashboard:
      enabled: false                   # Future: enable when pipeline dashboard exists

  # Gate checking
  gates:
    delivery_schema_path: "specs/delivery-schema.py"
    strict_mode: true                  # If true, missing post-conditions = FAIL
    custom_expression_whitelist:
      - "yaml_field:*"                 # Allow YAML field comparisons

  # NL matcher
  nl_matcher:
    enabled: true
    min_confidence: 0.3                # Minimum confidence to suggest a template

  # State management
  state:
    auto_save: true                    # Save state after every step update
    atomic_writes: true                # Write to temp file then rename
```

### 3.2 `defaults/capabilities.yaml`

```yaml
# Capability Registry
# Version: 1.0
# Author: ARCH-001
# Date: 2026-02-17
#
# This file defines all known capabilities in the pipeline system.
# Slot types reference these capabilities in their required_capabilities list.
# Agent .md files declare their capabilities in YAML front-matter.
#
# Capabilities are organized by category for readability.

capabilities:

  # -- Design & Architecture --
  architecture:
    - id: "system_design"
      description: "Can design system architectures with module interfaces and data flow"
    - id: "interface_design"
      description: "Can define typed API interfaces and integration contracts"
    - id: "trade_off_analysis"
      description: "Can evaluate multiple options with structured trade-off matrices"

  # -- Research & Analysis --
  research:
    - id: "web_search"
      description: "Can search the web for industry practices, papers, and frameworks"
    - id: "technical_analysis"
      description: "Can analyze technical systems, codebases, and architectures"
    - id: "market_data_analysis"
      description: "Can analyze financial market data, signals, and patterns"
    - id: "trend_analysis"
      description: "Can identify trends and patterns in data over time"

  # -- Implementation --
  implementation:
    - id: "python_coding"
      description: "Can write production Python code with type hints and async"
    - id: "test_writing"
      description: "Can write pytest tests with fixtures and parametrize"
    - id: "async_programming"
      description: "Can write asyncio-based concurrent code"
    - id: "deployment"
      description: "Can deploy code to remote servers via SSH/rsync"

  # -- Quality & Review --
  quality:
    - id: "code_review"
      description: "Can review code for bugs, style, and correctness"
    - id: "test_execution"
      description: "Can independently run test suites and analyze results"
    - id: "cross_validation"
      description: "Can compare independent metrics against claimed values"
    - id: "security_audit"
      description: "Can audit code and infrastructure for security vulnerabilities"

  # -- Governance & Audit --
  governance:
    - id: "process_audit"
      description: "Can systematically audit process adherence against defined protocols"
    - id: "artifact_validation"
      description: "Can verify artifact existence, format, and schema compliance"
    - id: "noncompliance_tracking"
      description: "Can identify, classify, and track process deviations"
    - id: "gate_verification"
      description: "Can execute gate checklists and produce binary PASS/FAIL verdicts"
    - id: "objective_evaluation"
      description: "Can evaluate work products without bias toward any role"

  # -- Communication --
  communication:
    - id: "structured_report_writing"
      description: "Can produce structured reports in Markdown/YAML format"
    - id: "stakeholder_communication"
      description: "Can communicate findings to technical and non-technical audiences"

  # -- Domain --
  domain:
    - id: "trading_systems"
      description: "Understands trading system architecture, order lifecycle, risk management"
    - id: "crypto_markets"
      description: "Understands cryptocurrency exchange APIs, market microstructure"
    - id: "quantitative_finance"
      description: "Understands quantitative trading strategies, backtesting, signals"
```

### 3.3 Default Slot Type Definitions

Each file in `defaults/slot-types/` follows the same schema as `auditor.yaml` (WP-5.2). Here are the core five plus auditor:

**`defaults/slot-types/designer.yaml`** (summary):
```yaml
slot_type:
  id: "designer"
  name: "Architecture Designer"
  category: "design"
  required_capabilities:
    - "system_design"
    - "interface_design"
    - "trade_off_analysis"
    - "structured_report_writing"
```

**`defaults/slot-types/researcher.yaml`** (summary):
```yaml
slot_type:
  id: "researcher"
  name: "Research Analyst"
  category: "research"
  required_capabilities:
    - "web_search"
    - "technical_analysis"
    - "structured_report_writing"
```

**`defaults/slot-types/implementer.yaml`** (summary):
```yaml
slot_type:
  id: "implementer"
  name: "Software Engineer"
  category: "implementation"
  required_capabilities:
    - "python_coding"
    - "test_writing"
    - "async_programming"
```

**`defaults/slot-types/reviewer.yaml`** (summary):
```yaml
slot_type:
  id: "reviewer"
  name: "QA Reviewer"
  category: "quality"
  required_capabilities:
    - "code_review"
    - "test_execution"
    - "cross_validation"
    - "structured_report_writing"
```

**`defaults/slot-types/approver.yaml`** (summary):
```yaml
slot_type:
  id: "approver"
  name: "Decision Maker"
  category: "governance"
  required_capabilities:
    - "stakeholder_communication"
  constraints:
    - "Human-in-the-loop step -- pipeline pauses for manual decision"
```

**`defaults/slot-types/auditor.yaml`**: Copy of `specs/pipelines/slot-types/auditor.yaml` (WP-5.2).

---

## 4. Bootstrap Logic

### 4.1 Bootstrap Function

Add to `pipeline/runner.py` or new `pipeline/bootstrap.py`:

```python
def bootstrap_pipeline_engine(project_root: str) -> None:
    """Initialize pipeline engine directory structure and defaults.

    Creates required directories and copies default configs if they
    don't exist. Safe to run multiple times (idempotent).

    This should be called once when the pipeline engine is first used.

    Args:
        project_root: Root directory of the project.
    """
    root = Path(project_root)
    defaults_dir = root / "specs" / "pipelines" / "defaults"

    # Create directories
    dirs = [
        root / "state" / "active",
        root / "state" / "active" / "audit",
        root / "state" / "archive",
        root / "specs" / "pipelines" / "slot-types",
        root / "specs" / "pipelines" / "templates",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Copy default slot types if slot-types/ is empty
    slot_types_dir = root / "specs" / "pipelines" / "slot-types"
    default_slots = defaults_dir / "slot-types"
    if default_slots.exists():
        for src_file in default_slots.glob("*.yaml"):
            dst_file = slot_types_dir / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
```

Impact: ~40 LOC.

### 4.2 Auto-Bootstrap in PipelineRunner

```python
class PipelineRunner:
    def __init__(self, project_root: str, ...):
        # ... existing init ...
        # Auto-bootstrap on first use
        bootstrap_pipeline_engine(project_root)
```

---

## 5. Slot Type Loading

### 5.1 SlotTypeRegistry

New file: `pipeline/slot_registry.py` (~60 LOC)

```python
class SlotTypeRegistry:
    """Registry of available slot types loaded from YAML files."""

    def __init__(self, slot_types_dir: str, defaults_dir: str | None = None):
        """Load slot types from directory.

        Loads from slot_types_dir first, then fills in any missing
        types from defaults_dir.
        """

    def get(self, slot_type_id: str) -> dict | None:
        """Get slot type definition by ID."""

    def list_all(self) -> list[str]:
        """List all registered slot type IDs."""

    def check_capability_match(
        self, slot_type_id: str, agent_capabilities: list[str]
    ) -> tuple[bool, list[str]]:
        """Check if agent capabilities satisfy slot type requirements.

        Returns:
            (is_match, missing_capabilities)
        """
```

---

## 6. Total Impact

| File | Type | LOC |
|------|------|-----|
| `defaults/config.yaml` | New config | ~60 |
| `defaults/capabilities.yaml` | New registry | ~80 |
| `defaults/slot-types/designer.yaml` | New slot type | ~40 |
| `defaults/slot-types/researcher.yaml` | New slot type | ~40 |
| `defaults/slot-types/implementer.yaml` | New slot type | ~40 |
| `defaults/slot-types/reviewer.yaml` | New slot type | ~40 |
| `defaults/slot-types/approver.yaml` | New slot type | ~30 |
| `defaults/slot-types/auditor.yaml` | Copy of WP-5.2 | ~90 |
| `pipeline/bootstrap.py` | New Python | ~40 |
| `pipeline/slot_registry.py` | New Python | ~60 |
| **Total** | | **~520** |

---

## 7. Backward Compatibility

- All defaults are fallbacks -- explicit configuration always wins
- Existing pipelines without slot types work unchanged (they use `role:` directly)
- Bootstrap is idempotent -- running it on an existing setup changes nothing
- No existing files are modified by bootstrap
