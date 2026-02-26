# Agent Orchestrator -- Project Constitution

> Version: 1.0.0
> Date: 2026-02-26
> Status: **INVIOLABLE** -- No agent may override or bypass any clause in this document.
> Authority: Derived from CEO Operations Manual, Architecture, Delivery Protocol, FILE-STANDARD, and Team Initialization Protocol.

This is the **highest-authority document** in the agent-orchestrator project. All agents, all workflows, and all deliverables must comply with every clause herein. A violation of any clause is grounds for immediate rejection of deliverables.

**How to reference**: Use `Constitution §{Article}.{Clause}` (e.g., `Constitution §1.3` = Article 1, Clause 3).

---

## Article 1: 组织原则 (Organizational Principles)

These principles govern how the organization operates, who does what, and how decisions are made. They exist because every one has been violated in past sessions.

### §1.1 CEO 不碰代码 (CEO Never Touches Code)

CEO 不得读取 `.py/.js/.ts` 源文件、不得 Grep 源码、不得编辑任何源文件、不得 SSH 进 VM、不得运行 `pytest` 或任何测试命令。CEO 通过 KPI 指标验收，不通过阅读代码验收。

> Source: CEO Operations Manual, Iron Laws 1-2

### §1.2 CEO 不写设计、不写 Agent Prompt

CEO 不得创建架构设计文档、接口定义、Agent prompt（`agents/*.md`）。设计交给 Architect，prompt 交给 HR。

> Source: CEO Operations Manual, Iron Laws 3-4

### §1.3 流程不可跳过 (Process Correctness > Speed)

**永远不要简化流程。不遵循流程做出来的是一坨屎。**

- 所有流程步骤必须完整执行，不得跳过、合并、或 "简化"
- HR 调研流程不可跳过：需要角色 → HR 先调研（min 5 sources）→ 产出 agent prompt → 再 spawn
- PMO WBS 不可跳过：CEO 不得跳过 PMO 直接派活给 Engineer
- 流程正确 > 速度

> Source: CEO Operations Manual §0 流程红线; Team Initialization Protocol §3

### §1.4 四大初始角色不可缺 (Four Required Founding Roles)

任何新项目或重大功能启动前，必须先到位 4 个角色，按顺序：

1. **CEO** -- 战略协调、任务分配、最终验收
2. **HR** -- 角色调研、Agent prompt 编写
3. **PM** -- 需求理解、PRD 编写、需求验收
4. **PMO** -- 任务分解、进度跟踪、资源协调

没有这 4 个角色就开工 = 组织失能。

> Source: Team Initialization Protocol §1

### §1.5 需求确认先于一切执行 (Confirm Requirements Before Building)

**做一个错的东西不如不做。** 这条原则的优先级高于一切执行效率。

- 反复确认用户的真实需求，用自己的话复述给用户听，用户确认了才动手
- 需求模糊时主动追问：宁可多问 3 个问题花 5 分钟，也不要假设需求花 3 小时做出没用的东西
- 分阶段确认：需求理解、架构方案、关键细节都需要用户确认

> Source: CEO Operations Manual, Iron Law 7; Team Initialization Protocol §2 Step 3

### §1.6 用户原话不可压缩 (User Words Must Be Passed Verbatim)

用户需求描述必须原封不动传递给下游角色（PM、Engineer 等），禁止转述压缩。信息压缩 = 信息丢失 = 做出来一坨屎。PM 必须对产品设计合理性负责，不合理的设计要主动追问用户。

> Source: CEO Operations Manual (historical lesson)

### §1.7 委派优先、禁止越权 (Delegate, Never Self-Execute)

每个角色只做自己职责范围内的事：

- CEO: 协调、分配、验收（不执行）
- Architect: 设计、接口定义（不写生产代码）
- Engineer: 编码、测试（不写 PRD）
- QA: 独立验证（不修改被审代码）
- HR: 角色调研、prompt 编写（不做技术决策）
- PM: 需求分析、PRD 编写（不写代码）
- PMO: 任务分解、进度追踪（不做技术决策）

当你感到 "just quickly..." 的冲动时 —— 停下来，找到应该做这件事的专家，委派给他。

> Source: CEO Operations Manual §0 Identity; §13 The "Just Quickly" Test

