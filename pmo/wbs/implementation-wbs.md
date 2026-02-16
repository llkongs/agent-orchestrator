# Work Breakdown Structure -- Pipeline Engine Implementation

> Version: 2.0.0
> Date: 2026-02-17
> Author: PMO-001
> Status: ACTIVE
> Objective: Implement the full pipeline engine per `architect/architecture.md`
> Scope: Phase 1 (Foundation), Phase 2 (Integration), Phase 3 (Polish), Phase 4 (Live Validation), Phase 5 (Governance & Bootstrap)

---

## 1. WBS Overview

```
IMPL-0: Pipeline Engine Implementation
|
+-- IMPL-1: Phase 1 -- Foundation (P0)                    [COMPLETED]
|   +-- WP-1.1: models.py + tests                         [COMPLETED]
|   +-- WP-1.2: loader.py + tests                         [COMPLETED]
|   +-- WP-1.3: validator.py + tests                      [COMPLETED]
|   +-- WP-1.4: state.py + tests                          [COMPLETED]
|   +-- WP-1.5: slot_registry.py + tests                  [COMPLETED]
|   +-- WP-1.6: gate_checker.py + tests                   [COMPLETED]
|   +-- WP-1.7: Phase 1 QA Review                         [COMPLETED -- QA PASS]
|
+-- IMPL-2: Phase 2 -- Integration (P1)                   [COMPLETED]
|   +-- WP-2.1: runner.py + tests                         [COMPLETED]
|   +-- WP-2.2: Convert 5 pipeline templates              [COMPLETED -- ARCH-001]
|   +-- WP-2.3: Update implementation-guide + schema      [COMPLETED -- ARCH-001]
|   +-- WP-2.4: Phase 2 QA Review                         [COMPLETED -- QA PASS]
|
+-- IMPL-3: Phase 3 -- Polish (P2)                        [COMPLETED]
|   +-- WP-3.1: nl_matcher.py + tests                     [COMPLETED]
|   +-- WP-3.2: __init__.py (public API)                  [COMPLETED]
|   +-- WP-3.3: Integration tests (end-to-end)            [COMPLETED]
|   +-- WP-3.4: Phase 3 QA Review + Final Verdict         [COMPLETED -- QA PASS]
|
+-- IMPL-4: Phase 4 -- Live Validation (P0 Final Acceptance)  [COMPLETED]
|   +-- WP-4.1: Pipeline live validation ("Spring Gala")  [COMPLETED -- "万家灯火" GDD delivered]
|
+-- IMPL-5: Phase 5 -- Governance & Bootstrap (P1)            [COMPLETED]
    +-- WP-5.1: Compliance auditor architecture eval           [COMPLETED -- ARCH-001]
    +-- WP-5.2: auditor SlotType YAML                          [COMPLETED -- ARCH-001]
    +-- WP-5.3: compliance-audit pipeline template             [COMPLETED -- ARCH-001]
    +-- WP-5.4: Bootstrap defaults/ directory design           [COMPLETED -- ARCH-001]
    +-- WP-5.5: Observer + AUDITING state implementation       [COMPLETED -- ENG-001, 312 tests, 97% cov]
    +-- WP-5.6: QA verify Phase 5 changes                     [COMPLETED -- QA PASS]
```

100% Rule: All 8 engine modules + templates + tests + reviews + live validation + governance + bootstrap = 100% of project scope.

### Progress Summary (2026-02-17)

| Status | Count | Work Packages |
|--------|-------|---------------|
| COMPLETED | 22 | ALL: WP-1.1--1.7, WP-2.1--2.4, WP-3.1--3.4, WP-4.1, WP-5.1--5.6 |
| **Total** | **22** | **Completion: 22/22 (100%) -- PROJECT COMPLETE** |

**ENG-001 metrics (per-module breakdown from Engineer):**

