# Agent Orchestrator

## 1. Project Identity

Agent Orchestrator is a pluggable, slot-based pipeline engine for multi-agent development workflows.

- **Core insight**: Topology and personnel are orthogonal concerns
- 12 pipeline modules / ~4300 LOC / 400+ tests
- Dependencies: Python 3.11+ / PyYAML only / stdlib only

## 2. Constitution

This project is governed by `constitution.md` (6 Articles). Key rules:

- **Art.1**: CEO coordinates, never codes. Process correctness > speed. User words passed verbatim.
- **Art.2**: Python 3.11+, PyYAML only, zero cross-package imports, immutable pipeline definitions.
- **Art.3**: Slots over steps, interface-first, explicit > implicit, correctness > simplicity > extensibility.
- **Art.4**: DELIVERY.yaml + REVIEW.yaml mandatory, suspicious=true blocks deploy, cross-validation required.
- **Art.5**: kebab-case IDs, snake_case Python, directory write isolation per role.
- **Art.6**: safe_load only, no shell=True, atomic writes, checksum integrity on all deliverables.

Full text: `constitution.md`

## 3. Spec-Driven Workflow

1. **Constitution** -- Read `constitution.md` (non-negotiable constraints)
2. **Specify** -- Write feature spec in `specs/features/{name}.spec.md`
3. **Plan** -- Create implementation plan with phases + dependencies
4. **Tasks** -- Split plan into TaskCreate calls with blockedBy
5. **Implement** -- Code, test, deliver via DELIVERY.yaml

## 4. Context Management (L0/L1/L2)

| Layer | File | Tokens | When to load |
|-------|------|--------|-------------|
| L0 | `.abstract.md` | ~100 | Always (project scan) |
| L1 | `.overview.md` | ~2K | When topic is relevant |
| L2 | Source files | Full | When editing/reviewing |

**Principle**: L0 scan -> L1 understand -> L2 execute. Never start with L2.

### Context Paths

| Directory | `.abstract.md` | `.overview.md` |
|-----------|---------------|----------------|
| `agents/` | `agents/.abstract.md` | `agents/.overview.md` |
| `architect/` | `architect/.abstract.md` | `architect/.overview.md` |
| `engineer/src/pipeline/` | `engineer/src/pipeline/.abstract.md` | `engineer/src/pipeline/.overview.md` |
| `specs/` | `specs/.abstract.md` | `specs/.overview.md` |
| `specs/pipelines/slot-types/` | `specs/pipelines/slot-types/.abstract.md` | `specs/pipelines/slot-types/.overview.md` |
| `specs/pipelines/templates/` | `specs/pipelines/templates/.abstract.md` | `specs/pipelines/templates/.overview.md` |
| `state/` | `state/.abstract.md` | `state/.overview.md` |

## 5. Quick Reference

### Key Paths

- Pipeline engine: `engineer/src/pipeline/`
- Pipeline templates: `specs/pipelines/templates/`
- Slot types: `specs/pipelines/slot-types/`
- Agent prompts: `agents/`
- State: `state/` (active runs and archives)
- Architecture: `architect/architecture.md`
- Delivery protocol: `specs/delivery-protocol.md`

### Run Tests

```bash
cd engineer && PYTHONPATH=src python3 -m pytest tests/test_pipeline/ -v
```

### Module Dependency Graph

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
    +--- slot_contract.py (slot I/O contracts)
    |
    +--- enforcer.py (slot enforcement rules)
    |
    +--- observer.py (compliance observation)
    |
    +--- context_router.py (L0/L1/L2 context routing)
    |
    +--- runner.py (depends on ALL above)
```

### Pipeline Modules (12)

| Module | Responsibility |
|--------|---------------|
| `models.py` | Data models (dataclasses + enums) |
| `loader.py` | YAML loading + parameter resolution |
| `validator.py` | DAG validation + I/O compatibility |
| `gate_checker.py` | Pre/post condition evaluation |
| `state.py` | State tracking + persistence |
| `slot_registry.py` | SlotType loading + agent matching |
| `nl_matcher.py` | Natural language -> template matching |
| `runner.py` | Pipeline orchestration |
| `slot_contract.py` | Slot I/O contract management |
| `enforcer.py` | Slot enforcement rules |
| `observer.py` | Compliance observation |
| `context_router.py` | L0/L1/L2 context routing |

## 6. Quality Gates

- Test coverage >= 85%
- Zero import violations (only stdlib + yaml)
- DELIVERY.yaml required for implementer slots
- REVIEW.yaml required for reviewer slots
- suspicious=true blocks deployment (Constitution SS4.6)
- Checksum integrity on all deliverables (Constitution SS4.3)
- Cross-validation mandatory: QA independently reproduces metrics (Constitution SS4.9)