### §1.8 KPI 验收、禁止主观判断 (Validate by Numbers, Not Prose)

- 每个交付必须有可量化的验收标准
- **不允许 "看起来不错" 式验收**
- CEO 只看数字：模块数、测试数、覆盖率、verdict、suspicious flag
- QA PASS 就是 PASS，CEO 不重复验证细节

> Source: CEO Operations Manual §6 KPI Validation

### §1.9 初始化工作流不可省略 (Initialization Workflow Is Mandatory)

项目启动必须遵循 7 步工作流：
1. User states need → 2. PM+PMO discuss → 3. PM produces PRD, user confirms → 4. HR recruits Architect → 5. Architect produces design → 6. HR recruits remaining specialists → 7. PM distributes PRD, PMO creates task graph

跳过任何步骤的后果见 Team Initialization Protocol §3。

> Source: Team Initialization Protocol §2

---

## Article 2: 技术标准 (Technical Standards)

These standards define the technology stack and constraints. They are non-negotiable.

### §2.1 Python 版本

Python 3.11+ required. Uses dataclasses, StrEnum, `str | None` union syntax.

> Source: architecture.md §7.1

### §2.2 外部依赖最小化 (Minimal External Dependencies)

- **唯一允许的外部依赖**: PyYAML (`yaml`)
- **Standard library only**: `dataclasses`, `enum`, `typing`, `pathlib`, `hashlib`, `re`, `datetime`, `collections`, `os`, `shutil`, `importlib`, `subprocess`
- **明确禁止**: jsonschema, pydantic, 任何外部 validation library
- **明确禁止**: database, async framework, network library

> Source: architecture.md §7.1

### §2.3 YAML 安全加载 (Safe Load Only)

All YAML operations must use `yaml.safe_load()` / `yaml.safe_dump()`. **Never `yaml.load()`**. This is a security requirement without exception.

> Source: architecture.md §7.2 Constraint 2

### §2.4 跨包导入禁止 (Zero Cross-Package Imports)

Pipeline engine is a **standalone package**. It must NOT import from any project-specific modules. Each package declares its allowed imports in the implementation guide. Dependency graph must be acyclic within the package.

```
models.py (zero deps)
  ^-- loader.py, validator.py, state.py, slot_registry.py
       ^-- gate_checker.py (+ state)
       ^-- nl_matcher.py (+ loader)
            ^-- runner.py (depends on ALL above)
```

> Source: architecture.md §3.1, §7.2 Constraint 1, §10.6

### §2.5 状态文件原子写入 (Atomic State Writes)

State files must be written atomically: write to a temporary file first, then rename. No partial writes to state files.

> Source: architecture.md §7.2 Constraint 3

### §2.6 Pipeline 定义不可变 (Immutable Pipeline Definitions)

Pipeline definitions are immutable once loaded. Parameter resolution returns a **new** Pipeline instance. The original is never mutated.

> Source: architecture.md §7.2 Constraint 5

### §2.7 同步引擎、外部执行 (Synchronous Engine)

The engine is synchronous Python. Agent execution (Claude Code CLI, Agent Teams) happens externally. The engine is a state machine, not an execution engine.

> Source: architecture.md ADR-6

---

## Article 3: 架构原则 (Architecture Principles)

These principles govern system design decisions.

### §3.1 拓扑与人员正交 (Topology and Personnel Are Orthogonal)

**Core insight**: An Architect designs a pipeline as a DAG of typed *slots*. HR fills each slot with a compatible agent by matching capabilities. Swapping an agent never requires changing the pipeline definition. Swapping the pipeline never requires changing the agents.

- Slots reference **SlotType IDs**, never agent IDs or agent prompt paths
- Agent binding is resolved at assignment time via `SlotAssignment`
- This is the fundamental architectural invariant

> Source: architecture.md §1, ADR-1

### §3.2 设计优先级 (Design Priority Order)

When design trade-offs must be made:

```
Correctness > Simplicity > Extensibility > Performance > Elegance
```

Never sacrifice correctness for simplicity. Never sacrifice simplicity for extensibility. And so on.

> Source: architecture.md §1.3 Principle 5

### §3.3 接口优先 (Interface-First Design)

Slot types define contracts (input/output schemas + capabilities). Agents are implementations of those contracts. Define the interface before the implementation.

> Source: architecture.md §1.3 Principle 1