| WP | Module | LOC | Coverage | Tests | Target Tests | Target Cov |
|----|--------|-----|----------|-------|--------------|------------|
| WP-1.1 | models.py | 292 | 100% | 55 | ~20 | >=95% |
| WP-1.2 | loader.py | 358 | 95% | 23 | ~10 | >=85% |
| WP-1.3 | validator.py | 261 | 100% | 21 | ~15 | >=90% |
| WP-1.4 | state.py | 381 | 94% | 26 | ~12 | >=90% |
| WP-1.5 | slot_registry.py | 279 | 92% | 22 | ~12 | >=90% |
| WP-1.6 | gate_checker.py | 459 | 96% | 60 | ~12 | >=85% |
| WP-2.1 | runner.py | 346 | 99% | 22 | ~12 | >=80% |
| WP-3.1 | nl_matcher.py | 305 | 96% | 31 | ~10 | >=80% |
| WP-3.2 | __init__.py | 94 | 100% | 10 | -- | -- |
| **Total** | **9 modules** | **2,775** | **97%** | **270** | **~113** | **>=85%** |

All targets exceeded. DELIVERY.yaml produced per protocol v1.1.

**Next gate:** QA-001 verdict (REVIEW.yaml in progress -- final step)
**Next milestone:** WP-4.1 live validation (Spring Festival Gala mini-game)

---

## 2. Phase 1: Foundation (P0)

### WP-1.1: Implement `models.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-1.1 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P0 -- CRITICAL PATH (everything depends on this) |
| **Depends On** | None (zero deps) |
| **Blocks** | WP-1.2, WP-1.3, WP-1.4, WP-1.5, WP-1.6 |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 1 spec)
- `specs/integration-contract.md` Section 2 (Module 1 interface)
- `specs/pipelines/slot-types/*.yaml` (SlotType reference for SlotTypeDefinition dataclass)

**Outputs:**
- `engineer/src/pipeline/models.py`
- `engineer/tests/test_pipeline/test_models.py`
- `engineer/tests/test_pipeline/__init__.py`
- `engineer/tests/test_pipeline/conftest.py`
- `engineer/src/pipeline/__init__.py` (empty initially)

**Acceptance Criteria:**
- All enums defined: `SlotStatus`, `PipelineStatus`, `ArtifactType`, `ConditionType`, `PostConditionType`, `ValidationLevel`
- All dataclasses defined per integration contract signatures
- >= 20 tests
- >= 95% coverage on models.py
- `ruff check` passes with 0 errors
- All tests pass: `pytest engineer/tests/test_pipeline/test_models.py`
- DELIVERY.yaml produced with checksums

---

### WP-1.2: Implement `loader.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-1.2 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P0 |
| **Depends On** | WP-1.1 (models.py) |
| **Blocks** | WP-2.1 (runner.py), WP-3.1 (nl_matcher.py) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 2 spec)
- `specs/integration-contract.md` Section 3 (Module 2 interface)
- `engineer/src/pipeline/models.py` (from WP-1.1)
- `specs/pipelines/templates/*.yaml` (sample pipelines for testing)

**Outputs:**
- `engineer/src/pipeline/loader.py`
- `engineer/tests/test_pipeline/test_loader.py`
- Test fixtures: `engineer/tests/test_pipeline/fixtures/valid-pipeline.yaml`

**Acceptance Criteria:**
- `PipelineLoader` class with `load()`, `resolve()`, `load_and_resolve()` methods
- Parameter resolution via regex substitution
- Uses only `yaml.safe_load()` (never `yaml.load()`)
- >= 10 tests
- >= 85% coverage on loader.py
- All tests pass

---

### WP-1.3: Implement `validator.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-1.3 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P0 |
| **Depends On** | WP-1.1 (models.py) |
| **Blocks** | WP-2.1 (runner.py) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 3 spec)
- `specs/integration-contract.md` Section 4 (Module 3 interface)
- `engineer/src/pipeline/models.py` (from WP-1.1)

**Outputs:**
- `engineer/src/pipeline/validator.py`
- `engineer/tests/test_pipeline/test_validator.py`
- Test fixtures: `engineer/tests/test_pipeline/fixtures/invalid-cycle.yaml`, `invalid-io.yaml`

**Acceptance Criteria:**
- `PipelineValidator` class with `validate()`, `check_dag()`, `topological_sort()`, `check_io_compatibility()`, `check_slot_types()` methods
- DAG acyclicity check via Kahn's algorithm
- All 7 validation rules implemented (unique IDs, valid deps, acyclicity, I/O compat, slot type existence, terminal slot, post-condition rules)
- >= 15 tests
- >= 90% coverage on validator.py
- All tests pass

