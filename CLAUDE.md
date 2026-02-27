# Agent Orchestrator

## 1. Project Identity

Agent Orchestrator is a pluggable, slot-based pipeline engine for multi-agent development workflows.

- **Core insight**: Topology and personnel are orthogonal concerns
- 18 pipeline modules / ~6400 LOC / 610+ tests
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
- Spec Kit config: `.specify/`
- OV bootstrap: `scripts/ov-bootstrap.sh`

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
    +--- nl_matcher.py (depends on models, loader; optional OV via subprocess)
    |
    +--- slot_contract.py (slot I/O contracts)
    |
    +--- enforcer.py (slot enforcement rules)
    |
    +--- observer.py (compliance observation)
    |
    +--- ov_context_router.py (depends on models; calls ov CLI via subprocess)
    |
    +--- context_router.py (L0/L1/L2 context routing; delegates to ov_context_router)
    |
    +--- project_planner.py (depends on models; blueprint data model + validation)
    |
    +--- pipeline_generator.py (depends on models, project_planner; generates pipelines from blueprints)
    |
    +--- runner.py (depends on ALL above)
    |
    +--- auto_executor.py (depends on models, runner, slot_contract, slot_registry; automated execution)
    |
    +--- bootstrap.py (depends on auto_executor, nl_matcher, runner, slot_contract, slot_registry; one-call init)
    |
    +--- cli.py (depends on runner, nl_matcher, slot_registry; CLI interface for Claude Code)
```

### Pipeline Modules (18)

| Module | Responsibility |
|--------|---------------|
| `models.py` | Data models (dataclasses + enums) |
| `loader.py` | YAML loading + parameter resolution |
| `validator.py` | DAG validation + I/O compatibility |
| `gate_checker.py` | Pre/post condition evaluation |
| `state.py` | State tracking + persistence |
| `slot_registry.py` | SlotType loading + agent matching |
| `nl_matcher.py` | Natural language -> template matching (+ OV semantic boost) |
| `runner.py` | Pipeline orchestration |
| `auto_executor.py` | Automated execution loop (agent resolution + parallel execution + retry) |
| `bootstrap.py` | One-call engine init (`boot()` + `BootstrappedExecutor`) |
| `cli.py` | CLI interface — `python -m pipeline.cli` for Claude Code |
| `slot_contract.py` | Slot I/O contract management |
| `enforcer.py` | Slot enforcement rules |
| `observer.py` | Compliance observation |
| `context_router.py` | L0/L1/L2 context routing (delegates to OV when available) |
| `ov_context_router.py` | OpenViking-backed context retrieval via `ov` CLI |
| `project_planner.py` | Blueprint data model + validation (meta-orchestration) |
| `pipeline_generator.py` | Pipeline/slot-type/agent generation from blueprints |

## 6. Pipeline CLI — 使用方法

本项目的核心产出是 pipeline 引擎。所有多步任务必须通过 pipeline CLI 执行。

### 设置别名

```bash
alias pipeline="PYTHONPATH=/home/coder/project/agent-orchestrator/engineer/src \
  /home/coder/project/agent-orchestrator/engineer/.venv/bin/python -m pipeline.cli"
```

### 工作流程

```bash
# 1. 查看可用模板
pipeline -P /path/to/target/project templates

# 2. 选择模板，创建流水线实例
pipeline -P /path/to/target/project prepare standard-feature.yaml -p feature_name=login

# 3. 查看下一步该做什么（哪些槽位已就绪）
pipeline next

# 4. 开始执行一个槽位（引擎会告诉你目标和交付物）
pipeline begin slot-design

# 5. 你执行实际工作（写代码、审查、测试等）

# 6. 完成后标记槽位
pipeline complete slot-design

# 7. 重复 3-6 直到所有槽位完成
pipeline next
pipeline begin slot-implement
# ... 做工作 ...
pipeline complete slot-implement

# 8. 查看最终状态
pipeline summary
```

### 其他命令

| 命令 | 说明 |
|------|------|
| `pipeline match <text>` | 自然语言匹配模板（预览，不执行） |
| `pipeline status` | 显示流水线当前状态 |
| `pipeline fail <slot_id> <error>` | 标记槽位失败 |
| `pipeline skip <slot_id>` | 跳过槽位 |

### 关键规则

- `prepare` 后状态存磁盘，后续命令自动恢复，无需重复指定
- 每个槽位必须先 `begin` 再 `complete`，不能跳过
- 被依赖的槽位完成后，下游槽位才会出现在 `next` 中
- 失败的槽位会阻塞下游，用 `skip` 可以绕过

## 7. Quality Gates

- Test coverage >= 85%
- Zero import violations (only stdlib + yaml)
- DELIVERY.yaml required for implementer slots
- REVIEW.yaml required for reviewer slots
- suspicious=true blocks deployment (Constitution SS4.6)
- Checksum integrity on all deliverables (Constitution SS4.3)
- Cross-validation mandatory: QA independently reproduces metrics (Constitution SS4.9)

## 8. External Tool Integration

### Spec Kit (`specify` CLI)

[Spec Kit](https://github.com/nicholasgriffintn/specify) provides spec-driven development tooling.

- **Config**: `.specify/` directory (templates, memory, scripts)
- **Slash commands**: 9 `speckit.*` commands in `.claude/commands/`
- **Constitution sync**: `.specify/memory/constitution.md` mirrors project constitution
- **Usage**: `specify init`, `specify plan`, `specify implement`

### OpenViking (`ov` CLI)

[OpenViking](https://github.com/nicholasgriffintn/openviking) provides agent-native context management with `viking://` URIs.

- **Namespace**: `viking://agent-orchestrator`
- **Bootstrap**: `bash scripts/ov-bootstrap.sh` (registers resources + relations)
- **Server**: `bash scripts/ov-serve.sh start`
- **Integration points**:
  - `ov_context_router.py` — L0/L1/L2 context via `ov abstract`/`ov overview`/`ov read`
  - `context_router.py` — delegates to OV when `use_openviking=True`, falls back to file scan
  - `nl_matcher.py` — boosts keyword matches with `ov find` semantic search
  - `/context` command — uses OV when available for richer context
- **Graceful degradation**: All OV features are opt-in (`use_openviking=False` default). OV unavailable = file-scan fallback, zero impact on existing behavior.
- **Constitution compliance**: Integrated via `subprocess.run()` only (no Python imports per Art.2).