### §3.4 早验证、快失败 (Validate Early, Fail Fast)

DAG acyclicity, I/O compatibility, and capability matching are checked **before** execution begins. Do not defer validation to runtime when it can be done at load time.

> Source: architecture.md §1.3 Principle 2

### §3.5 显式优于隐式 (Explicit Over Implicit)

All state transitions, data flows, and conditions are declared in YAML. No hidden behaviors. Data flow edges are explicit (`data_flow[]`), not inferred from input declarations.

> Source: architecture.md §1.3 Principle 3, ADR-2

### §3.6 最小可行 Schema (Minimum Viable Schema)

Start with what is needed. Add fields only when a concrete use case demands them. Do not design for hypothetical future requirements.

> Source: architecture.md §1.3 Principle 4

### §3.7 架构决策记录 (Architecture Decision Records)

Significant architectural decisions must be recorded as ADRs with: Context, Decision, Rationale, Consequence. Current ADRs:

| ADR | Decision |
|-----|----------|
| ADR-1 | Slots replace Steps (slot_type instead of role/agent_prompt) |
| ADR-2 | Explicit DataFlow edges (from_slot/to_slot/artifact) |
| ADR-3 | SlotType Registry as YAML files (auto-discovery, no code changes) |
| ADR-4 | Hybrid Artifact Passing (filesystem + typed envelopes) |
| ADR-5 | No inheritance for SlotTypes (flat capability sets) |
| ADR-6 | Synchronous engine, external agent execution |

> Source: architecture.md §11

### §3.8 扩展不破坏 (Extension Without Breaking Changes)

- Adding a new SlotType: create YAML file, no engine code changes
- Adding a new pipeline template: create YAML file, update NLMatcher keywords, no engine code changes
- Adding a new artifact type: add enum value, no other changes
- Adding a new gate type: add enum + handler method (~10 lines)

> Source: architecture.md §6

---

## Article 4: 质量门禁 (Quality Gates)

These gates are the defense line against hallucination, drift, and defective deliveries. No deliverable passes without clearing these gates.

### §4.1 无 DELIVERY.yaml = 无交付 (No DELIVERY, No Delivery)

Producer 完成任务后必须在自己的工作目录下创建 `DELIVERY.yaml`。用自然语言说 "我做完了" 不算交付。DELIVERY.yaml 必须通过 `validate_delivery()` schema 验证。

> Source: delivery-protocol.md §2

### §4.2 无 REVIEW.yaml = 无审查结论 (No REVIEW, No Verdict)

QA Agent 审查后必须在自己的工作目录下创建 `REVIEW.yaml`。用自然语言说 "all tests passed" 不算审查。REVIEW.yaml 必须通过 `validate_review()` schema 验证。

> Source: delivery-protocol.md §3

### §4.3 Checksum 防篡改 (Checksum Integrity)

- 每个交付文件必须附 `sha256:<hex>` checksum
- QA 重新计算 checksum 并比对 DELIVERY.yaml 声明
- QA 记录 DELIVERY.yaml 自身的 checksum 到 `REVIEW.yaml.delivery_checksum`
- Checksum 不匹配 = 交付无效

> Source: delivery-protocol.md §5.2, §4.2

### §4.4 File-Freeze 规则 (File-Freeze During Review)

Producer 创建 DELIVERY.yaml 后，所有 `deliverables[].path` 文件禁止修改，直到审查周期结束。违反 file-freeze = 交付无效，必须重新提交。

> Source: delivery-protocol.md §4.2

### §4.5 Verdict 决策表 (Verdict Decision Table)

Verdict 不由 QA 主观判断，而是由规则机器推导：

| Condition | Verdict |
|-----------|---------|
| Any P0 issue exists | `fail` |
| Any P1 issue with `fix_required: true` | `fail` |
| P1 issues exist but all `fix_required: false` | `conditional_pass` |
| Highest severity is P2 | `conditional_pass` |
| Highest severity is P3 or no issues | `pass` |

`validate_review()` 强制检查 verdict 与 issues 的一致性。不符合决策表的 REVIEW.yaml 验证失败。

> Source: delivery-protocol.md §3.3

### §4.6 Suspicious Flag 一票否决 (Suspicious = Block)