---

### WP-1.4: Implement `state.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-1.4 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P0 |
| **Depends On** | WP-1.1 (models.py) |
| **Blocks** | WP-1.6 (gate_checker.py), WP-2.1 (runner.py) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 5 spec)
- `specs/integration-contract.md` Section 5 (Module 4 interface)
- `engineer/src/pipeline/models.py` (from WP-1.1)

**Outputs:**
- `engineer/src/pipeline/state.py`
- `engineer/tests/test_pipeline/test_state.py`

**Acceptance Criteria:**
- `PipelineStateTracker` class with `init_state()`, `update_slot()`, `get_ready_slots()`, `is_complete()`, `get_status_summary()`, `save()`, `load()`, `archive()` methods
- Atomic file writes (temp + rename)
- Slot readiness logic: all `depends_on` COMPLETED + all data_flow sources COMPLETED
- >= 12 tests
- >= 90% coverage on state.py
- All tests pass

---

### WP-1.5: Implement `slot_registry.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-1.5 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P0 |
| **Depends On** | WP-1.1 (models.py) |
| **Blocks** | WP-2.1 (runner.py) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 6 spec)
- `specs/integration-contract.md` Section 6 (Module 5 interface)
- `specs/pipelines/slot-types/*.yaml` (5 core SlotType definitions)
- `agents/*.md` (agent capability front-matter)
- `engineer/src/pipeline/models.py` (from WP-1.1)

**Outputs:**
- `engineer/src/pipeline/slot_registry.py`
- `engineer/tests/test_pipeline/test_slot_registry.py`
- Test fixtures: `engineer/tests/test_pipeline/fixtures/sample-slot-type.yaml`, `sample-agent.md`

**Acceptance Criteria:**
- `SlotRegistry` class with `load_slot_types()`, `load_agent_capabilities()`, `get_slot_type()`, `find_compatible_agents()`, `validate_assignment()`, `generate_slot_manifest()` methods
- Capability matching: `agent.capabilities SUPERSET_OF slot_type.required_capabilities`
- YAML front-matter parsing from .md files
- >= 12 tests
- >= 90% coverage on slot_registry.py
- All tests pass

---

### WP-1.6: Implement `gate_checker.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-1.6 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P0 |
| **Depends On** | WP-1.1 (models.py), WP-1.4 (state.py) |
| **Blocks** | WP-2.1 (runner.py) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 4 spec)
- `specs/integration-contract.md` Section 7 (Module 6 interface)
- `engineer/src/pipeline/models.py` (from WP-1.1)
- `engineer/src/pipeline/state.py` (from WP-1.4)

**Outputs:**
- `engineer/src/pipeline/gate_checker.py`
- `engineer/tests/test_pipeline/test_gate_checker.py`

**Acceptance Criteria:**
- `GateChecker` class with `check_pre_conditions()`, `check_post_conditions()`, `all_passed()` methods
- Individual checkers: `check_file_exists()`, `check_slot_completed()`, `check_delivery_valid()`, `check_review_valid()`, `evaluate_custom()`
- All checkers return `GateCheckResult` (never raise)
- No `shell=True` in subprocess calls
- >= 12 tests
- >= 85% coverage on gate_checker.py
- All tests pass

---

### WP-1.7: Phase 1 QA Review

| Field | Value |
|-------|-------|
| **ID** | WP-1.7 |
| **Role** | QA-001 (QA Engineer) |
| **Slot Type** | reviewer |
| **Priority** | P0 |
| **Depends On** | WP-1.1 through WP-1.6 (all Phase 1 modules) |
| **Blocks** | WP-2.1 (Phase 2 start) |

**Inputs:**
- ENG-001's DELIVERY.yaml for Phase 1
- All source files in `engineer/src/pipeline/` (models, loader, validator, state, slot_registry, gate_checker)
- All test files in `engineer/tests/test_pipeline/`
- `specs/integration-contract.md` (interface reference)
- `specs/delivery-protocol.md` (review protocol)
- `specs/delivery-schema.py` (validation functions)

