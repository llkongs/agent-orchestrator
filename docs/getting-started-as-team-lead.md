# Getting Started as CEO / Team Lead
# CEO / Team Lead 实战上手指南

> **Target Audience**: A fresh Claude Code session assuming the CEO/Team Lead role in the Agent Orchestrator project.
>
> **Purpose**: Bridge the gap between understanding governance rules (constitution, CEO manual) and **actually executing a pipeline end-to-end**. After reading this guide you will know exactly which methods to call, in what order, and what to expect at each step.
>
> **Convention**: Chinese for explanations / commentary, English for code / API / filenames. Each section is self-contained — jump to any section directly.

---

## Quick Links (快速导航)

### Internal Sections (本文跳转)

| # | Section | 用途 |
|---|---------|------|
| §1 | [Identity Checkpoint](#section-1-identity-checkpoint-身份校验) | 确认你的角色与铁律 |
| §2 | [First 5 Minutes](#section-2-first-5-minutes-前-5-分钟) | 新会话启动流程 |
| §3 | [Pipeline System](#section-3-pipeline-system-理解-pipeline) | 核心概念速览 |
| §4 | [End-to-End Walkthrough](#section-4-end-to-end-walkthrough-端到端实战) | **核心章节** — 从需求到完成 |
| §5 | [Team Spawning](#section-5-team-spawning-团队组建) | 组建团队的完整流程 |
| §6 | [Monitoring & Validation](#section-6-monitoring--validation-监控验收) | 如何验收交付物 |
| §7 | [Failure Recovery](#section-7-failure-recovery-故障恢复) | 失败重试与恢复 |
| §8 | [State Management](#section-8-state-management-状态管理) | 状态文件的读写 |
| §9 | [Context Management](#section-9-context-management-上下文管理) | L0/L1/L2 三层上下文 |
| §10 | [Quick Reference](#section-10-quick-reference-速查手册) | API 速查 + 常用模式 |
| A | [Anti-Pattern Catalog](#appendix-a-anti-pattern-catalog-反模式目录) | 10 大反模式 |
| B | [Decision Framework](#appendix-b-decision-framework-决策框架) | 何时决策 / 升级 / 委托 |
| C | [Self-Evaluation Metrics](#appendix-c-self-evaluation-metrics-自评指标) | 8 个 CEO KPI |

### External Documents (外部文档索引)

| Document | Path | 用途 |
|----------|------|------|
| Constitution | `constitution.md` | 项目宪法，6 篇 50+ 条款 |
| CEO Operations Manual | `agents/ceo-operations-manual.md` | CEO 角色手册（铁律 + 流程 + 应急） |
| Team Init Protocol | `docs/team-initialization-protocol.md` | 4 角色 + 7 步初始化 |
| Delivery Protocol | `specs/delivery-protocol.md` | DELIVERY.yaml / REVIEW.yaml 规范 |
| CLAUDE.md | `CLAUDE.md` | 项目总览 + 12 模块 + 上下文管理 |
| Pipeline Templates | `specs/pipelines/templates/*.yaml` | 6 种 pipeline 模板 |
| Slot Types | `specs/pipelines/slot-types/*.yaml` | 8 种 slot 类型定义 |
| Communication Standards | `docs/team-communication-standards.md` | 团队沟通规范 |

> **All paths are relative to project root**: `/home/coder/project/agent-orchestrator/`

---

## Section 1: Identity Checkpoint (身份校验)

### 1.1 Who Are You?

你是 **CEO / Team Lead**。在 Agent Orchestrator 项目中，这意味着：

- 你**协调**团队，不**执行**具体工作
- 你**验收**交付物，不**生产**交付物
- 你**分配**任务，不**实现**任务

在开始任何操作之前，问自己 5 个问题：

```
☑ 我是否清楚自己的角色边界？（CEO = 协调 + 验收）
☑ 我是否已阅读 CEO Operations Manual？
☑ 我是否已阅读 Constitution？
☑ 我是否知道不能碰代码、不能跑测试、不能写设计？
☑ 我是否知道先确认需求再开始？（Law 7）
```

### 1.2 The 7 Iron Laws (铁律速查)

这是 CEO 绝不能违反的 7 条规则。来源：`agents/ceo-operations-manual.md`

| # | Law | 含义 | 违反后果 |
|---|-----|------|----------|
| 1 | Never Touch Code | 不读/写/grep `.py/.js/.ts` 文件 | 角色越界，架构混乱 |
| 2 | Never Run Tests | 不执行 pytest / ssh 远程操作 | 职责混淆 |
| 3 | Never Write Architecture | 不写设计文档/定义接口 | Architect 角色被侵蚀 |
| 4 | Never Write Agent Prompts | 不自己写 prompt，交给 HR | HR 角色被侵蚀 |
| 5 | Never Poll Filesystem | 不写 `sleep` + `ls` 循环 | 效率低下，agent 应主动汇报 |
| 6 | Never Micromanage | 定义 what (成功标准)，不定义 how | 限制 agent 发挥 |
| 7 | Never Build Before Confirming | 先复述需求让用户确认 | 做错产品 |

### 1.3 The "Just Quickly" Trap

> **场景**: 你想"快速看一下"某个 `.py` 文件的实现细节。
>
> **正确做法**: 委托给 Engineer 或 QA。
>
> **为什么**: 一旦你开始读代码，你就会想改代码。一旦你改了代码，你就不再是 CEO 了。角色边界是组织效率的基础。

**Common Mistake**: 觉得"只是读一下不算违规"。但 Law 1 明确说 "Don't read `.py/.js/.ts` files"。读 = 执行层关注 = 角色漂移。

---

## Section 2: First 5 Minutes (前 5 分钟)

### 2.1 Reading Order (推荐阅读顺序)

新会话启动后，按以下顺序阅读：

```
1. CLAUDE.md                              → 项目概览 + 模块依赖
2. constitution.md                        → 6 篇宪法条款
3. agents/ceo-operations-manual.md        → CEO 角色手册
4. docs/team-initialization-protocol.md   → 4 角色 + 7 步
5. specs/delivery-protocol.md             → 交付验收标准
6. 本文档（你正在读的）                    → 实战操作指南
```

> 前 3 个文件是 CEO 的 **L0 必读文件**。读完这 3 个文件后，你应该清楚自己能做什么、不能做什么。

### 2.2 Recovery vs Fresh Start Decision Tree

```
                    ┌──────────────────────┐
                    │ Session start        │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ ls ~/.claude/teams/   │
                    │ Does a team exist?    │
                    └──────────┬───────────┘
                               │
                  ┌────────────┴────────────┐
                  │ YES                      │ NO
                  ▼                          ▼
     ┌────────────────────────┐  ┌─────────────────────┐
     │ Recovery Mode          │  │ Fresh Start Mode     │
     │                        │  │                      │
     │ 1. Read MEMORY.md      │  │ 1. Read MEMORY.md    │
     │ 2. Read team config    │  │    (may be empty)    │
     │ 3. Check state/ dir    │  │ 2. Await user needs  │
     │ 4. Check TaskList      │  │ 3. Follow §5 to     │
     │ 5. Resume or recreate  │  │    spawn team        │
     └────────────────────────┘  └─────────────────────┘
```

### 2.3 Environment Confirmation

在启动团队之前，确认以下环境条件：

```bash
# 确认项目目录存在
ls /home/coder/project/agent-orchestrator/

# 确认关键文件存在
ls /home/coder/project/agent-orchestrator/CLAUDE.md
ls /home/coder/project/agent-orchestrator/constitution.md
ls /home/coder/project/agent-orchestrator/agents/ceo-operations-manual.md

# 确认 pipeline 模块存在
ls /home/coder/project/agent-orchestrator/engineer/src/pipeline/

# 确认模板目录
ls /home/coder/project/agent-orchestrator/specs/pipelines/templates/

# 确认状态目录
ls /home/coder/project/agent-orchestrator/state/
```

### 2.4 Recovery Mode: Reading Team State

如果发现已有团队，按以下步骤恢复：

```
Step 1: Read team config
  → ~/.claude/teams/{team-name}/config.json
  → 提取 members[].name, agentType

Step 2: Read task list
  → TaskList tool
  → 哪些 pending / in_progress / completed

Step 3: Read state files
  → state/*.state.yaml
  → 当前 pipeline 进度

Step 4: Decide
  → Agents alive? → SendMessage to test
  → Agents dead? → Delete team → Recreate (see Emergency Protocols)
```

**Common Mistake**: 直接开始 spawn 新 agent 而不检查旧团队状态。这会导致 "Stale Team Conflict"（团队名冲突），需要先 `TeamDelete` 再 `TeamCreate`。

---

## Section 3: Pipeline System (理解 Pipeline)

### 3.1 Core Concepts (核心概念)

Agent Orchestrator 的核心洞见（见 `CLAUDE.md` §Architecture）：

> **Topology and personnel are orthogonal concerns.**
> Pipeline 定义做什么（topology），Agent 分配定义谁做（personnel）。

三个关键实体：

| Entity | 定义 | 示例 |
|--------|------|------|
| **Pipeline Template** | YAML 文件，定义 slot 顺序和依赖 | `standard-feature.yaml` |
| **Slot** | Pipeline 中的一个工作单元 | `architect-design`, `engineer-implement` |
| **Slot Type** | Slot 的能力要求定义 | `designer`, `implementer`, `reviewer` |

### 3.2 Slot Status State Machine

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ dependencies met
                    ┌────▼────┐
                    │  READY  │◄───────────────────────┐
                    └────┬────┘                        │
                         │ begin_slot()                │
                    ┌────▼─────┐                       │
                    │PRE_CHECK │                        │
                    └────┬─────┘                       │
                         │ pass                        │
                   ┌─────▼──────┐       ┌──────────┐   │
                   │IN_PROGRESS │──────►│ RETRYING │───┘
                   └─────┬──────┘ fail  └──────────┘
                         │ agent done
                   ┌─────▼──────┐
                   │POST_CHECK  │
                   └─────┬──────┘
                         │ pass
                   ┌─────▼──────┐
                   │ COMPLETED  │ (terminal)
                   └────────────┘

  Side paths:
    Any state ──fail──► FAILED ──retry_slot()──► RETRYING
    Any state ──skip──► SKIPPED (terminal)
```

关键转换规则（来源 `engineer/src/pipeline/state.py`）：

| From | Allowed To |
|------|-----------|
| PENDING | BLOCKED, READY, PRE_CHECK, IN_PROGRESS, SKIPPED, FAILED |
| BLOCKED | READY, PRE_CHECK, IN_PROGRESS, SKIPPED, FAILED |
| READY | PRE_CHECK, IN_PROGRESS, SKIPPED, FAILED |
| PRE_CHECK | IN_PROGRESS, FAILED |
| IN_PROGRESS | POST_CHECK, COMPLETED, FAILED, RETRYING |
| POST_CHECK | COMPLETED, FAILED |
| COMPLETED | *(terminal)* |
| FAILED | RETRYING, SKIPPED |
| SKIPPED | *(terminal)* |
| RETRYING | PRE_CHECK, IN_PROGRESS |

### 3.3 Pipeline Status State Machine

```
  LOADED → VALIDATED → RUNNING → COMPLETED → AUDITING → COMPLETED
                         │                                   │
                         ├──► PAUSED ──► RUNNING              │
                         │                                   │
                         ├──► FAILED ──► RUNNING (retry)     │
                         │                                   │
                         └──► ABORTED (terminal)             │
```

| From | Allowed To |
|------|-----------|
| LOADED | VALIDATED, RUNNING, ABORTED, COMPLETED, FAILED |
| VALIDATED | RUNNING, ABORTED |
| RUNNING | PAUSED, COMPLETED, FAILED, ABORTED |
| PAUSED | RUNNING, ABORTED |
| COMPLETED | AUDITING |
| FAILED | RUNNING |
| ABORTED | *(terminal)* |
| AUDITING | COMPLETED |

### 3.4 The 6 Pipeline Templates

来源：`specs/pipelines/templates/*.yaml`

| Template | Slots | Parameters | Use Case |
|----------|-------|-----------|----------|
| `standard-feature` | architect-design → engineer-implement → qa-review → ceo-approve → deploy | `feature_name` (req), `phase_id` (req), `target_module` (opt) | 标准功能开发 |
| `research-task` | research → architect-review → ceo-decision | `research_topic` (req), `research_brief` (req) | 调研任务（不产出代码） |
| `quant-strategy` | architect-scope → (signal-research ∥ strategy-design) → engineer-implement → qa-review → ceo-approve | `strategy_name` (req), `target_symbol` (def: BTC/USDT), `phase_id` (opt) | 量化策略开发（含并行阶段） |
| `hotfix` | engineer-fix → qa-review → ceo-approve → deploy | `bug_id` (req), `bug_description` (req), `affected_module` (req), `phase_id` (def: hotfix) | 紧急 bug 修复（跳过设计） |
| `security-hardening` | security-audit → architect-remediation → engineer-fix → qa-review → security-reaudit → ceo-approve | `audit_scope` (def: full), `phase_id` (def: security) | 安全加固（双审计） |
| `compliance-audit` | collect-evidence → process-audit → ceo-review-audit | `target_pipeline_id` (req), `target_state_file` (req), `audit_scope` (def: full), `phase_id` (def: audit) | 事后合规审计（只读） |

### 3.5 The 8 Slot Types

来源：`specs/pipelines/slot-types/*.yaml`

| Slot Type | Category | Required Capabilities | Key Outputs |
|-----------|----------|----------------------|-------------|
| `designer` | architecture | system_design, interface_definition, technical_documentation | design_doc |
| `researcher` | research | web_search, technical_analysis, structured_report_writing | research_report |
| `implementer` | engineering | python_development, test_writing, delivery_protocol | delivery_yaml, source_dir, test_dir |
| `reviewer` | quality | independent_testing, code_review, delivery_protocol, cross_validation | review_yaml, verdict |
| `approver` | governance | decision_making | decision (approved/rejected/deferred) |
| `deployer` | operations | deployment, ssh_operations, service_management | deployment_status |
| `auditor` | security | *(see YAML)* | audit_report |
| `compliance-auditor` | compliance | *(see YAML)* | evidence_manifest, audit_report |

**Common Mistake**: 混淆 Slot Type 和 Agent Role。Slot Type 定义能力需求，Agent Role 定义人员角色。一个 Agent 可以填充多种 Slot Type（只要它的 capabilities 是 slot type 的超集）。这就是 "topology ≠ personnel" 的含义。

---

## Section 4: End-to-End Walkthrough (端到端实战)

> **这是本文档的核心章节。**
>
> 场景：用户说 `"implement feature dashboard-v2 in phase6"`
>
> 我们将走完从接收需求到 pipeline 完成的完整 8 步流程。

### Step 1: Receive and Confirm Requirements (接收需求 — Law 7)

**铁律 7**: Never Build Before Confirming Requirements。

用户说了 `"implement feature dashboard-v2 in phase6"`，你**不能**立刻开始。必须先复述确认：

```
CEO → User:

"让我确认一下需求：
  - 功能名称: dashboard-v2
  - 所属阶段: phase6
  - 你希望我启动标准功能开发流程 (standard-feature pipeline)，包含：
    设计 → 实现 → QA → 审批 → 部署

  请确认这是你要的，或者补充更多细节。"
```

**等用户确认后才能继续。**

> Constitution §1.5 + CEO Manual Law 7: Confirmation > Speed.

### Step 2: NLMatcher — Template Matching (模板匹配)

用户确认后，使用 NLMatcher 将自然语言匹配到 pipeline 模板。

```python
from engineer.src.pipeline.nl_matcher import NLMatcher, TemplateMatch

# Initialize matcher with templates directory
matcher = NLMatcher(
    templates_dir="/home/coder/project/agent-orchestrator/specs/pipelines/templates"
)

# Match user input to templates
nl_input = "implement feature dashboard-v2 in phase6"
candidates: list[TemplateMatch] = matcher.match(nl_input)

# Expected output: list of TemplateMatch sorted by confidence
# candidates[0] should be:
#   TemplateMatch(
#       template_id="standard-feature",
#       template_path="specs/pipelines/templates/standard-feature.yaml",
#       confidence=0.85,         # high — "implement" + "feature" both match
#       matched_keywords=["implement", "feature"],
#       description="Standard feature development pipeline",
#       suggested_params={"feature_name": "dashboard-v2", "phase_id": "phase6"}
#   )
```

提取参数：

```python
# Extract parameters from natural language
params: dict[str, Any] = matcher.extract_params(nl_input, "standard-feature")

# Expected output:
# {
#     "feature_name": "dashboard-v2",
#     "phase_id": "phase6"
# }

# Generate human-readable summary for CEO review
summary: str = matcher.generate_summary(candidates[0], params)
print(summary)

# Expected output (format):
# Template: standard-feature
# Parameters: feature_name=dashboard-v2, phase_id=phase6
# Confidence: 0.85
```

**CEO 检查点**: 确认 `template_id` 和 `params` 是否正确。如果 `confidence < 0.5` 或匹配看起来不对，手动选择正确的模板。

**Pattern Extraction Reference** (NLMatcher 内置正则):

| Parameter | Pattern | Example |
|-----------|---------|---------|
| feature_name | word after "feature" / "功能" | `feature dashboard-v2` → `dashboard-v2` |
| phase_id | `phase[-_]?(\d+)` or `阶段\s*(\d+)` | `phase6` → `phase6` |
| bug_id | `[A-Z]{1,4}-\d{1,4}` | `BUG-42` |
| strategy_name | word after "strategy" / "策略" | `strategy momentum` → `momentum` |
| target_symbol | `[A-Z]{2,10}/[A-Z]{2,10}` | `BTC/USDT` |
| module_name | word after "module" / "模块" | `module auth` → `auth` |

### Step 3: PipelineRunner.prepare() — Load and Initialize (加载初始化)

```python
from engineer.src.pipeline.runner import PipelineRunner
from engineer.src.pipeline.models import Pipeline, PipelineState

# Initialize runner
runner = PipelineRunner(
    project_root="/home/coder/project/agent-orchestrator",
    templates_dir="/home/coder/project/agent-orchestrator/specs/pipelines/templates",
    state_dir="/home/coder/project/agent-orchestrator/state",
    slot_types_dir="/home/coder/project/agent-orchestrator/specs/pipelines/slot-types",
    agents_dir="/home/coder/project/agent-orchestrator/agents",
    constitution_path="/home/coder/project/agent-orchestrator/constitution.md",
)

# Prepare pipeline: load YAML → validate DAG → initialize state
pipeline, state = runner.prepare(
    yaml_path="specs/pipelines/templates/standard-feature.yaml",
    params={
        "feature_name": "dashboard-v2",
        "phase_id": "phase6",
    }
)

# Expected state after prepare():
#   state.pipeline_id = "standard-feature"
#   state.status = PipelineStatus.LOADED
#   state.definition_hash = "sha256:abc123..."  (hash of YAML content)
#   state.parameters = {"feature_name": "dashboard-v2", "phase_id": "phase6"}
#   state.slots = {
#       "architect-design":    SlotState(status=PENDING),
#       "engineer-implement":  SlotState(status=PENDING),
#       "qa-review":           SlotState(status=PENDING),
#       "ceo-approve":         SlotState(status=PENDING),
#       "deploy":              SlotState(status=PENDING),
#   }
```

**prepare() 内部做了什么**:
1. 从 `yaml_path` 加载 YAML 模板
2. 用 `params` 替换模板中的变量
3. 验证 DAG（检查 `depends_on` 无环、所有引用有效）
4. 计算 `definition_hash`（YAML 内容的 sha256）
5. 初始化所有 slot 为 `PENDING`
6. 创建 state 文件：`state/{pipeline_id}-{ISO-timestamp}.state.yaml`

**异常处理**:
| Exception | 含义 | CEO 动作 |
|-----------|------|----------|
| `PipelineLoadError` | YAML 文件不存在或格式错 | 检查模板路径 |
| `PipelineParameterError` | 必填参数缺失 | 补充参数重试 |
| `PipelineExecutionError` | 验证失败 | 检查 DAG 定义 |

### Step 4: SlotRegistry — Find Compatible Agents (查找兼容 Agent)

在执行 pipeline 之前，需要知道每个 slot 需要什么样的 agent。

```python
from engineer.src.pipeline.slot_registry import SlotRegistry

registry = SlotRegistry(
    slot_types_dir="/home/coder/project/agent-orchestrator/specs/pipelines/slot-types",
    agents_dir="/home/coder/project/agent-orchestrator/agents",
)

# For the first slot (architect-design), find compatible agents
matches = registry.find_compatible_agents("designer")

# Expected output: list of CapabilityMatch, sorted by capability count descending
# [
#     CapabilityMatch(
#         agent_id="architect",
#         is_compatible=True,
#         matched_capabilities=["system_design", "interface_definition", "technical_documentation"],
#         missing_capabilities=[],
#     ),
# ]

# Can also validate a specific assignment
result = registry.validate_assignment("designer", "architect")
# result.is_compatible == True
```

**Matching Rule**: Agent 的 capabilities 必须是 slot type 的 `required_capabilities` 的**超集**。

```
Agent capabilities ⊇ Slot type required_capabilities → compatible
```

**Generate Manifest for HR**:

```python
manifest = registry.generate_slot_manifest(pipeline)
# Returns SlotManifest with all slots + their required capabilities
# HR uses this to recruit/assign agents
```

### Step 5: TeamCreate + Spawn Agents (团队创建 + 派遣 Agent)

现在从 Python API 回到 Claude Code 操作层。使用 Claude Code 工具创建团队并派遣 agent。

**Step 5a: Create Team**

```
# Claude Code tool call
TeamCreate(
    team_name="dashboard-v2",
    description="Implementing dashboard-v2 feature in phase6"
)
```

**Step 5b: Create Tasks**

```
# Create tasks for each pipeline slot
TaskCreate(subject="Design dashboard-v2", description="...")
TaskCreate(subject="Implement dashboard-v2", description="...")
TaskCreate(subject="QA review dashboard-v2", description="...")
TaskCreate(subject="CEO approve dashboard-v2", description="...")
TaskCreate(subject="Deploy dashboard-v2", description="...")
```

**Step 5c: Spawn Agents with 6-Element Prompt**

每个 agent spawn prompt 必须包含 6 个要素（来源 `agents/ceo-operations-manual.md` §4.1）：

```
Spawn Prompt Template:
╔══════════════════════════════════════════════════════════════╗
║ 1. IDENTITY                                                  ║
║    "You are {AGENT_ID}, the {Role Title} for {Project Name}" ║
║                                                              ║
║ 2. SESSION CONTEXT                                           ║
║    Project: agent-orchestrator                               ║
║    Phase: {phase_id}                                         ║
║    Team: {team_name}                                         ║
║    Date: {today}                                             ║
║                                                              ║
║ 3. REQUIRED READING                                          ║
║    - agents/{role}.md  (your role handbook)                   ║
║    - docs/team-communication-standards.md                    ║
║    - docs/team-initialization-protocol.md                    ║
║    - {relevant PRD/design docs}                              ║
║                                                              ║
║ 4. ORGANIZATIONAL STATE                                      ║
║    Completed: {list}                                         ║
║    In-progress: {list}                                       ║
║    Known issues: {list}                                      ║
║    Dependencies: {list}                                      ║
║                                                              ║
║ 5. ASSIGNMENT                                                ║
║    {Specific bounded task description}                       ║
║                                                              ║
║ 6. SUCCESS CRITERIA                                          ║
║    {Quantitative KPIs + expected deliverables}               ║
╚══════════════════════════════════════════════════════════════╝
```

**Example: Spawning Architect**

```
Task(
    subagent_type="general-purpose",
    team_name="dashboard-v2",
    name="architect",
    model="opus",               # Opus for architecture (CEO Manual model selection)
    prompt="""
You are ARCH-001, the Lead Architect for agent-orchestrator.

## Session Context
- Project: agent-orchestrator
- Phase: phase6
- Team: dashboard-v2
- Date: 2026-02-26

## Required Reading (read these files FIRST)
1. agents/architect.md
2. docs/team-communication-standards.md
3. constitution.md (Articles 2, 3)

## Organizational State
- This is a new feature, no prior work exists
- Pipeline: standard-feature, slot: architect-design
- Downstream: engineer-implement depends on your design doc

## Assignment
Design the dashboard-v2 feature. Produce a design document covering:
- Component architecture
- Data model
- API design
- Integration points with existing pipeline system

## Success Criteria
- [ ] Design doc written to architect/ directory
- [ ] All interfaces have typed signatures
- [ ] Dependency diagram included
- [ ] No code in design doc (Constitution §5.4: directory write isolation)
""")
```

**Model Selection Guide** (来源 CEO Manual):

| Role | Recommended Model | 原因 |
|------|------------------|------|
| Architect | Opus 4.6 | 需要深度推理和系统设计能力 |
| Engineer (complex) | Opus 4.6 | 复杂实现需要强推理 |
| Engineer (standard) | Sonnet 4.6 | 标准实现够用 |
| QA | Sonnet 4.6 | 审查和测试不需要最强推理 |
| HR | Sonnet 4.6 | Prompt 编写 |
| PMO | Sonnet 4.6 | 任务分解 |
| PM | Sonnet 4.6 | 需求理解 |
| Simple tasks | Haiku 4.5 | 简单文件组织、常规查找 |

### Step 6: Pipeline Execution Loop (Pipeline 执行循环)

Pipeline 执行是一个循环：找就绪 slot → 开始执行 → agent 工作 → 完成/失败。

```python
from engineer.src.pipeline.models import SlotStatus, PipelineStatus, Slot

# === Main Execution Loop ===

# Step 6a: Get next slots ready to execute
ready_slots: list[Slot] = runner.get_next_slots(pipeline, state)
# Returns Slot objects whose dependencies are all COMPLETED/SKIPPED
# For standard-feature, initially only "architect-design" is ready

# Step 6b: Begin a slot
for slot in ready_slots:
    state = runner.begin_slot(
        slot=slot,
        pipeline=pipeline,
        state=state,
        agent_id="ARCH-001",          # optional: track which agent
        agent_prompt="Design ...",     # optional: record the prompt
    )
    # begin_slot() does:
    #   1. Check pre-conditions (gate_checker)
    #   2. If pass: status → IN_PROGRESS
    #   3. If fail: status → FAILED
    #   4. Build context via context_router (non-critical)
    #   5. Save state

# Step 6c: Agent works... (asynchronous, CEO monitors via messages)
# Agent sends DELIVERY.yaml when done

# Step 6d: Complete the slot
state = runner.complete_slot(
    slot_id="architect-design",
    pipeline=pipeline,
    state=state,
)
# complete_slot() does:
#   1. Check post-conditions (gate_checker)
#   2. If pass: status → COMPLETED
#   3. If fail: status → FAILED
#   4. Check if pipeline is complete
#   5. Save state

# Step 6e: Repeat — next slots become ready
ready_slots = runner.get_next_slots(pipeline, state)
# Now "engineer-implement" should be ready
# (its dependency "architect-design" is COMPLETED)
```

**Execution Loop Pseudocode** (CEO 视角):

```
while pipeline not complete:
    ready_slots = runner.get_next_slots(pipeline, state)

    if no ready_slots and pipeline not complete:
        → All slots blocked or failed
        → Check for failures, retry or skip (see §7)

    for slot in ready_slots:
        1. begin_slot(slot, ...)           → status: IN_PROGRESS
        2. Assign agent (SendMessage)      → agent starts working
        3. Wait for agent delivery         → agent sends DELIVERY.yaml
        4. Validate delivery (see §6)      → CEO checks metrics
        5. If QA needed, wait for REVIEW   → QA sends REVIEW.yaml
        6. complete_slot(slot_id, ...)      → status: COMPLETED

    # After each slot completion, new slots may become ready
```

**Important**: CEO 不直接执行这个 Python 循环。这些方法由 Engineer 执行。CEO 的职责是：
1. 指挥 Engineer 调用正确的方法
2. 在每个 slot 之间做验收决策
3. 处理失败（retry/skip/abort）

### Step 7: Validate Delivery (验收交付)

当 agent 完成一个 slot，它应提交 `DELIVERY.yaml`。CEO 必须验证。

**DELIVERY.yaml 关键检查项** (来源 `specs/delivery-protocol.md`):

```yaml
# DELIVERY.yaml v1.1 — CEO 检查清单
version: "1.1"
agent_id: "ENG-001"
agent_name: "engineer"
task_id: "phase6-dashboard-v2"
timestamp: "2026-02-26T10:30:00Z"
status: "complete"                    # ← Must be: complete/partial/blocked

deliverables:
  - path: "engineer/src/pipeline/dashboard.py"
    type: "source"
    checksum: "sha256:abc123..."      # ← CEO: checksum 格式正确？
    loc: 250                          # ← CEO: 行数合理？

test_results:
    runner: "pytest"
    command: "python -m pytest tests/ -v"
    total: 45                         # ← CEO: 测试数量足够？
    passed: 45
    failed: 0                         # ← CEO: 必须为 0
    coverage_pct: 92.5                # ← CEO: >= 85% (Constitution §4)

verification_steps:                    # ← v1.1 Anti-Hallucination
  - step: "pytest"
    command: "python -m pytest tests/ -v"
    status: "success"                  # ← strict enum: success/failure/skipped
    stdout_hash: "sha256:def456..."   # ← verifiable hash
    metrics:
      tests_passed: 45
  - step: "ruff"
    command: "ruff check ."
    status: "success"
    stdout_hash: "sha256:789ghi..."
```

**CEO 的 5 项验收检查**:

```
☑ 1. status == "complete"（不是 "partial" 或 "blocked"）
☑ 2. All checksums are sha256 format (sha256:<64 hex chars>)
☑ 3. test_results.failed == 0 AND coverage_pct >= 85%
☑ 4. verification_steps: 至少 1 个 step，全部 status == "success"
☑ 5. 如有 golden_dataset: all status == "success", failed == 0
```

**REVIEW.yaml — QA 独立审查** (来源 `specs/delivery-protocol.md`):

```yaml
# REVIEW.yaml v1.1 — QA 独立审查结果
version: "1.1"
agent_id: "QA-001"
agent_name: "qa"
timestamp: "2026-02-26T11:00:00Z"

target:
  agent: "ENG-001"
  delivery: "DELIVERY.yaml"
  task_id: "phase6-dashboard-v2"

verdict: "pass"                       # ← Decision table derived

delivery_checksum: "sha256:xyz789..." # ← QA recorded at review start

issues: []                            # ← No issues found

independent_metrics:
  test_results:
    command: "python -m pytest tests/ -v"
    total: 45
    passed: 45
    failed: 0
    coverage_pct: 92.5
    stdout_hash: "sha256:aaa111..."

cross_validation:                      # ← v1.1 Anti-Hallucination chain
    test_count_match: true             # ← ENG said 45, QA got 45
    test_pass_match: true              # ← Both say 45 passed
    coverage_delta: 0.0                # ← |ENG - QA| delta
    coverage_threshold: 2.0            # ← Max allowed delta
    suspicious: false                  # ← ⚠️ THIS IS THE KEY FLAG
    details: "All metrics match"

summary:
    total_issues: 0
    p0_count: 0
    p1_count: 0
    blocking: false
    recommendation: "Approve for deployment"
```

**Anti-Hallucination Defense Chain** (4 层防护):

```
Layer 1: Engineer claims results in DELIVERY.yaml
Layer 2: QA independently runs tests → records in REVIEW.yaml
Layer 3: Cross-validation compares Engineer vs QA metrics
Layer 4: CEO checks suspicious flag

If suspicious == true → DEPLOYMENT BLOCKED (Constitution §4.6)
No exceptions. No overrides.
```

**Verdict Decision Table** (QA 用，CEO 验证):

| Condition | Verdict |
|-----------|---------|
| Any P0 issue | `fail` |
| P1 with `fix_required=true` | `fail` |
| P1 non-blocking | `conditional_pass` |
| Max severity P2 | `conditional_pass` |
| Max severity P3 or no issues | `pass` |

**CEO 的 REVIEW.yaml 检查**:

```
☑ 1. verdict 是 pass 或 conditional_pass（fail → 不能继续）
☑ 2. cross_validation.suspicious == false（true → 阻止部署）
☑ 3. delivery_checksum 与实际 DELIVERY.yaml 匹配（不匹配 → 过期审查）
☑ 4. test_count_match == true AND test_pass_match == true
☑ 5. coverage_delta <= coverage_threshold
```

### Step 8: Pipeline Completion (Pipeline 完成)

所有 slot 都 COMPLETED 后：

```python
# Check if pipeline is complete
summary: str = runner.get_summary(state)
print(summary)

# Expected output:
# Pipeline: standard-feature
# Status: COMPLETED
# Progress: 5/5 slots completed
#
# Slots:
#   architect-design:    COMPLETED
#   engineer-implement:  COMPLETED
#   qa-review:           COMPLETED
#   ceo-approve:         COMPLETED
#   deploy:              COMPLETED

# Optional: Start auditing phase
state = runner.start_auditing(state)
# state.status → AUDITING
# Can run compliance-audit pipeline afterwards
```

**Post-Pipeline CEO Checklist**:

```
☑ 1. get_summary() shows all slots COMPLETED (or SKIPPED with justification)
☑ 2. No suspicious flags in any REVIEW.yaml
☑ 3. All DELIVERY.yaml checksums verified
☑ 4. State file saved (auto by runner)
☑ 5. Update MEMORY.md with completion note
☑ 6. Shutdown team (SendMessage type: "shutdown_request")
☑ 7. Archive state if needed (see §8)
```

**Shutting Down the Team**:

```
# Send shutdown requests to all team members
SendMessage(type="shutdown_request", recipient="architect", content="Pipeline complete, shutting down")
SendMessage(type="shutdown_request", recipient="engineer", content="Pipeline complete, shutting down")
SendMessage(type="shutdown_request", recipient="qa", content="Pipeline complete, shutting down")

# Wait for approval responses, then
TeamDelete()
```

**Common Mistake**: 忘记在 pipeline 完成后更新 MEMORY.md。下次 session 的 CEO 将不知道这个 pipeline 已完成，可能会尝试重新执行。

---

## Section 5: Team Spawning (团队组建)

### 5.1 The 4 Founding Roles

来源：`docs/team-initialization-protocol.md`

每个团队**必须**先建立 4 个基础角色，然后才能开始任何实际工作：

| # | Role | 职责 | Model |
|---|------|------|-------|
| 1 | **CEO** | 战略协调、任务分配、最终验收 | *(你自己)* |
| 2 | **HR** | 调研角色、编写 agent prompt、招聘专家 | Sonnet 4.6 |
| 3 | **PM** | 需求理解、PRD 编写、需求验收 | Sonnet 4.6 |
| 4 | **PMO** | 任务分解、进度追踪、资源协调 | Sonnet 4.6 |

### 5.2 The 7-Step Initialization Workflow

来源：`docs/team-initialization-protocol.md`

```
Step 1: User states need
  → CEO confirms requirements (Law 7)

Step 2: PM + PMO discuss
  → Requirements clarification
  → Solution comparison
  → Priority ordering

Step 3: PM produces PRD, user confirms
  → Worked examples
  → Acceptance criteria
  → Negative scope (what NOT to build)

Step 4: HR recruits Architect
  → Research >= 5 sources for role design
  → Write tailored agent prompt
  → Spawn Architect with PRD

Step 5: Architect produces design doc
  → Tech selection
  → Data model
  → API design

Step 6: HR recruits remaining specialists
  → Engineers, QA, etc.
  → Tailored prompts per role

Step 7: PM distributes PRD; PMO creates tasks
  → Tasks with dependencies
  → Resource allocation
```

### 5.3 Why Steps Cannot Be Skipped

| Skipped Step | Consequence |
|-------------|------------|
| Skip PM | 需求误解，做错产品 |
| Skip Architect first | 无蓝图，工程师冲突，集成失败，返工 3-5x |
| Skip PMO | 任务无序，agent 阻塞在错误项上，重复劳动 |
| Skip HR / use generic prompts | Agent 角色漂移，质量差，职责混乱 |

### 5.4 Spawn Prompt Six Elements Checklist

每次 spawn agent 时，检查你的 prompt 是否包含所有 6 个要素：

```
☑ 1. IDENTITY — "You are {ID}, the {Role} for {Project}"
☑ 2. SESSION CONTEXT — project, phase, team, date
☑ 3. REQUIRED READING — role handbook, standards, protocol, PRD
☑ 4. ORGANIZATIONAL STATE — completed, in-progress, issues, deps
☑ 5. ASSIGNMENT — specific bounded task
☑ 6. SUCCESS CRITERIA — quantitative KPIs + deliverables
```

### 5.5 Common Spawning Patterns

**Pattern A: Sequential Pipeline** (e.g., standard-feature)

```
1. Spawn Architect → wait for design
2. Spawn Engineer → wait for implementation
3. Spawn QA → wait for review
4. CEO approves → Spawn deployer
```

**Pattern B: Parallel Phase** (e.g., quant-strategy)

```
1. Spawn Architect → wait for scope
2. Spawn Researcher + Designer simultaneously (parallel_group)
3. Wait for both → Spawn Engineer
```

**Pattern C: Hotfix** (skip design)

```
1. Spawn Engineer directly → fix
2. Spawn QA → review
3. CEO approves → Deploy
```

### 5.6 Mandatory Reading for All Agents

来源：`docs/team-initialization-protocol.md`

每个 agent 的 required reading 必须包含：

```
1. agents/{role}.md              — Role handbook (HR 编写)
2. docs/team-communication-standards.md — 沟通规范
3. docs/team-initialization-protocol.md — 初始化协议
4. {Active PRD/design doc}        — 当前任务的需求/设计文档
```

**Common Mistake**: 忘记在 spawn prompt 中指定 `team_name` 参数。没有 `team_name`，agent 就是一个独立 subagent，无法加入团队通讯和 TaskList。

---

## Section 6: Monitoring & Validation (监控验收)

### 6.1 Monitoring Active Pipeline

**get_summary()** — 查看 pipeline 整体进度：

```python
summary = runner.get_summary(state)
# Returns human-readable string:
# Pipeline: standard-feature
# Status: RUNNING
# Progress: 2/5 slots completed
#
# Slots:
#   architect-design:    COMPLETED
#   engineer-implement:  COMPLETED
#   qa-review:           IN_PROGRESS
#   ceo-approve:         PENDING
#   deploy:              PENDING
```

**TaskList** — 查看团队任务进度：

```
TaskList()
# Shows all tasks with status, owner, and blockedBy
```

**Agent Messages** — 自动推送，不需要轮询。Agent 完成工作后会通过 SendMessage 发送状态更新。

### 6.2 DELIVERY.yaml Validation Checklist

完整检查清单（来源 `specs/delivery-protocol.md` v1.1）：

```
=== DELIVERY.yaml CEO Validation ===

□ Top-level:
  □ version == "1.1"
  □ status ∈ {complete, partial, blocked}
  □ timestamp is valid ISO 8601

□ deliverables[]:
  □ Each has path, type, checksum, loc, language
  □ checksum format: sha256:<64 hex chars>
  □ loc > 0 (not zero)

□ test_results:
  □ total == passed + failed + skipped + errors
  □ failed == 0
  □ coverage_pct >= 85.0

□ verification_steps[] (v1.1 Anti-Hallucination):
  □ At least 1 step exists
  □ Each step.status ∈ {success, failure, skipped}  (NO natural language!)
  □ All steps have status == "success"
  □ If any step "failure" → top-level status CANNOT be "complete"
  □ stdout_hash format: sha256:<64 hex chars>
  □ If test_results exists → must have step=="pytest" with matching metrics

□ golden_dataset[] (if present):
  □ Each: passed + failed == test_count
  □ All status == "success"
  □ If any failed > 0 → top-level status CANNOT be "complete"

□ exports[]:
  □ Each has name, type, module, description
  □ type ∈ {dataclass, enum, abc, function, interface_impl, constant}
```

### 6.3 REVIEW.yaml Validation Checklist

```
=== REVIEW.yaml CEO Validation ===

□ Verdict:
  □ verdict ∈ {pass, conditional_pass, fail}
  □ Verdict matches decision table (see §4 Step 7)
  □ If any P0 issue → verdict MUST be "fail"

□ Cross-Validation (v1.1):
  □ cross_validation section exists
  □ test_count_match == true
  □ test_pass_match == true
  □ coverage_delta <= coverage_threshold (default 2.0%)
  □ suspicious == false

□ If suspicious == true:
  □ STOP. DO NOT APPROVE.
  □ Record in MEMORY.md
  □ Request QA re-run with fresh environment
  □ If still suspicious → reject delivery

□ delivery_checksum:
  □ Matches actual DELIVERY.yaml hash
  □ If mismatch → review is stale, request new review
```

### 6.4 Anti-Hallucination Defense Chain

```
CEO's 4-Layer Defense:

  ┌──────────────────────────────────────────────────┐
  │ Layer 1: Engineer Self-Report                     │
  │   DELIVERY.yaml with verification_steps           │
  │   + stdout_hash + checksums                       │
  └──────────────────┬───────────────────────────────┘
                     │ QA independently reproduces
  ┌──────────────────▼───────────────────────────────┐
  │ Layer 2: QA Independent Metrics                   │
  │   REVIEW.yaml with independent_metrics            │
  │   + own test run + own checksums                  │
  └──────────────────┬───────────────────────────────┘
                     │ System compares
  ┌──────────────────▼───────────────────────────────┐
  │ Layer 3: Cross-Validation                         │
  │   test_count_match, test_pass_match,              │
  │   coverage_delta, suspicious flag                 │
  └──────────────────┬───────────────────────────────┘
                     │ CEO reviews
  ┌──────────────────▼───────────────────────────────┐
  │ Layer 4: CEO Final Check                          │
  │   Check suspicious flag                           │
  │   Verify checksums                                │
  │   Approve or reject                               │
  └──────────────────────────────────────────────────┘
```

**Never trust a single agent's self-report.** CEO Manual 明确要求：总是要 QA 独立验证，然后交叉比对。

**Common Mistake**: Agent 说 "I finished all tests, everything passes" 然后 CEO 直接批准。正确做法：要求 DELIVERY.yaml + REVIEW.yaml，检查 `suspicious` flag。

---

## Section 7: Failure Recovery (故障恢复)

### 7.1 Slot Failure Handling

当一个 slot 失败时，CEO 有三个选项：

| Action | Method | When to Use |
|--------|--------|-------------|
| **Retry** | `runner.retry_slot()` | 临时故障、网络问题、可修复错误 |
| **Skip** | `runner.skip_slot()` | 非关键 slot、可以跳过 |
| **Fail** | `runner.fail_slot()` | 不可恢复、需要人工干预 |

#### retry_slot()

```python
# Retry a failed slot
state = runner.retry_slot(
    slot_id="engineer-implement",
    pipeline=pipeline,
    state=state,
    agent_id="ENG-002",        # optional: assign different agent
    agent_prompt="...",        # optional: updated instructions
)

# Internal flow:
#   1. Validate slot status == FAILED
#   2. Check retry_count < max_retries (default: 2, see ExecutionConfig)
#   3. Transition: FAILED → RETRYING → (PRE_CHECK →) IN_PROGRESS
#   4. Increment retry_count, clear error
#   5. Run pre-conditions again

# Raises PipelineExecutionError if:
#   - Slot is not in FAILED state
#   - retry_count >= max_retries (default 2)
```

**ExecutionConfig Defaults**:
```python
@dataclass
class ExecutionConfig:
    timeout_hours: float = 4.0
    retry_on_fail: bool = True
    max_retries: int = 2            # ← max 2 retries per slot
    parallel_group: str | None = None
```

#### skip_slot()

```python
# Skip a slot (CEO decision)
state = runner.skip_slot(
    slot_id="deploy",
    state=state,
)

# Internal flow:
#   1. Transition: current → SKIPPED
#   2. Unblock dependent slots (treated as satisfied)
#   3. Save state
```

> **注意**: 跳过一个 slot 会解锁它的下游依赖。确保跳过是合理的。

#### fail_slot()

```python
# Manually mark slot as failed
state = runner.fail_slot(
    slot_id="engineer-implement",
    error="Agent produced incorrect output, manual fix required",
    state=state,
)

# Internal flow:
#   1. Transition: current → FAILED
#   2. Record error message
#   3. Check if pipeline is complete (all terminal)
```

### 7.2 suspicious=true Recovery

**Constitution §4.6**: `suspicious=true` blocks deployment **unconditionally**.

```
If cross_validation.suspicious == true:

1. STOP — Do not approve, do not continue
2. Record in MEMORY.md:
   "⚠️ Suspicious flag on {slot_id} at {timestamp}. Details: {cross_validation.details}"
3. Ask QA to re-run in clean environment:
   SendMessage(
       type="message",
       recipient="qa",
       content="Cross-validation flagged suspicious. Re-run all tests in a clean environment and produce new REVIEW.yaml."
   )
4. Compare new results with original
5. If STILL suspicious → Reject delivery, request engineer re-implementation
6. If resolved → Update REVIEW.yaml, proceed
```

### 7.3 Pipeline Resume (断点续传)

当 session 中断后需要恢复：

```python
# Resume from saved state file
pipeline, state = runner.resume(
    state_path="/home/coder/project/agent-orchestrator/state/standard-feature-2026-02-26T10:00:00.state.yaml"
)

# Internal flow:
#   1. Load state from YAML file
#   2. Reload pipeline YAML (path stored in state)
#   3. Verify definition_hash matches (integrity check)
#   4. Return (pipeline, state) ready to continue

# If the YAML was modified since the state was created:
#   Raises PipelineExecutionError: "definition_hash mismatch"
#   → Use resume_with_pipeline() with explicit path instead
```

**resume_with_pipeline()** — 当 YAML 路径变了：

```python
pipeline, state = runner.resume_with_pipeline(
    state_path="state/standard-feature-2026-02-26T10:00:00.state.yaml",
    yaml_path="specs/pipelines/templates/standard-feature.yaml",
    params={"feature_name": "dashboard-v2", "phase_id": "phase6"},
)
```

### 7.4 Zombie Team Recovery

来源：`agents/ceo-operations-manual.md` Emergency Protocols

```
Symptom: Agents not responding to messages
Diagnosis: Team exists but agents are dead

Recovery Steps:
1. Check team exists:
   ls ~/.claude/teams/

2. Test agent responsiveness:
   SendMessage(type="message", recipient="engineer", content="Status check")

3. If no response after reasonable wait:
   TeamDelete()                    # Remove dead team

4. TeamCreate(team_name="dashboard-v2-r2")  # New name to avoid conflict

5. Re-spawn all agents with full context (6-element prompt)
   Include in ORGANIZATIONAL STATE:
   - "Previous session interrupted at slot {X}"
   - "State file: state/{file}.state.yaml"
   - "Completed work: {list from state}"
```

### 7.5 Cascading Failure Protocol

```
Trigger: Multiple agents failing simultaneously

Steps:
1. Broadcast HALT:
   SendMessage(type="broadcast", content="HALT — Cascading failure detected. All agents pause current work.")

2. Request PMO dependency analysis:
   SendMessage(type="message", recipient="pmo", content="Analyze failure dependencies. Which is the root cause?")

3. Fix root cause first (usually the earliest failing slot)

4. Resume in dependency order:
   - Fix slot A → retry_slot("A")
   - When A completes → dependents unblock automatically
   - Continue normal execution
```

### 7.6 Context Limit Emergency

```
Trigger: Approaching token limit (system warning)

Steps:
1. Request PMO summary:
   SendMessage(type="message", recipient="pmo", content="Generate completion status report for handoff")

2. Update MEMORY.md:
   - Current pipeline state
   - Completed slots
   - In-progress slots and their status
   - Known issues
   - State file path

3. Shutdown all agents:
   SendMessage(type="shutdown_request", recipient="architect", ...)
   SendMessage(type="shutdown_request", recipient="engineer", ...)

4. Write handoff note in MEMORY.md:
   "Session ended at {timestamp}. Resume from state/{file}.state.yaml"

5. End session
```

**Common Mistake**: 在 cascading failure 时逐个 retry 每个 slot 而不找根因。通常一个上游 slot 的失败导致了所有下游失败——修好上游，下游自动恢复。

---

## Section 8: State Management (状态管理)

### 8.1 State File Location and Format

```
State directory: /home/coder/project/agent-orchestrator/state/
File naming:     {pipeline_id}-{ISO-timestamp}.state.yaml
Example:         state/standard-feature-2026-02-26T10-00-00.state.yaml
```

**State File Structure**:

```yaml
# state/standard-feature-2026-02-26T10-00-00.state.yaml
pipeline_id: "standard-feature"
pipeline_version: "1.0.0"
definition_hash: "sha256:abc123..."     # hash of pipeline YAML (integrity)
status: "running"                        # PipelineStatus enum
started_at: "2026-02-26T10:00:00Z"
completed_at: null                       # set when terminal
parameters:
  feature_name: "dashboard-v2"
  phase_id: "phase6"
yaml_path: "specs/pipelines/templates/standard-feature.yaml"
slots:
  architect-design:
    slot_id: "architect-design"
    status: "completed"
    started_at: "2026-02-26T10:01:00Z"
    completed_at: "2026-02-26T10:15:00Z"
    retry_count: 0
    error: null
    agent_id: "ARCH-001"
    agent_prompt: "..."
    pre_check_results: [...]
    post_check_results: [...]
  engineer-implement:
    slot_id: "engineer-implement"
    status: "in_progress"
    started_at: "2026-02-26T10:16:00Z"
    completed_at: null
    retry_count: 0
    ...
```

### 8.2 Atomic Writes (原子写入)

**Constitution §2.5**: Atomic state file writes (temp file + rename).

```python
# How state.py implements atomic writes internally:
#   1. Write to temp file: state/{pipeline_id}-{ts}.state.yaml.tmp
#   2. os.rename(tmp_path, final_path)  # atomic on POSIX
#   3. Never leaves partial file on crash
```

CEO 不需要手动实现这个——`PipelineStateTracker` 自动处理。但你需要知道：
- State 文件是**安全的**，即使进程崩溃也不会损坏
- 如果看到 `.tmp` 文件，说明写入被中断——可以删除

### 8.3 definition_hash (完整性校验)

```python
# definition_hash = sha256 of pipeline YAML content
# Computed at prepare() time, stored in state

# On resume(), runner verifies:
#   sha256(current YAML) == state.definition_hash
# If mismatch → PipelineExecutionError
# This prevents: modified YAML + old state = inconsistent execution
```

**When hash mismatch occurs**:
- Pipeline YAML was edited between sessions
- Options:
  1. Use `resume_with_pipeline()` with new params (re-validate)
  2. Start fresh with `prepare()` (lose progress)

### 8.4 PipelineStateTracker Key Methods

```python
class PipelineStateTracker:

    def init_state(
        pipeline: Pipeline,
        params: dict[str, Any],
        yaml_path: str | None = None
    ) -> PipelineState:
        """Create initial state with all slots PENDING."""

    def update_pipeline_status(
        state: PipelineState,
        status: PipelineStatus
    ) -> PipelineState:
        """
        Update pipeline status.
        Auto-sets started_at (RUNNING, once) and completed_at (terminal).
        Raises InvalidTransitionError on invalid transition.
        """

    def update_slot(
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
        """
        Update slot status.
        Auto-sets started_at (IN_PROGRESS) and completed_at (terminal).
        Raises InvalidTransitionError on invalid transition.
        """

    def get_ready_slots(
        pipeline: Pipeline,
        state: PipelineState
    ) -> list[str]:
        """
        Find slot IDs ready to execute.
        Checks: PENDING/BLOCKED status + all deps COMPLETED/SKIPPED.
        Returns list of slot ID strings (not Slot objects).
        """

    def is_complete(state: PipelineState) -> bool:
        """True if all slots are terminal (COMPLETED/SKIPPED/FAILED)."""
```

### 8.5 MEMORY.md Management

State 文件管理 pipeline 状态。MEMORY.md 管理**跨 session 的组织记忆**。

```
CEO 必须在以下时机更新 MEMORY.md:
  ✓ Pipeline 完成时 — 记录完成的功能
  ✓ Session 结束前 — 记录当前进度
  ✓ 重大决策时 — 记录决策理由
  ✓ Failure 发生时 — 记录故障和修复

MEMORY.md 不该包含:
  ✗ 代码片段
  ✗ 临时调试信息
  ✗ 重复已有文档的内容
```

**Common Mistake**: 只依赖 state 文件而不更新 MEMORY.md。State 文件记录 pipeline 机器状态，MEMORY.md 记录组织上下文（为什么这样做、什么决策、什么问题）。两者互补。

---

## Section 9: Context Management (上下文管理)

### 9.1 Three-Tier Context System (L0/L1/L2)

来源：`CLAUDE.md` + `engineer/src/pipeline/context_router.py`

| Tier | File Suffix | Tokens | Load When | 用途 |
|------|------------|--------|-----------|------|
| **L0** | `.abstract.md` | ~100 | Always | 一句话摘要，永远加载 |
| **L1** | `.overview.md` | ~2K | Topic relevant | 概览，相关时加载 |
| **L2** | Source files | Full | Editing/reviewing | 完整源文件 |

### 9.2 Context Paths

```
agents/.abstract.md          → agents/.overview.md          → agents/*.md
architect/.abstract.md       → architect/.overview.md       → architect/*.md
engineer/src/pipeline/.abstract.md → .overview.md           → *.py
specs/.abstract.md           → specs/.overview.md           → specs/*.md
specs/pipelines/templates/.abstract.md → .overview.md       → *.yaml
specs/pipelines/slot-types/.abstract.md → .overview.md      → *.yaml
state/.abstract.md           → state/.overview.md           → *.yaml
```

### 9.3 Slot Type → Directory Mapping

来源：`engineer/src/pipeline/context_router.py`

```python
_SLOT_DIRECTORY_MAP: dict[str, list[str]] = {
    "designer":     ["specs/", "architect/"],
    "researcher":   ["specs/", "agents/", "docs/"],
    "implementer":  ["engineer/src/pipeline/", "specs/pipelines/"],
    "reviewer":     ["engineer/src/pipeline/", "specs/"],
    "approver":     ["architect/", "specs/"],
    "auditor":      ["compliance-auditor/", "specs/"],
    "deployer":     ["engineer/", "state/"],
}
```

这张映射表告诉 ContextRouter：当一个 slot 类型是 `implementer` 时，应该给它 `engineer/src/pipeline/` 和 `specs/pipelines/` 下的上下文文件。

### 9.4 ContextRouter API

```python
class ContextRouter:

    def __init__(
        self,
        project_root: str,
        constitution_path: str
    ) -> None:
        """Initialize with project root and constitution path."""

    def build_context(
        self,
        slot: Slot,
        pipeline: Pipeline,
        *,
        max_tokens: int = 8000
    ) -> list[ContextItem]:
        """
        Build tiered context list for a slot.
        Steps:
          1. Constitution always at L2
          2. Load all L0 (.abstract.md) files
          3. Based on slot_type, load relevant L1 (.overview.md)
          4. Upgrade within token budget
        Returns: Ordered list of ContextItem within budget
        """

    def get_constitution(self) -> str:
        """Read and return constitution.md content."""

    def get_mandatory_reads(self, slot_type: str) -> list[str]:
        """Return directory prefixes for slot type from _SLOT_DIRECTORY_MAP."""

    def upgrade_tier(
        self,
        item: ContextItem,
        target: ContextTier
    ) -> ContextItem:
        """
        Upgrade ContextItem to higher tier.
          L0 → L1: .abstract.md → .overview.md
          L1 → L2: .overview.md → source file
        Raises: ValueError, FileNotFoundError
        """

    def generate_slot_context_yaml(
        self,
        items: list[ContextItem]
    ) -> str:
        """Generate YAML string describing context items."""
```

### 9.5 ContextItem and ContextTier

```python
class ContextTier(StrEnum):
    L0 = "abstract"    # ~100 tokens
    L1 = "overview"    # ~2K tokens
    L2 = "detail"      # Full source file

@dataclass(frozen=True)
class ContextItem:
    path: str              # file path
    tier: ContextTier      # current tier
    relevance: float       # 0.0-1.0
    tokens_estimate: int   # estimated token count
```

### 9.6 How CEO Uses Context Management

CEO 自己不直接调用 ContextRouter（那是 Engineer 的事），但需要理解它的工作方式来：

1. **确保 spawn prompt 的 Required Reading 与 slot type 对齐**
   - 给 designer spawn 时，提到 `specs/` 和 `architect/` 下的文件
   - 给 implementer spawn 时，提到 `engineer/src/pipeline/` 和 `specs/pipelines/` 下的文件

2. **在 6-element prompt 中指定上下文层级**
   - "Read L2 (full detail) for your assigned module"
   - "Read L0 (abstracts) for other modules to understand boundaries"

3. **控制 token 预算**
   - 默认 `max_tokens=8000` for context
   - 如果 agent 任务简单，可以减少
   - 如果 agent 需要全局视野（如 Architect），可以增加

**Common Mistake**: 给所有 agent 一样的上下文。Designer 不需要看 `engineer/src/pipeline/` 的代码，Implementer 不需要看 `compliance-auditor/` 的文件。使用 `_SLOT_DIRECTORY_MAP` 对齐上下文。

---

## Section 10: Quick Reference (速查手册)

### 10.1 API One-Line Reference

```python
# === PipelineRunner ===
runner = PipelineRunner(project_root, templates_dir, state_dir, slot_types_dir, agents_dir, constitution_path=...)
pipeline, state = runner.prepare(yaml_path, params)            # Load + validate + init
ready = runner.get_next_slots(pipeline, state)                  # Get ready Slot objects
state = runner.begin_slot(slot, pipeline, state, agent_id=...) # Pre-check → IN_PROGRESS
state = runner.complete_slot(slot_id, pipeline, state)          # Post-check → COMPLETED
state = runner.fail_slot(slot_id, error, state)                # → FAILED
state = runner.skip_slot(slot_id, state)                       # → SKIPPED (unblocks deps)
state = runner.retry_slot(slot_id, pipeline, state, agent_id=...)  # FAILED → RETRYING → IN_PROGRESS
summary = runner.get_summary(state)                             # Human-readable status
state = runner.start_auditing(state)                            # COMPLETED → AUDITING
pipeline, state = runner.resume(state_path)                     # Resume from state file
pipeline, state = runner.resume_with_pipeline(state_path, yaml_path, params)

# === NLMatcher ===
matcher = NLMatcher(templates_dir)
candidates = matcher.match(nl_input)                            # → list[TemplateMatch]
params = matcher.extract_params(nl_input, template_id)          # → dict
summary = matcher.generate_summary(match, params)               # → str

# === SlotRegistry ===
registry = SlotRegistry(slot_types_dir, agents_dir)
agents = registry.find_compatible_agents(slot_type_id)          # → list[CapabilityMatch]
result = registry.validate_assignment(slot_type_id, agent_id)   # → CapabilityMatch
manifest = registry.generate_slot_manifest(pipeline)            # → SlotManifest

# === ContextRouter ===
router = ContextRouter(project_root, constitution_path)
items = router.build_context(slot, pipeline, max_tokens=8000)   # → list[ContextItem]
text = router.get_constitution()                                # → str
dirs = router.get_mandatory_reads(slot_type)                    # → list[str]
upgraded = router.upgrade_tier(item, target_tier)               # → ContextItem
yaml_str = router.generate_slot_context_yaml(items)             # → str

# === PipelineStateTracker ===
state = tracker.init_state(pipeline, params, yaml_path=...)     # → PipelineState
state = tracker.update_pipeline_status(state, status)           # → PipelineState
state = tracker.update_slot(state, slot_id, status, error=...)  # → PipelineState
ready_ids = tracker.get_ready_slots(pipeline, state)            # → list[str]
done = tracker.is_complete(state)                               # → bool
```

### 10.2 Key Paths Table

| Path | Content |
|------|---------|
| `CLAUDE.md` | Project overview + module deps + context mgmt |
| `constitution.md` | 6 Articles, 50+ clauses |
| `agents/ceo-operations-manual.md` | CEO role handbook |
| `agents/*.md` | Agent role handbooks (HR-written) |
| `docs/team-initialization-protocol.md` | 4 roles + 7 steps |
| `docs/team-communication-standards.md` | Communication rules |
| `specs/delivery-protocol.md` | DELIVERY + REVIEW YAML specs |
| `specs/pipelines/templates/*.yaml` | 6 pipeline templates |
| `specs/pipelines/slot-types/*.yaml` | 8 slot type definitions |
| `engineer/src/pipeline/*.py` | 12 pipeline modules |
| `engineer/src/pipeline/models.py` | Enums + Dataclasses |
| `engineer/src/pipeline/runner.py` | PipelineRunner (orchestrator) |
| `engineer/src/pipeline/state.py` | State persistence + transitions |
| `engineer/src/pipeline/nl_matcher.py` | NL → template matching |
| `engineer/src/pipeline/slot_registry.py` | Agent-slot matching |
| `engineer/src/pipeline/context_router.py` | L0/L1/L2 context routing |
| `state/*.state.yaml` | Pipeline state files |

### 10.3 Five Common Patterns

**Pattern 1: Start New Feature**
```
1. Confirm requirements (Law 7)
2. NLMatcher.match() → template
3. runner.prepare() → pipeline, state
4. TeamCreate → spawn founding roles (HR, PM, PMO)
5. Follow 7-step init → spawn specialists
6. Execute pipeline loop (§4 Step 6)
```

**Pattern 2: Resume Interrupted Session**
```
1. Read MEMORY.md → find state file path
2. runner.resume(state_path) → pipeline, state
3. runner.get_summary(state) → check progress
4. Check team: ls ~/.claude/teams/
5. Re-spawn team if needed → continue execution
```

**Pattern 3: Handle Failure**
```
1. Identify failed slot from get_summary()
2. Read error from state.slots[slot_id].error
3. Decide: retry (retry_slot) / skip (skip_slot) / abort
4. If retry: check retry_count < max_retries (2)
5. Spawn new agent if needed (different model/prompt)
```

**Pattern 4: Emergency Hotfix**
```
1. NLMatcher.match("hotfix BUG-42 in module auth") → hotfix template
2. runner.prepare() with bug_id, bug_description, affected_module
3. Skip Architect (hotfix template doesn't have design slot)
4. Spawn Engineer → fix → QA review → approve → deploy
```

**Pattern 5: Post-Pipeline Audit**
```
1. After pipeline COMPLETED, optionally:
2. runner.start_auditing(state) → AUDITING
3. Prepare compliance-audit template:
   params = {target_pipeline_id: "...", target_state_file: "..."}
4. Execute compliance-audit pipeline (read-only)
5. Review audit report → finalize
```

### 10.4 SlotStatus Transition Quick Reference

```
PENDING ──────► READY ──────► PRE_CHECK ──────► IN_PROGRESS ──────► POST_CHECK ──────► COMPLETED
   │               │              │                  │                  │
   │               │              │                  ├───► FAILED ──────┤
   │               │              │                  │        │         │
   │               │              └──► FAILED        │    RETRYING      │
   │               │                     │           │     │  │         │
   │               └──► SKIPPED          └─► SKIPPED │     │  └──► PRE_CHECK
   │                                                 │     │
   └──► BLOCKED ──► READY                            └─► RETRYING
                                                           │
                                                           └──► IN_PROGRESS
```

### 10.5 Enum Values Quick Reference

**SlotStatus**: `pending | blocked | ready | pre_check | in_progress | post_check | completed | failed | skipped | retrying`

**PipelineStatus**: `loaded | validated | running | paused | completed | failed | aborted | auditing`

**ArtifactType**: `design_doc | code | test_code | delivery_yaml | review_yaml | config | research | audit_report | agent_prompt | approval | deployment | slot_output`

**ConditionType**: `file_exists | slot_completed | approval | artifact_valid | delivery_valid | review_valid | tests_pass | checksum_match | custom`

**ValidationLevel**: `checksum | schema | exists | none`

**ContextTier**: `abstract (L0) | overview (L1) | detail (L2)`

### 10.6 Constitution Cross-Reference

| Need | Article |
|------|---------|
| CEO never codes | §1.1 |
| Process > speed | §1.3 |
| User words verbatim | §1.6 |
| Python 3.11+ only | §2.1 |
| PyYAML only, no external deps | §2.2 |
| `yaml.safe_load()` only | §2.3, §6.1 |
| Zero cross-package imports | §2.4 |
| Atomic state writes | §2.5, §6.3 |
| Pipeline immutable after load | §2.6 |
| Topology ≠ personnel | §3.1 |
| Interface-first design | §3.3 |
| No DELIVERY = no delivery | §4.1 |
| No REVIEW = no verdict | §4.2 |
| Checksum integrity | §4.3 |
| `suspicious=true` blocks deploy | §4.6 |
| Strict enum status codes | §4.7 |
| Cross-validation mandatory | §4.9 |
| Fail-open strategy | §4.10 |
| Directory write isolation | §4.11, §5.4 |
| No `shell=True` | §6.2 |
| `definition_hash` integrity | §6.6 |

---

## Appendix A: Anti-Pattern Catalog (反模式目录)

来源：`agents/ceo-operations-manual.md` §9

| # | Anti-Pattern | Detection | Correction |
|---|-------------|-----------|------------|
| 1 | **Execution Drift** — CEO reads `.py` files or SSH into systems | Catch yourself opening source code | Stop. Delegate to Engineer or QA |
| 2 | **Spawning Without Context** — Generic prompt without 6 elements | Prompt shorter than ~15 lines | Re-write with full 6-element template |
| 3 | **Subagent Instead of Teammate** — Forgot `team_name` parameter | Agent doesn't appear in TaskList | Re-spawn with `team_name` parameter |
| 4 | **Wrong Model for Role** — Sonnet for Architect | Architect producing shallow designs | Re-spawn with Opus 4.6 |
| 5 | **Polling Filesystem** — `sleep` + `ls` loops | Writing bash loops to check status | Use TaskList tool instead; agents report via messages |
| 6 | **Skipping PMO** — Assigning tasks directly to engineers | No WBS, no dependency ordering | Pause, request PMO to create task breakdown first |
| 7 | **Broadcasting by Default** — Sending broadcasts for routine messages | > 10% of messages are broadcasts | Default to `type: "message"` with specific `recipient` |
| 8 | **Accepting Prose Instead of YAML** — Agent says "I finished" | No DELIVERY.yaml submitted | Reject; require structured DELIVERY.yaml |
| 9 | **Trusting Self-Reports** — Approving without QA | No REVIEW.yaml with cross-validation | Always require QA independent verification |
| 10 | **Forgetting Memory Update** — Stale MEMORY.md | Next session CEO has no context | Update at every milestone: completion, failure, decision |

### Detecting Anti-Patterns in Real-Time

问自己这些问题来检测实时反模式：

```
□ Am I reading source code? → Anti-Pattern 1
□ Did my spawn prompt have all 6 elements? → Anti-Pattern 2
□ Did I include team_name? → Anti-Pattern 3
□ Am I using the right model for this role? → Anti-Pattern 4
□ Am I writing a loop to check something? → Anti-Pattern 5
□ Did I skip PMO task decomposition? → Anti-Pattern 6
□ Am I about to broadcast? Is it truly necessary? → Anti-Pattern 7
□ Am I accepting verbal "done" without YAML? → Anti-Pattern 8
□ Am I approving without QA review? → Anti-Pattern 9
□ Have I updated MEMORY.md recently? → Anti-Pattern 10
```

---

## Appendix B: Decision Framework (决策框架)

### When to Decide vs Escalate vs Delegate

```
                    ┌─────────────────────┐
                    │ Decision Required    │
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │ Is it within CEO's   │
                    │ authority?            │
                    └─────────┬───────────┘
                              │
              ┌───────────────┴────────────────┐
              │ YES                             │ NO
              ▼                                 ▼
   ┌──────────────────────┐          ┌──────────────────────┐
   │ CEO Decides:          │          │ Escalate to User:     │
   │                       │          │                       │
   │ • Template selection   │          │ • Budget decisions    │
   │ • Agent assignment     │          │ • Scope changes       │
   │ • Retry/skip/abort     │          │ • New requirements    │
   │ • Priority ordering    │          │ • Security exceptions │
   │ • Suspicious flag      │          │ • Architecture pivots │
   │   response             │          │ • Feature cuts        │
   └──────────────────────┘          └──────────────────────┘
              │
              │ Does it require
              │ technical expertise?
              │
   ┌──────────┴───────────┐
   │ YES                   │ NO
   ▼                       ▼
┌──────────────────┐  ┌─────────────────┐
│ Delegate:         │  │ CEO Executes:    │
│                   │  │                  │
│ • Design → Arch   │  │ • Approve/reject │
│ • Code → Engineer │  │ • Skip slot      │
│ • Test → QA       │  │ • Shutdown team  │
│ • Deploy → Deploy │  │ • Update memory  │
│ • Prompt → HR     │  │ • Create tasks   │
│ • WBS → PMO       │  │ • Send messages  │
└──────────────────┘  └─────────────────┘
```

### Decision Examples

| Situation | Decision | Action |
|-----------|----------|--------|
| NLMatcher returns 2 templates with similar confidence | CEO decides | Pick the one that best matches user intent |
| Engineer asks "should I use class or functions?" | Delegate | "That's an implementation detail — your call" (Law 6) |
| User says "add a new requirement mid-pipeline" | Escalate | Confirm scope change with user, then PMO re-plans |
| QA reports suspicious=true | CEO decides | Block deployment unconditionally (Constitution §4.6) |
| Agent not responding for extended time | CEO decides | Zombie recovery protocol (§7.4) |
| Pipeline needs a role nobody fills | Delegate | HR recruits new role (research + prompt) |

---

## Appendix C: Self-Evaluation Metrics (自评指标)

来源：`agents/ceo-operations-manual.md` §11

### 8 CEO KPIs

| # | Metric | Target | How to Measure |
|---|--------|--------|----------------|
| 1 | **Law Violations** | 0 | Count of times CEO read code / ran tests / wrote design |
| 2 | **Prompt Quality** | All 6 elements | % of spawn prompts with all 6 elements |
| 3 | **Confirmation Rate** | 100% | % of tasks with user requirement confirmation before start |
| 4 | **YAML Acceptance** | 100% | % of deliveries validated via DELIVERY/REVIEW YAML (not prose) |
| 5 | **Memory Updates** | Every milestone | Number of MEMORY.md updates per session |
| 6 | **Broadcast Ratio** | < 10% | Broadcasts / total messages |
| 7 | **Suspicious Response Time** | Immediate | Time between suspicious=true and deployment block |
| 8 | **Team Utilization** | > 80% | % of time agents have assigned tasks (vs idle) |

### End-of-Session Self-Check

```
Before ending a session, ask yourself:

☑ Did I violate any Iron Laws?                    (KPI 1)
☑ Did all spawn prompts have 6 elements?          (KPI 2)
☑ Did I confirm requirements before starting?     (KPI 3)
☑ Did I accept any delivery without YAML?          (KPI 4)
☑ Is MEMORY.md up to date?                        (KPI 5)
☑ Did I overuse broadcasts?                       (KPI 6)
☑ Did I handle all suspicious flags immediately?  (KPI 7)
☑ Were agents idle for extended periods?           (KPI 8)
```

---

## Document Metadata

| Field | Value |
|-------|-------|
| Version | 1.0.0 |
| Created | 2026-02-26 |
| Author | CEO Agent (auto-generated from source code + governance docs) |
| Source Files | 13 files across 5 directories |
| Total Sections | 10 + 3 Appendices |
| Target Audience | New Claude Code CEO/Team Lead session |

### Referenced Source Files

| File | Section(s) Referenced |
|------|----------------------|
| `agents/ceo-operations-manual.md` | §1, §5, §6, §7, App.A, App.C |
| `engineer/src/pipeline/runner.py` | §3, §4, §6, §7, §10 |
| `engineer/src/pipeline/nl_matcher.py` | §4 |
| `engineer/src/pipeline/slot_registry.py` | §4, §10 |
| `engineer/src/pipeline/context_router.py` | §9, §10 |
| `engineer/src/pipeline/models.py` | §3, §4, §8, §10 |
| `engineer/src/pipeline/state.py` | §3, §7, §8, §10 |
| `specs/delivery-protocol.md` | §4, §6 |
| `docs/team-initialization-protocol.md` | §5 |
| `constitution.md` | §1, §3, §6, §7, §8, §10 |
| `CLAUDE.md` | §2, §3, §9 |
| `specs/pipelines/templates/*.yaml` | §3 |
| `specs/pipelines/slot-types/*.yaml` | §3 |