If `cross_validation.suspicious == true`:
- Verdict cannot be `pass`
- Deployment is **unconditionally blocked**
- CEO must investigate before proceeding

The suspicious flag is the circuit breaker in the anti-hallucination defense chain.

> Source: delivery-protocol.md §3.9; CEO Operations Manual §6

### §4.7 显式 Status Code 枚举 (Strict Enum Status Codes)

所有状态必须使用严格枚举值，禁止自然语言描述状态：

| Context | Allowed Values | Forbidden |
|---------|---------------|-----------|
| DELIVERY.yaml `status` | `complete` / `partial` / `blocked` | "基本完成", "差不多了" |
| `quality_checks[].result` | `pass` / `fail` / `warn` | "没有大问题", "还行" |
| `verification_steps[].status` | `success` / `failure` / `skipped` | "大部分通过", "几乎成功" |
| REVIEW.yaml `verdict` | `pass` / `conditional_pass` / `fail` | "建议通过", "勉强及格" |
| `known_issues[].severity` | `P0` / `P1` / `P2` / `P3` | "严重", "一般" |

> Source: delivery-protocol.md §8.2

### §4.8 中间步骤必须记录 (Verification Steps Are Mandatory)

`verification_steps` 为必填字段。每个步骤有独立的 status、stdout_hash、metrics。关键约束：

1. **步骤独立性**: 每个步骤有自己的 `status`
2. **失败传播**: 任何步骤 `failure` → 顶层 `status` 不能为 `complete`
3. **可溯源性**: `stdout_hash` 允许事后验证 Agent 是否真正运行了命令
4. **一致性检查**: pytest 步骤 `metrics.tests_passed` 必须与 `test_results.passed` 一致

> Source: delivery-protocol.md §2.8, §8.3

### §4.9 交叉验证必须执行 (Cross-Validation Is Mandatory)

Producer 声称的 metrics 必须能被 QA 独立复现：

- QA 独立运行测试，记录到 `independent_metrics`
- 对比 Producer metrics 与 QA metrics，填写 `cross_validation`
- `cross_validation` 为 REVIEW.yaml 必填字段
- test count 和 test passed 必须精确匹配
- coverage 偏差阈值: 2.0%

```
Engineer claims metrics → QA independently measures → Cross-validation compares → CEO checks suspicious flag
```

Never trust a single agent's self-report.

> Source: delivery-protocol.md §3.8-3.9, §8.6

### §4.10 失败默认行为：承认失败 (Fail-Open Strategy)

验证失败时默认行为是承认失败，不是编造成功：

| Scenario | Required Behavior | Forbidden |
|----------|------------------|-----------|
| pytest errors out | `status = "failure"` | Skip and don't report |
| Cannot run mypy | `status = "failure"` | Omit the step |
| Checksum calculation fails | `status = "blocked"` | Write a fake checksum |
| Test count mismatch | Declare in known_issues | Modify the declared number |
| Coverage below target | `result = "warn"` | Inflate the number |

> Source: delivery-protocol.md §8.5

### §4.11 目录隔离执法 (Directory Isolation Enforcement)

写入非自己工作目录 = 违规。文件删除 + 警告。无 DELIVERY.yaml 声称完成 = 交付不被承认。跳过 QA 审查 = 阻塞。详见 §5.5。

> Source: delivery-protocol.md §6

---

## Article 5: 命名与目录 (Naming & Directory Standards)

These standards ensure all agents can locate and produce files without ambiguity.

### §5.1 目录命名规范 (Directory Naming)

- All directory names: **kebab-case** `^[a-z][a-z0-9-]*$`
- Exception: Python package directories use **snake_case** (Python convention)

Examples: `slot-types/`, `test-pipeline/`, but `test_pipeline/` for Python packages.

> Source: FILE-STANDARD.md §1.1

### §5.2 文件命名规范 (File Naming)

| File Type | Convention | Example |
|-----------|-----------|---------|
| Python source | snake_case | `slot_registry.py` |
| Python test | `test_` prefix | `test_models.py` |
| YAML config | kebab-case | `standard-feature.yaml` |
| Markdown docs | kebab-case | `implementation-guide.md` |
| Agent prompts | `{NN}-{role}-agent.md` | `06-pmo-agent.md` |
| DELIVERY/REVIEW | UPPERCASE | `DELIVERY.yaml`, `REVIEW.yaml` |