**Outputs:**
- `qa/REVIEW.yaml`
- Independent test run results
- Coverage report

**Acceptance Criteria:**
- All 6 modules independently tested by QA
- Cross-validation: QA runs tests independently and compares results against Engineer's DELIVERY.yaml
- Coverage meets targets per architecture.md Section 10.2
- REVIEW.yaml produced with verdict (PASS/CONDITIONAL_PASS/FAIL)
- If suspicious=true on cross-validation, verdict cannot be PASS

---

## 3. Phase 2: Integration (P1)

### WP-2.1: Implement `runner.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-2.1 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P1 -- CRITICAL PATH |
| **Depends On** | WP-1.7 (Phase 1 QA PASS) |
| **Blocks** | WP-3.3 (integration tests) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 8 spec)
- `specs/integration-contract.md` Section 8 (Module 7 interface)
- All Phase 1 modules (models, loader, validator, state, slot_registry, gate_checker)

**Outputs:**
- `engineer/src/pipeline/runner.py`
- `engineer/tests/test_pipeline/test_runner.py`

**Acceptance Criteria:**
- `PipelineRunner` class with `prepare()`, `get_next_slots()`, `begin_slot()`, `complete_slot()`, `fail_slot()`, `skip_slot()`, `get_summary()`, `resume()` methods
- State mutations delegated to `PipelineStateTracker` (runner never mutates PipelineState directly)
- Gate checks via `GateChecker` before/after slot execution
- Definition hash integrity verification on resume
- >= 12 tests
- >= 80% coverage on runner.py
- All tests pass

---

### WP-2.2: Convert pipeline templates to slot-based format

| Field | Value |
|-------|-------|
| **ID** | WP-2.2 |
| **Role** | ARCH-001 (Architect) |
| **Slot Type** | designer |
| **Priority** | P1 |
| **Depends On** | WP-1.7 (Phase 1 QA PASS -- ensures models are stable) |
| **Blocks** | WP-3.3 (integration tests need valid templates) |

**Inputs:**
- `architect/architecture.md` (slot-based pipeline format)
- `specs/pipelines/slot-types/*.yaml` (5 core SlotType definitions)
- `specs/pipelines/templates/*.yaml` (5 existing templates in old format)

**Outputs:**
- Updated `specs/pipelines/templates/standard-feature.yaml` (slot-based)
- Updated `specs/pipelines/templates/research-task.yaml` (slot-based)
- Updated `specs/pipelines/templates/quant-strategy.yaml` (slot-based)
- Updated `specs/pipelines/templates/security-hardening.yaml` (slot-based)
- Updated `specs/pipelines/templates/hotfix.yaml` (slot-based)
- `architect/DELIVERY.yaml`

**Acceptance Criteria:**
- All 5 templates use `slot_type` instead of `role`/`agent_prompt`
- All templates have explicit `data_flow[]` edges
- All `slot_type` references match existing SlotType definitions
- Templates pass `PipelineValidator.validate()` (once runner is available)
- DELIVERY.yaml produced with checksums

---

### WP-2.3: Update implementation-guide.md + schema.yaml

| Field | Value |
|-------|-------|
| **ID** | WP-2.3 |
| **Role** | ARCH-001 (Architect) |
| **Slot Type** | designer |
| **Priority** | P1 |
| **Depends On** | WP-1.7 (Phase 1 complete -- knows actual interfaces) |
| **Blocks** | None (informational update) |

**Inputs:**
- `architect/architecture.md` (current architecture)
- `specs/integration-contract.md` (current contracts)
- Implemented module interfaces from Phase 1

**Outputs:**
- Updated `specs/pipelines/schema.yaml` (aligned with slot-based architecture)
- Updated `specs/pipelines/implementation-guide.md` (reflects slot_registry.py, updated field names)

**Acceptance Criteria:**
- schema.yaml reflects slot-based fields (slot_type, not role)
- implementation-guide.md includes slot_registry.py module spec
- No contradictions with architecture.md or integration-contract.md

---

### WP-2.4: Phase 2 QA Review

| Field | Value |
|-------|-------|
| **ID** | WP-2.4 |
| **Role** | QA-001 (QA Engineer) |
| **Slot Type** | reviewer |
| **Priority** | P1 |
| **Depends On** | WP-2.1, WP-2.2, WP-2.3 |
| **Blocks** | WP-3.1 (Phase 3 start) |

**Inputs:**
- ENG-001's DELIVERY.yaml for Phase 2
- ARCH-001's DELIVERY.yaml for template conversion
- `engineer/src/pipeline/runner.py` + tests
- Updated templates and specs

**Outputs:**
- `qa/REVIEW.yaml` (Phase 2)

**Acceptance Criteria:**
- runner.py independently tested
- Template validation confirmed
- Cross-validation with Engineer's claimed metrics
- REVIEW.yaml with verdict

---

## 4. Phase 3: Polish (P2)

### WP-3.1: Implement `nl_matcher.py` + tests

| Field | Value |
|-------|-------|
| **ID** | WP-3.1 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P2 |
| **Depends On** | WP-2.4 (Phase 2 QA PASS) |
| **Blocks** | WP-3.4 (final QA review) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 7 spec)
- `specs/integration-contract.md` Section 9 (Module 8 interface)
- `engineer/src/pipeline/models.py` (from WP-1.1)
- `engineer/src/pipeline/loader.py` (from WP-1.2)
- `specs/pipelines/templates/*.yaml` (converted templates for keyword extraction)

**Outputs:**
- `engineer/src/pipeline/nl_matcher.py`
- `engineer/tests/test_pipeline/test_nl_matcher.py`

**Acceptance Criteria:**
- `NLMatcher` class with `match()`, `extract_params()`, `generate_summary()` methods
- Supports Chinese and English input
- Hardcoded keyword maps per template
- >= 10 tests
- >= 80% coverage on nl_matcher.py
- All tests pass

---

### WP-3.2: Implement `__init__.py` (public API)

| Field | Value |
|-------|-------|
| **ID** | WP-3.2 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P2 |
| **Depends On** | WP-3.1 (nl_matcher.py) |
| **Blocks** | WP-3.3 (integration tests) |

**Inputs:**
- `architect/architecture.md` Section 3.2 (Module 9 spec)
- `specs/integration-contract.md` Section 10 (Module 9 interface)
- All implemented modules

**Outputs:**
- `engineer/src/pipeline/__init__.py` (with public API exports)

**Acceptance Criteria:**
- Exports: `Pipeline`, `PipelineState`, `PipelineStatus`, `Slot`, `SlotStatus`, `PipelineRunner`, `PipelineValidator`, `ValidationResult`, `PipelineLoader`, `GateChecker`, `PipelineStateTracker`, `SlotRegistry`, `NLMatcher`
- All exports importable without errors

---

### WP-3.3: Integration tests (end-to-end pipeline runs)

| Field | Value |
|-------|-------|
| **ID** | WP-3.3 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P2 |
| **Depends On** | WP-3.2 (__init__.py), WP-2.2 (converted templates) |
| **Blocks** | WP-3.4 (final QA review) |

**Inputs:**
- All engine modules
- `specs/pipelines/templates/*.yaml` (converted, slot-based)
- `specs/pipelines/slot-types/*.yaml` (5 core types)
- `agents/*.md` (for capability matching tests)

**Outputs:**
- `engineer/tests/test_pipeline/test_integration.py`

**Acceptance Criteria:**
- End-to-end test: load template -> resolve params -> validate -> init state -> advance through slots -> complete
- Tests cover at least 2 different pipeline templates (standard-feature + one other)
- Tests verify: DAG ordering, gate checks, state transitions, artifact flow
- All integration tests pass
- Overall coverage >= 85% across all modules

---

### WP-3.4: Phase 3 QA Review + Final Verdict

| Field | Value |
|-------|-------|
| **ID** | WP-3.4 |
| **Role** | QA-001 (QA Engineer) |
| **Slot Type** | reviewer |
| **Priority** | P2 |
| **Depends On** | WP-3.1, WP-3.2, WP-3.3 |
| **Blocks** | None (final deliverable) |