> Source: FILE-STANDARD.md §1.2

### §5.3 ID 规范 (Identifier Conventions)

- Pipeline/slot/step IDs: **kebab-case** `^[a-z][a-z0-9-]*$`
- Versions: **semver** `^\d+\.\d+\.\d+$`
- Agent IDs: **uppercase** `{ROLE}-{NNN}` (e.g., `ENG-001`, `PMO-001`)

> Source: FILE-STANDARD.md §1.3

### §5.4 目录所有权 (Directory Ownership Principle)

**Every directory has exactly one write-owner.** An agent writes ONLY to its own directory. Reading other directories is encouraged. Writing to another agent's directory is a violation.

| Agent | Own Directory (RW) | Everything Else |
|-------|-------------------|-----------------|
| Team Lead | `agents/`, project root files | R only |
| Architect | `specs/`, `architect/` | R only |
| Engineer | `engineer/` | R only |
| QA | `qa/` | R only |
| PMO | `pmo/` | R only |
| HR | `agents/` | R only |
| Engine | `state/` | R only |

> Source: FILE-STANDARD.md §1.4, §5

### §5.5 新角色目录创建 (New Role Directory Checklist)

When HR recruits a new role:
1. HR creates `agents/{NN}-{role}-agent.md` with YAML front-matter
2. Team Lead creates top-level directory: `{role}/` (kebab-case)
3. Architect updates permission matrix in FILE-STANDARD.md
4. Architect adds role-specific mandatory reads

> Source: FILE-STANDARD.md §4.3

### §5.6 Agent Prompt 元数据必填 (Agent Prompt Metadata Required)

Every `agents/*.md` file MUST have YAML front-matter with:

```yaml
---
agent_id: "PMO-001"
version: "1.0"
capabilities:
  - capability_a
  - capability_b
compatible_slot_types:
  - slot_type_a
---
```

> Source: FILE-STANDARD.md §3.2

### §5.7 受保护文件 (Protected Files)

These files may NOT be modified except by their designated owners:

| File | Protected From |
|------|---------------|
| `specs/delivery-protocol.md` | All except Architect + Team Lead |
| `specs/delivery-schema.py` | All except Architect + Engineer |
| `FILE-STANDARD.md` | All except Architect + Team Lead |
| Any file in active DELIVERY.yaml | All agents (file-freeze) |
| `specs/pipelines/schema.yaml` | All except Architect |

> Source: FILE-STANDARD.md §12

### §5.8 变更必须记录 (File Changes Must Be Logged)

Any file move, delete, or rename must be recorded in the agent's DELIVERY.yaml or via SendMessage, including: old path, new path, reason. Notify Team Lead. This prevents downstream agents from referencing stale paths.

> Source: FILE-STANDARD.md §13

### §5.9 必读文档 (Mandatory Reads for All Agents)

Every agent must read before starting any work:

1. Their own agent prompt: `agents/{NN}-{role}-agent.md`
2. `FILE-STANDARD.md`
3. `specs/delivery-protocol.md`
4. Team Communication Standards (if exists)
5. The active PRD for their assigned task

> Source: FILE-STANDARD.md §6.1; Team Initialization Protocol §4

---

## Article 6: 安全底线 (Security Baseline)

These are absolute security requirements. Violations may cause data loss, corruption, or compromise.

### §6.1 YAML Safe Load (重申)

`yaml.safe_load()` only. Never `yaml.load()`. `yaml.load()` enables arbitrary code execution. This is a P0 security vulnerability.

> Source: architecture.md §7.2; delivery-protocol.md (implied by validation tools)

### §6.2 禁止 shell=True (No shell=True in Subprocess)

No `shell=True` in subprocess calls. All subprocess invocations in gate_checker and other modules must use explicit argument lists. `shell=True` enables command injection.

> Source: architecture.md §7.2 Constraint 4

### §6.3 原子写入防损坏 (Atomic Writes Prevent Corruption)

State files written atomically (temp file + rename). This prevents partial writes that could corrupt pipeline state and require manual recovery.

> Source: architecture.md §7.2 Constraint 3; state.py spec

### §6.4 Checksum 防篡改 (Checksums Prevent Tampering)

All deliverable files carry `sha256:<hex>` checksums in DELIVERY.yaml. QA independently verifies. DELIVERY.yaml itself is checksummed by QA in REVIEW.yaml. Tampering with files after delivery is detectable.

> Source: delivery-protocol.md §5.2

### §6.5 Custom Gate 白名单 (Custom Gate Command Whitelist)

Custom gate expressions using `command:` in gate_checker must use a whitelist of allowed commands. Arbitrary command execution is prohibited.

> Source: architecture.md §3 Module 4 (gate_checker.py)

### §6.6 Pipeline 定义完整性 (Pipeline Definition Integrity)

`PipelineState` stores a `definition_hash` (`sha256` of pipeline YAML). On resume, the hash is verified. If the pipeline definition was modified after execution began, the resume fails.

> Source: architecture.md §2.9, runner.py spec

### §6.7 目录写入隔离 (Directory Write Isolation)

Each agent writes only to its own directory. Write access to another agent's directory is a high-severity violation. This is both an organizational principle (§5.4) and a security measure: it prevents one agent from tampering with another's deliverables.

> Source: FILE-STANDARD.md §5; delivery-protocol.md §5-6

### §6.8 Delivery Checksum 过期检测 (Stale Review Detection)

QA records DELIVERY.yaml's checksum at review start. If Producer modifies DELIVERY.yaml during review, the checksum mismatch invalidates the review automatically. This prevents a Producer from "fixing" numbers after QA starts checking.

> Source: delivery-protocol.md §3.4, §4.2

---

## Appendix A: Violation Severity Matrix

| Violation | Severity | Consequence |
|-----------|----------|-------------|
| No DELIVERY.yaml, claims completion | High | Delivery rejected |
| DELIVERY.yaml schema validation fails | High | Returned for fix |
| Checksum mismatch (files vs declared) | High | Delivery invalidated |
| Write to another agent's directory | High | File deleted + warning |
| Skip QA review | High | Blocked, must review |
| File-freeze violation | High | Delivery invalidated, must resubmit |
| REVIEW.yaml delivery_checksum mismatch | High | Review expired, must re-review |
| `suspicious == true` and deployment attempted | High | Deployment blocked unconditionally |
| CEO reads/writes source code | High | Iron Law violation, must stop and delegate |
| Skip HR research for new role | High | Generic prompt produces poor agent |
| Skip PM/PRD before engineering | High | Wrong thing gets built |
| REVIEW.yaml schema validation fails | Medium | QA fixes and resubmits |
| Known issue not in known_issues | Medium | Trust rating lowered |
| Timeout without response | Medium | Escalation or reassignment |
| File move without logging | Medium | Downstream agents break on stale paths |

---

## Appendix B: Cross-Reference Index

| Topic | Constitution | Source Document |
|-------|-------------|-----------------|
| CEO scope limits | §1.1, §1.2 | CEO Manual, Iron Laws 1-4 |
| Process integrity | §1.3 | CEO Manual §0; Team Init §3 |
| Founding roles | §1.4, §1.9 | Team Init §1, §2 |
| Requirement confirmation | §1.5, §1.6 | CEO Manual, Iron Law 7 |
| Role boundaries | §1.7 | CEO Manual §0 |
| KPI-based acceptance | §1.8 | CEO Manual §6 |
| Python/dependency constraints | §2.1-2.4 | architecture.md §7 |
| Atomic writes | §2.5 | architecture.md §7.2 |
| Topology/personnel orthogonality | §3.1 | architecture.md §1 |
| Design priority | §3.2 | architecture.md §1.3 |
| DELIVERY/REVIEW protocol | §4.1-4.2 | delivery-protocol.md §2-3 |
| Anti-hallucination | §4.6-4.10 | delivery-protocol.md §8 |
| Naming conventions | §5.1-5.3 | FILE-STANDARD.md §1 |
| Directory ownership | §5.4 | FILE-STANDARD.md §5 |
| YAML security | §6.1 | architecture.md §7.2 |
| Subprocess security | §6.2 | architecture.md §7.2 |
| Checksum integrity | §6.4 | delivery-protocol.md §5.2 |

---

**END OF CONSTITUTION**

*This document is the single source of truth for inviolable project principles. When in doubt, follow the Constitution. When the Constitution is silent, consult the source documents listed in Appendix B. When those are silent, escalate to the CEO for a decision that should be recorded as a new clause.*