**Inputs:**
- ENG-001's DELIVERY.yaml for Phase 3
- All source files in `engineer/src/pipeline/`
- All test files in `engineer/tests/test_pipeline/`
- Overall coverage report

**Outputs:**
- `qa/REVIEW.yaml` (Final)
- Final verdict on the complete pipeline engine

**Acceptance Criteria:**
- All 8 modules + __init__.py independently verified
- Integration tests pass
- Overall coverage >= 85%
- No import violations (no imports from outside src/pipeline/ except stdlib + PyYAML)
- Cross-validation of all metrics
- Final REVIEW.yaml with verdict

---

## 5. Phase 4: Live Validation (P0 -- Final Acceptance)

### WP-4.1: Pipeline end-to-end live validation

| Field | Value |
|-------|-------|
| **ID** | WP-4.1 |
| **Role** | Team Lead + all agents as needed |
| **Slot Type** | N/A (manual orchestration) |
| **Priority** | P0 -- USER'S FINAL ACCEPTANCE CRITERION |
| **Depends On** | WP-3.4 (Final QA PASS) |
| **Blocks** | None (project completion gate) |

**Objective:**
Run the completed pipeline engine on a real project: **"Design a mini-game suitable for the Spring Festival Gala (Chun Wan)"**. This validates the full pipeline lifecycle end-to-end with real agents, not just unit tests.

**Inputs:**
- Complete pipeline engine (all 8 modules passing QA)
- Slot-based pipeline templates (converted)
- 5 core SlotType YAML definitions
- All agent prompts with capability front-matter

**Execution Steps:**
1. Team Lead issues natural language request: "Design a mini-game suitable for the Spring Festival Gala"
2. NLMatcher selects appropriate pipeline template (likely `research-task` or `standard-feature`)
3. PipelineLoader loads and resolves parameters
4. PipelineValidator validates the pipeline DAG
5. SlotRegistry generates slot manifest; HR fills slots with compatible agents
6. PipelineRunner orchestrates execution through all slots
7. Agents produce real artifacts at each slot (design doc, research report, etc.)
8. GateChecker evaluates pre/post conditions at each gate
9. PipelineStateTracker records all state transitions
10. Pipeline reaches COMPLETED status

**Outputs:**
- Completed pipeline state YAML in `state/archive/`
- Real artifacts produced by each slot (design docs, research reports, etc.)
- Full execution log demonstrating state transitions
- Proof that the pipeline engine orchestrated a multi-step agent workflow end-to-end

**Acceptance Criteria:**
- Pipeline successfully transitions: LOADED -> VALIDATED -> RUNNING -> COMPLETED
- Every slot transitions through the correct state machine: PENDING -> READY -> PRE_CHECK -> IN_PROGRESS -> POST_CHECK -> COMPLETED
- All gate checks (pre and post conditions) execute and pass
- Data flows correctly between slots (upstream artifacts available to downstream)
- SlotRegistry correctly matches agents to slot types
- State persistence works (state YAML written and readable)
- The final output is a coherent mini-game design produced by the pipeline, not just a technical pass

---

## 6. Phase 5: Governance & Bootstrap (P1)

### WP-5.1: Compliance Auditor Architecture Evaluation [COMPLETED]

| Field | Value |
|-------|-------|
| **ID** | WP-5.1 |
| **Role** | ARCH-001 (Architect) |
| **Slot Type** | designer |
| **Priority** | P1 |
| **Depends On** | WP-4.1 (project baseline complete) |
| **Blocks** | WP-5.5 (ENG implementation) |
| **Status** | COMPLETED |

**Inputs:**
- `architect/architecture.md` (current architecture)
- HR-001 compliance auditor research (CMMI PPQA framework)
- Three-party discussion (HR + ARCH + PMO)

**Outputs:**
- `architect/evaluations/compliance-auditor-architecture-eval.md` (architecture evaluation)

**Key Decisions:**
- **Post-pipeline batch model** (NOT real-time hooks): Auditor runs after pipeline COMPLETED as independent step
- **AUDITING state**: New state between COMPLETED and ARCHIVED (~15 LOC in models.py)
- **Read-only access**: Auditor reads REVIEW.yaml + gate reports, produces Process Audit Report
- **No veto power**: Observe and report only, CEO decides action
- **SlotType**: `auditor` (process-focused, distinct from SEC-001's `security_specialist`)
- **Independence**: Audits ALL roles including QA and PMO

---

### WP-5.2: auditor SlotType YAML

| Field | Value |
|-------|-------|
| **ID** | WP-5.2 |
| **Role** | ARCH-001 (Architect) |
| **Slot Type** | designer |
| **Priority** | P1 |
| **Depends On** | WP-5.1 (architecture evaluation) |
| **Blocks** | WP-5.3 (template needs this SlotType) |

**Outputs:**
- `specs/pipelines/slot-types/auditor.yaml` (updated or new, process-focused)

**Acceptance Criteria:**
- category: governance (process-focused, NOT security)
- required_capabilities: process_audit, artifact_validation, noncompliance_tracking, trend_analysis, objective_evaluation
- Follows existing SlotType YAML schema
- Zero conflict with SEC-001's `security_specialist` SlotType

---

### WP-5.3: compliance-audit Pipeline Template

| Field | Value |
|-------|-------|
| **ID** | WP-5.3 |
| **Role** | ARCH-001 (Architect) |
| **Slot Type** | designer |
| **Priority** | P1 |
| **Depends On** | WP-5.2 (compliance-auditor SlotType) |
| **Blocks** | None |

**Outputs:**
- `specs/pipelines/templates/compliance-audit.yaml`

**Acceptance Criteria:**
- Slot-based v2.0 format (consistent with other 5 templates)
- Slots: collect-evidence -> analyze-compliance -> recommend-improvements -> ceo-review
- Uses `compliance-auditor` and `approver` SlotTypes
- Explicit `data_flow[]` edges
- Passes PipelineValidator.validate()

---

### WP-5.4: Bootstrap defaults/ Directory Design

| Field | Value |
|-------|-------|
| **ID** | WP-5.4 |
| **Role** | ARCH-001 (Architect) |
| **Slot Type** | designer |
| **Priority** | P1 |
| **Depends On** | None |
| **Blocks** | None |

**Outputs:**
- `architect/bootstrap-design.md` (design document)
- `defaults/` directory structure specification

**Acceptance Criteria:**
- Defines which files ship as defaults (HR prompt only as built-in role, per HR-001 research)
- HR prompt parameterization mechanism ({{PROJECT_CONTEXT}}, {{MUST_READ_FILES}})
- Defines initialization flow (how defaults/ content gets into project directory)
- File organization: defaults/agents/, defaults/slot-types/, defaults/templates/
- Clear first-use UX: user provides project brief -> system fills HR prompt params -> HR starts
- Bootstrap sequence: HR -> recruit Architect -> Architect designs topology -> HR recruits remaining roles

---

### WP-5.5: Implement AUDITING State + Post-Pipeline Step

| Field | Value |
|-------|-------|
| **ID** | WP-5.5 |
| **Role** | ENG-001 (Engineer) |
| **Slot Type** | implementer |
| **Priority** | P1 |
| **Depends On** | WP-5.1 (ARCH architecture eval) |
| **Blocks** | WP-5.6 (QA verification) |

**Inputs:**
- `architect/evaluations/compliance-auditor-architecture-eval.md` (from WP-5.1)
- Current engine source code

**Outputs:**
- Updated `engineer/src/pipeline/models.py` (+~15 LOC: AUDITING state in PipelineStatus)
- Updated `engineer/src/pipeline/runner.py` (post-pipeline AUDITING step)
- Updated `engineer/src/pipeline/nl_matcher.py` (+~5 LOC: compliance-audit keywords)
- New/updated tests
- DELIVERY.yaml

**Acceptance Criteria:**
- AUDITING state added between COMPLETED and ARCHIVED in PipelineStatus
- Post-pipeline step mechanism in runner.py
- All existing 270 tests still pass (backward compatibility)
- New tests for AUDITING state transitions
- Coverage >= 97% maintained
- DELIVERY.yaml with checksums

---

### WP-5.6: QA Verify AUDITING State Changes

| Field | Value |
|-------|-------|
| **ID** | WP-5.6 |
| **Role** | QA-001 (QA Engineer) |
| **Slot Type** | reviewer |
| **Priority** | P1 |
| **Depends On** | WP-5.5 (ENG implementation) |
| **Blocks** | None |

**Inputs:**
- ENG-001's DELIVERY.yaml for Phase 5
- Updated source files

**Outputs:**
- `qa/REVIEW.yaml` (Phase 5)

**Acceptance Criteria:**
- All tests pass independently
- Backward compatibility verified (existing 270 tests unaffected)
- AUDITING state transitions work correctly
- Post-pipeline step mechanism verified
- Cross-validation with Engineer's metrics
- REVIEW.yaml with verdict

---

## 7. Dependency Matrix

```
WP-1.1 (models)           --> [no deps]
WP-1.2 (loader)           --> WP-1.1
WP-1.3 (validator)        --> WP-1.1
WP-1.4 (state)            --> WP-1.1
WP-1.5 (slot_registry)    --> WP-1.1
WP-1.6 (gate_checker)     --> WP-1.1, WP-1.4
WP-1.7 (Phase 1 QA)       --> WP-1.1, WP-1.2, WP-1.3, WP-1.4, WP-1.5, WP-1.6
WP-2.1 (runner)           --> WP-1.7
WP-2.2 (templates)        --> WP-1.7
WP-2.3 (spec updates)     --> WP-1.7
WP-2.4 (Phase 2 QA)       --> WP-2.1, WP-2.2, WP-2.3
WP-3.1 (nl_matcher)       --> WP-2.4
WP-3.2 (__init__)          --> WP-3.1
WP-3.3 (integration)      --> WP-3.2, WP-2.2
WP-3.4 (Final QA)         --> WP-3.1, WP-3.2, WP-3.3
WP-4.1 (live validation)  --> WP-3.4
WP-5.1 (arch eval)        --> WP-4.1               [COMPLETED]
WP-5.2 (auditor SlotType) --> WP-5.1
WP-5.3 (CA template)      --> WP-5.2
WP-5.4 (bootstrap design) --> [no deps]
WP-5.5 (AUDITING impl)    --> WP-5.1
WP-5.6 (Phase 5 QA)       --> WP-5.5
```

### Critical Path (Phase 5)

```
WP-5.1 (ARCH design) -> WP-5.5 (ENG implement) -> WP-5.6 (QA verify)
```

(3 work packages on Phase 5 critical path)

### Parallelism Opportunities

**Within Phase 5** (all start immediately):
- WP-5.1, WP-5.2, WP-5.4 can run in parallel (all ARCH-001, no dependencies between them)
- WP-5.3 waits for WP-5.2 (needs compliance-auditor SlotType)
- WP-5.5 waits for WP-5.1 (needs design doc)
- WP-5.6 waits for WP-5.5 (needs implementation)

---

## 8. Resource Allocation Summary

| Agent | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Total |
|-------|---------|---------|---------|---------|---------|-------|
| ENG-001 | WP-1.1--1.6 (6) | WP-2.1 (1) | WP-3.1--3.3 (3) | -- | WP-5.5 (1) | 11 |
| QA-001 | WP-1.7 (1) | WP-2.4 (1) | WP-3.4 (1) | -- | WP-5.6 (1) | 4 |
| ARCH-001 | -- | WP-2.2--2.3 (2) | -- | -- | WP-5.1--5.4 (4) | 6 |

---

## 9. Estimated Test Counts

| Work Package | Module | Est. Tests |
|-------------|--------|------------|
| WP-1.1 | models.py | ~20 |
| WP-1.2 | loader.py | ~10 |
| WP-1.3 | validator.py | ~15 |
| WP-1.4 | state.py | ~12 |
| WP-1.5 | slot_registry.py | ~12 |
| WP-1.6 | gate_checker.py | ~12 |
| WP-2.1 | runner.py | ~12 |
| WP-3.1 | nl_matcher.py | ~10 |
| WP-3.3 | integration tests | ~10+ |
| WP-5.5 | observer hooks | ~10 |
| **Total** | | **~123+** |
