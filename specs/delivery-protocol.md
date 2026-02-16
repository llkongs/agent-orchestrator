# Agent Delivery Protocol Specification

> Version: 1.1
> Date: 2026-02-14
> Author: ARCH-001 (Architect Agent)
> Status: Active
> Changelog: v1.1 - Added anti-hallucination mechanisms (Section 8)

---

## 1. Purpose

Agent 交付物必须是**机器可验证的结构化清单**，而非自然语言叙述。
本协议定义两个核心 artifact：

| Artifact | 生产方 | 用途 |
|---|---|---|
| **DELIVERY.yaml** | Producer (Architect / Engineer) | 交付清单，声明文件、接口、测试、质量 |
| **REVIEW.yaml** | QA Agent | 审查结论，逐项验证 DELIVERY.yaml 声明 |

验证工具：`architect/delivery-schema.py` 提供 `validate_delivery()` 和 `validate_review()` 函数。

---

## 2. DELIVERY.yaml Schema

Producer 完成任务后必须在自己的工作目录下创建 `DELIVERY.yaml`。
**无 DELIVERY.yaml = 无交付。**

### 2.1 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `version` | string | Y | 协议版本，当前 `"1.1"` |
| `agent_id` | string | Y | Agent 角色 ID (如 `ENG-001`) |
| `agent_name` | string | Y | Agent 实例名 (如 `engineer`) |
| `task_id` | string | Y | 任务标识 (如 `phase-1-foundation`) |
| `timestamp` | string (ISO 8601) | Y | 交付时间 |
| `status` | enum | Y | `complete` / `partial` / `blocked` |

### 2.2 deliverables (交付文件清单)

列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `path` | string | Y | 相对于项目根的文件路径 |
| `type` | enum | Y | `source` / `test` / `config` / `doc` / `script` / `schema` |
| `description` | string | Y | 一句话说明 |
| `checksum` | string | Y | `sha256:<hex>`，防篡改 |
| `loc` | int | Y | 文件行数 |
| `language` | string | Y | 编程语言或格式 (python / yaml / markdown) |
| `implements` | string | N | 实现了哪个设计文件 |

### 2.3 exports (接口契约)

本次交付暴露给其他 Agent 使用的接口。列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | Y | 导出名称 (类名/函数名) |
| `type` | enum | Y | `dataclass` / `enum` / `abc` / `function` / `interface_impl` / `constant` |
| `module` | string | Y | Python 模块路径 |
| `description` | string | Y | 一句话说明 |

### 2.4 dependencies (依赖声明)

本次交付依赖了哪些其他 Agent 的产出。列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent` | string | Y | 来源 Agent ID |
| `file` | string | Y | 依赖的文件路径 |
| `usage` | string | Y | 用了什么 |

### 2.5 test_results (测试结果)

**必须是实际运行数据，不是自述。**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `runner` | string | Y | 测试框架 (pytest) |
| `command` | string | Y | 实际运行的完整命令 |
| `total` | int | Y | 测试总数 |
| `passed` | int | Y | 通过数 |
| `failed` | int | Y | 失败数 |
| `skipped` | int | Y | 跳过数 |
| `errors` | int | Y | 错误数 |
| `coverage_pct` | float | Y | 总体覆盖率百分比 |
| `coverage_by_module` | list | N | 逐模块覆盖率 |

`coverage_by_module` 每项：

| 字段 | 类型 | 必填 |
|---|---|---|
| `module` | string | Y |
| `stmts` | int | Y |
| `coverage_pct` | float | Y |

### 2.6 quality_checks (质量自检)

Agent 运行的静态检查。列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `check` | string | Y | 检查名称 |
| `command` | string | N | 运行的命令 |
| `result` | enum | Y | `pass` / `fail` / `warn` |
| `details` | string | Y | 结果详情 |

### 2.7 known_issues (已知问题)

诚实声明已知但未解决的问题。列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | Y | 问题编号 (KI-NNN) |
| `severity` | enum | Y | `P0` / `P1` / `P2` / `P3` (与 REVIEW.yaml issues 统一) |
| `description` | string | Y | 问题描述 |
| `planned_fix` | string | N | 计划修复时间 |

### 2.8 verification_steps (验证步骤记录) **[v1.1 新增 - 防幻觉]**

**核心原则：不只看最终结果，必须记录每个关键验证步骤的独立状态。**

类似 CI/CD pipeline 的 step-by-step 记录。每个步骤有独立的 status_code，任何一步 failure 则整体 status 不能为 `complete`。

列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `step` | string | Y | 步骤标识 (如 `pytest`, `ruff`, `mypy`, `checksum_verify`) |
| `command` | string | Y | 实际运行的完整命令 |
| `status` | enum | Y | **严格枚举**: `success` / `failure` / `skipped` |
| `stdout_hash` | string | Y | `sha256:<hex>` — 命令实际 stdout 的 hash，可溯源验证 |
| `metrics` | mapping | N | 步骤产出的结构化数据 (见下方) |
| `duration_seconds` | float | N | 步骤执行耗时（秒） |

**验证规则 (由 `validate_delivery()` 强制检查)：**

1. `verification_steps` 为必填字段，至少包含 1 个步骤
2. 每个步骤的 `status` 只能是 `success` / `failure` / `skipped`，不能是自然语言
3. 如果任何步骤 `status == "failure"`，则顶层 `status` 不能为 `complete`
4. `stdout_hash` 格式必须为 `sha256:<64 hex chars>`
5. 当 `test_results` 存在时，必须存在一个 `step == "pytest"` 的步骤，且其 `metrics.tests_passed` 必须等于 `test_results.passed`

**metrics 子字段 (按 step 类型)：**

| step 类型 | metrics 字段 | 类型 | 说明 |
|---|---|---|---|
| `pytest` | `tests_passed` | int | 通过测试数 |
| `pytest` | `tests_failed` | int | 失败测试数 |
| `pytest` | `coverage_percent` | float | 覆盖率百分比 |
| `ruff` | `errors` | int | lint 错误数 |
| `ruff` | `warnings` | int | lint 警告数 |
| `mypy` | `errors` | int | 类型检查错误数 |
| `checksum_verify` | `files_checked` | int | 校验文件数 |
| `checksum_verify` | `files_matched` | int | 匹配文件数 |

**示例：**

```yaml
verification_steps:
  - step: "pytest"
    command: "cd engineer && .venv/bin/python -m pytest tests/ -v --tb=short"
    status: "success"
    stdout_hash: "sha256:a1b2c3d4e5f6..."
    metrics:
      tests_passed: 227
      tests_failed: 0
      coverage_percent: 93.8
    duration_seconds: 2.31

  - step: "ruff"
    command: "ruff check src/"
    status: "success"
    stdout_hash: "sha256:f6e5d4c3b2a1..."
    metrics:
      errors: 0
      warnings: 0
    duration_seconds: 0.45

  - step: "mypy"
    command: "mypy src/ --strict"
    status: "success"
    stdout_hash: "sha256:1a2b3c4d5e6f..."
    metrics:
      errors: 0
    duration_seconds: 3.12
```

### 2.9 golden_dataset (黄金测试集) **[v1.1 新增 - 防幻觉]**

预先定义的输入-输出对，用于防止 agent 行为漂移。每次交付必须通过 golden dataset 测试。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | Y | 测试集名称 |
| `description` | string | Y | 测试集用途 |
| `test_count` | int | Y | 测试用例数 |
| `passed` | int | Y | 通过数 |
| `failed` | int | Y | 失败数 |
| `status` | enum | Y | `success` (全通过) / `failure` (有失败) |
| `result_hash` | string | Y | `sha256:<hex>` — 测试输出的 hash |

**验证规则：**

1. `golden_dataset` 为可选字段，但如果存在则必须全部通过 (`status == "success"`)
2. `passed + failed` 必须等于 `test_count`
3. 如果 `failed > 0` 则 `status` 必须为 `failure`
4. 如果 `status == "failure"`，则顶层 `status` 不能为 `complete`

---

## 3. REVIEW.yaml Schema

QA Agent 审查后在自己的工作目录下创建 `REVIEW.yaml`。
**无 REVIEW.yaml = 无审查结论。**

### 3.1 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `version` | string | Y | 协议版本 `"1.0"` |
| `agent_id` | string | Y | QA Agent ID |
| `agent_name` | string | Y | QA Agent 名称 |
| `timestamp` | string (ISO 8601) | Y | 审查时间 |

### 3.2 target (审查目标)

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent` | string | Y | 被审查的 Agent ID |
| `delivery` | string | Y | DELIVERY.yaml 路径 |
| `task_id` | string | Y | 任务标识 |

### 3.3 verdict (审查结论)

枚举值，**最重要的字段**：

| 值 | 含义 | 后续动作 |
|---|---|---|
| `pass` | 全部通过 | 可进入下一阶段 |
| `conditional_pass` | 有非阻塞问题 | 可继续，但需后续修复 |
| `fail` | 有阻塞问题 | 必须修复后重新交付 |

**Verdict 决策表 (Decision Table)**

verdict 不由 QA 主观判断，而是由以下规则机器推导：

| 条件 | verdict | 说明 |
|---|---|---|
| 存在任何 P0 issue | `fail` | P0 = 阻塞，无条件 fail |
| 存在任何 P1 issue 且 `fix_required: true` | `fail` | P1 阻塞必须修复 |
| 存在 P1 issue 但全部 `fix_required: false` | `conditional_pass` | P1 非阻塞，可继续但需跟进 |
| 最高 severity 为 P2 | `conditional_pass` | 有改进空间，非阻塞 |
| 最高 severity 为 P3 或无 issue | `pass` | 通过 |

`validate_review()` 会强制检查 verdict 与 issues 的一致性。不符合决策表的 REVIEW.yaml 验证失败。

### 3.4 delivery_checksum

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `delivery_checksum` | string | Y | 被审查的 DELIVERY.yaml 文件的 `sha256:<hex>` |

QA 在开始审查时记录 DELIVERY.yaml 的 checksum。如果 Producer 在审查期间修改了 DELIVERY.yaml，该 checksum 会失配，review 自动视为过期。

### 3.5 issues (问题清单)

列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | Y | 问题编号 (P{0-3}-NNN) |
| `severity` | enum | Y | `P0` (阻塞) / `P1` (严重) / `P2` (一般) / `P3` (建议) |
| `category` | enum | Y | `security` / `correctness` / `performance` / `style` / `testing` |
| `file` | string | Y | 相关文件路径 |
| `line` | int/null | N | 具体行号，未知则 null |
| `description` | string | Y | 问题描述 |
| `expected` | string | Y | 期望行为 |
| `actual` | string | Y | 实际行为 |
| `fix_required` | bool | Y | true = 阻塞必须修复 |
| `fix_deadline` | string/null | N | 修复期限 |

### 3.6 delivery_verification (交付物验证)

逐项核实 DELIVERY.yaml 的声明。列表，每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `claim` | string | Y | DELIVERY.yaml 中的声明 |
| `verified` | bool | Y | 是否验证通过 |
| `method` | string | Y | 验证方法 |
| `actual_result` | string | Y | 实际结果 |

### 3.7 additional_tests (补充测试)

QA 编写的额外测试。列表，每项：

| 字段 | 类型 | 必填 |
|---|---|---|
| `path` | string | Y |
| `test_count` | int | Y |
| `all_passed` | bool | Y |
| `description` | string | N |

### 3.8 independent_metrics (独立复现指标) **[v1.1 新增 - 防幻觉]**

QA 必须独立运行测试/检查，记录自己的 metrics，与 Producer 声称的做对比。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `test_results` | mapping | Y | QA 独立运行 pytest 的结果 |
| `quality_checks` | list | Y | QA 独立运行 ruff/mypy 等的结果 |

`test_results` 子字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `command` | string | Y | QA 实际运行的命令 |
| `total` | int | Y | 测试总数 |
| `passed` | int | Y | 通过数 |
| `failed` | int | Y | 失败数 |
| `coverage_pct` | float | Y | 覆盖率百分比 |
| `stdout_hash` | string | Y | `sha256:<hex>` — 实际输出的 hash |

`quality_checks` 每项：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `check` | string | Y | 检查名称 |
| `command` | string | Y | QA 运行的命令 |
| `result` | enum | Y | `pass` / `fail` / `warn` |
| `details` | string | Y | 结果详情 |
| `stdout_hash` | string | Y | `sha256:<hex>` — 实际输出的 hash |

### 3.9 cross_validation (交叉验证) **[v1.1 新增 - 防幻觉]**

自动对比 Producer (DELIVERY.yaml) 与 QA (REVIEW.yaml) 各自独立运行的 metrics。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `test_count_match` | bool | Y | Producer 声称的 test total 是否与 QA 复现一致 |
| `test_pass_match` | bool | Y | Producer 声称的 passed 是否与 QA 复现一致 |
| `coverage_delta` | float | Y | 覆盖率差值 (Producer - QA)，绝对值 |
| `coverage_threshold` | float | Y | 可接受的覆盖率偏差阈值 (默认 2.0%) |
| `suspicious` | bool | Y | 如果任何指标不匹配或 coverage_delta > threshold，标记为 true |
| `details` | string | Y | 交叉验证详情说明 |

**验证规则 (由 `validate_review()` 强制检查)：**

1. `cross_validation` 为必填字段
2. 如果 `test_count_match == false` 或 `test_pass_match == false`，则 `suspicious` 必须为 `true`
3. 如果 `coverage_delta > coverage_threshold`，则 `suspicious` 必须为 `true`
4. 如果 `suspicious == true`，verdict 不能为 `pass`（至少为 `conditional_pass`）

### 3.10 summary (总结) *(原 3.8)*

| 字段 | 类型 | 必填 |
|---|---|---|
| `total_issues` | int | Y |
| `p0_count` | int | Y |
| `p1_count` | int | Y |
| `p2_count` | int | Y |
| `p3_count` | int | Y |
| `blocking` | bool | Y |
| `recommendation` | string | Y |

---

## 4. Handshake Flow (握手流程)

```
Producer                          Team Lead                         QA
   |                                 |                              |
   |  1. Complete work               |                              |
   |  2. Create DELIVERY.yaml        |                              |
   |  3. Notify team-lead            |                              |
   | ==============================> |                              |
   |                                 |  4. validate_delivery()      |
   |                                 |     - Schema validation      |
   |                                 |     - File existence check   |
   |                                 |     - Checksum spot check    |
   |                                 |                              |
   |        [validation fail]        |                              |
   | <============================== |                              |
   |  Reject: fix DELIVERY.yaml      |                              |
   |                                 |                              |
   |        [validation pass]        |                              |
   |                                 |  5. Assign QA review         |
   |                                 | ============================>|
   |                                 |                              |
   |                                 |                 6. Read DELIVERY.yaml
   |                                 |                 7. Verify each claim
   |                                 |                 8. Run tests independently
   |                                 |                 9. Write additional tests
   |                                 |                10. Check all checksums
   |                                 |                11. Create REVIEW.yaml
   |                                 |                12. validate_review()
   |                                 | <============================|
   |                                 |                              |
   |                                 | 13. Read REVIEW.yaml         |
   |                                 | 14. Check verdict            |
   |                                 |                              |
   |     [verdict = fail]            |                              |
   | <============================== |                              |
   |  Send fix list from issues[]    |                              |
   |  15. Fix issues                 |                              |
   |  16. Update DELIVERY.yaml       |                              |
   | ==============================> |                              |
   |                                 | 17. Re-assign QA             |
   |                                 | ============================>|
   |                                 |                18. Verify fixes|
   |                                 | <============================|
   |                                 |                              |
   |     [verdict = pass]            |                              |
   |                                 | 19. Mark task complete        |
   |                                 | 20. Start next phase          |
```

### 4.1 各步骤要求

| 步骤 | 执行者 | 机器验证 | 说明 |
|---|---|---|---|
| 2 | Producer | `validate_delivery()` | 必须通过 schema 验证后才能通知 |
| 4 | Team Lead | `validate_delivery()` | 二次验证 + 文件存在性检查 |
| 10 | QA | `sha256sum` | 重新计算 checksum 并比对 DELIVERY.yaml |
| 12 | QA | `validate_review()` | 必须通过 schema 验证后才能提交 |

### 4.2 File-Freeze 规则

Producer 创建 DELIVERY.yaml 后，进入 **file-freeze** 状态：

1. DELIVERY.yaml 中列出的所有 `deliverables[].path` 文件**禁止修改**，直到审查周期结束
2. QA 在审查开始时记录 DELIVERY.yaml 自身的 checksum 到 `REVIEW.yaml.delivery_checksum`
3. QA 验证每个 deliverable 的 checksum 是否与 DELIVERY.yaml 声明一致
4. 如果 Producer 必须修改文件（如紧急 bug），必须：
   - 撤回当前交付（通知 team-lead）
   - 修改文件
   - 重新生成 DELIVERY.yaml（新 timestamp、新 checksum）
   - 重新提交

**违反 file-freeze = 交付无效，必须重新提交。**

### 4.3 超时规则

| 环节 | 超时 | 超时动作 |
|---|---|---|
| QA 审查 | 交付后 4 小时内完成 | Team Lead 催促或重新分配 |
| Producer 修复 | 收到修复清单后 4 小时内 | Team Lead 升级 |
| 单轮修复循环 | 最多 3 轮 | 超过 3 轮 Team Lead 介入协调 |

---

## 5. Directory Isolation & Permission Matrix

```
crypto-trading-system/
├── docs/                ← Team Lead 管理
├── agents/              ← Team Lead 管理
├── architect/           ← Architect 工作目录
│   ├── DELIVERY.yaml
│   └── ...
├── engineer/            ← Engineer 工作目录
│   ├── DELIVERY.yaml
│   └── ...
└── qa/                  ← QA 工作目录
    ├── REVIEW.yaml
    └── ...
```

### 5.1 Read/Write Permission Matrix

| Agent | architect/ | engineer/ | qa/ | docs/ | agents/ |
|---|---|---|---|---|---|
| **Architect** | **RW** | R | R | R | R |
| **Engineer** | R | **RW** | R | R | R |
| **QA** | R | R | **RW** | R | R |
| **Team Lead** | R | R | R | **RW** | **RW** |

**原则**：每个 Agent 只能写入自己的目录。读取其他 Agent 的产出是被鼓励的（用于对齐接口和验证实现），但不得修改。

### 5.2 Checksum 防篡改

```bash
# 生成
sha256sum path/to/file.py
# 输出: abc123def456...  path/to/file.py

# 在 DELIVERY.yaml 中记录为:
# checksum: "sha256:abc123def456..."

# QA 验证: 重新计算并比对
```

---

## 6. Violation Handling

| 违规类型 | 严重度 | 处理 |
|---|---|---|
| 无 DELIVERY.yaml 声称完成 | High | 交付不被承认，退回 |
| DELIVERY.yaml schema 验证失败 | High | 退回修复 DELIVERY.yaml |
| 声明与实际不符 (checksum/test) | High | QA 标记 fail，退回修复 |
| 写入非自己的工作目录 | High | 文件删除 + 警告 |
| 跳过 QA 审查进入下阶段 | High | 阻塞，必须补审 |
| checksum 不匹配 | High | 交付无效，重新生成 |
| REVIEW.yaml schema 验证失败 | Medium | QA 修复后重新提交 |
| 已知问题未在 known_issues 声明 | Medium | QA 降低信任评级 |
| file-freeze 期间修改 deliverable | High | 交付无效，必须重新提交 |
| REVIEW.yaml delivery_checksum 失配 | High | review 过期，必须重新审查 |
| 超时未响应 | Medium | Team Lead 升级或重新分配 |

---

## 7. Quick Reference

### Producer Checklist (交付时)

1. 所有文件写入自己的工作目录
2. 运行测试，记录 stdout 并计算 stdout_hash
3. 运行 ruff / mypy，记录 stdout 并计算 stdout_hash
4. 计算每个文件的 sha256 checksum
5. 填写 `verification_steps` — 每个步骤独立记录 status + stdout_hash + metrics
6. 运行 golden dataset 测试（如果存在），记录到 `golden_dataset`
7. 填写 DELIVERY.yaml 所有必填字段
8. 确认一致性：`verification_steps` 中无 failure 且 metrics 与 `test_results` 一致
9. 运行 `validate_delivery("DELIVERY.yaml")` 确认通过
10. 通知 team-lead

### QA Checklist (审查时)

1. 读取 DELIVERY.yaml
2. 计算 DELIVERY.yaml 的 checksum，记录到 `delivery_checksum`
3. 验证 schema: `validate_delivery()`
4. 验证每个文件存在且 checksum 匹配 (file-freeze 检测)
5. 独立运行测试，记录到 `independent_metrics`
6. 对比 Producer metrics 与 QA metrics，填写 `cross_validation`
7. 逐项验证 exports 中声明的接口
8. 编写补充测试覆盖边界场景
9. 记录所有问题到 issues[]
10. 根据 verdict 决策表确定 verdict
11. 填写 REVIEW.yaml（含 `delivery_checksum`、`independent_metrics`、`cross_validation`）
12. 运行 `validate_review("REVIEW.yaml")` 确认通过
13. 通知 team-lead

---

## 8. Anti-Hallucination Mechanisms (防幻觉机制) **[v1.1 新增]**

### 8.1 问题背景

LLM Agent 存在以下已知风险模式：

| 风险 | 表现 | 后果 |
|---|---|---|
| **虚报成功 (False Success)** | Agent 用自然语言说 "all tests passed" 但实际未运行 | 有缺陷的代码进入下一阶段 |
| **行为漂移 (Behavior Drift)** | Agent 随时间逐渐偏离预期行为，输出格式或质量下降 | 渐进式质量退化，难以察觉 |
| **自证循环 (Self-Validation Loop)** | Agent 自己写测试、自己运行、自己报告结果 | 无外部验证的闭环，无法检测系统性错误 |
| **模糊状态 (Ambiguous Status)** | Agent 用 "基本完成"、"大部分通过" 等模糊表述 | 无法机器判定，人类需要额外审查 |
| **遗漏失败 (Omitted Failures)** | Agent 不报告已知的失败或跳过的测试 | 失败信号被隐藏 |

### 8.2 显式 Status Code 机制

**原则：所有状态必须使用严格枚举值，禁止自然语言描述状态。**

| 上下文 | 允许的枚举值 | 禁止的表述 |
|---|---|---|
| DELIVERY.yaml `status` | `complete` / `partial` / `blocked` | "基本完成"、"差不多了" |
| `quality_checks[].result` | `pass` / `fail` / `warn` | "没有大问题"、"还行" |
| `verification_steps[].status` | `success` / `failure` / `skipped` | "大部分通过"、"几乎成功" |
| `golden_dataset.status` | `success` / `failure` | "接近通过" |
| REVIEW.yaml `verdict` | `pass` / `conditional_pass` / `fail` | "建议通过"、"勉强及格" |
| `known_issues[].severity` | `P0` / `P1` / `P2` / `P3` | "严重"、"一般" |

**验证工具 `delivery-schema.py` 对所有枚举字段做硬校验，非法值直接 FAIL。**

### 8.3 中间步骤记录 (Atomic Validation)

**原则：不只看最终结果，要求记录关键中间步骤，每个步骤有独立 status code。**

```
传统方式 (v1.0):                    防幻觉方式 (v1.1):
┌─────────────────┐                ┌─────────────────────────────────┐
│ test_results:   │                │ verification_steps:             │
│   passed: 227   │  (单一声明)    │   - step: pytest                │
│   failed: 0     │                │     status: success             │
│                 │                │     stdout_hash: sha256:abc...  │
│                 │                │     metrics:                    │
│                 │                │       tests_passed: 227         │
│                 │                │   - step: ruff                  │
│                 │                │     status: success             │
│                 │                │     stdout_hash: sha256:def...  │
│                 │                │   - step: mypy                  │
│                 │                │     status: success             │
│                 │                │     stdout_hash: sha256:123...  │
└─────────────────┘                └─────────────────────────────────┘
```

**关键约束：**

1. **步骤独立性**：每个步骤有自己的 `status`，不受其他步骤影响
2. **失败传播**：任何步骤 `failure` → 顶层 `status` 不能为 `complete`
3. **可溯源性**：`stdout_hash` 允许事后验证 Agent 是否真正运行了命令
4. **一致性检查**：`verification_steps` 中 pytest 步骤的 `metrics.tests_passed` 必须与 `test_results.passed` 一致

### 8.4 Golden Dataset 回归测试

**原则：预定义的输入-输出对，每次交付必须通过，防止行为漂移。**

Golden dataset 的用途：
- 确保核心模型的创建/序列化行为不变
- 确保配置加载的确定性输出不变
- 确保异常层次结构不变

**使用流程：**

1. Architect 在架构设计时定义 golden dataset（输入-输出对）
2. Engineer 实现后运行 golden dataset 测试，记录到 `DELIVERY.yaml.golden_dataset`
3. QA 独立运行 golden dataset，对比结果
4. 如果 golden dataset 测试失败，交付不能标记为 `complete`

### 8.5 显式失败信号

**原则：验证失败时默认行为是承认失败，不是编造成功。**

**Fail-Open 策略（安全第一）：**

| 场景 | 默认行为 | 禁止行为 |
|---|---|---|
| pytest 运行出错 | `verification_steps[].status = "failure"` | 跳过不报告 |
| 无法运行 mypy | `verification_steps[].status = "failure"` | 省略该步骤 |
| checksum 计算失败 | 整体 status = `blocked` | 填写假 checksum |
| 测试数量与声明不符 | 在 known_issues 中声明 | 修改声明数字 |
| 覆盖率低于目标 | `quality_checks[].result = "warn"` | 夸大覆盖率 |

**验证器强制规则：**

- `verification_steps` 中有任何 `failure` → `status != "complete"` (否则 FAIL)
- `golden_dataset` 中有 `failure` → `status != "complete"` (否则 FAIL)
- `test_results.failed > 0` → 必须在 `known_issues` 中有对应条目解释原因

### 8.6 交叉验证增强

**原则：Producer 声称的 metrics 必须能被 QA 独立复现。**

```
Producer (DELIVERY.yaml)          QA (REVIEW.yaml)
┌────────────────────┐            ┌────────────────────────────┐
│ test_results:      │            │ independent_metrics:       │
│   passed: 227      │ ── 对比 ──>│   test_results:            │
│   coverage: 93.8   │            │     passed: 227            │
│                    │            │     coverage: 93.8         │
│ verification_steps:│            │                            │
│   - step: pytest   │            │ cross_validation:          │
│     status: success│            │   test_count_match: true   │
│     stdout_hash:   │            │   test_pass_match: true    │
│       sha256:abc...│            │   coverage_delta: 0.0      │
└────────────────────┘            │   suspicious: false        │
                                  └────────────────────────────┘
```

**偏差阈值和处理：**

| 指标 | 阈值 | 超出时处理 |
|---|---|---|
| test total 不匹配 | 0 (必须精确匹配) | `suspicious = true`, verdict 不能为 `pass` |
| test passed 不匹配 | 0 (必须精确匹配) | `suspicious = true`, verdict 不能为 `pass` |
| coverage 偏差 | 2.0% (默认) | `suspicious = true`, verdict 不能为 `pass` |

**`validate_review()` 强制检查：**

1. `cross_validation` 字段必须存在
2. `suspicious` 必须与 match/delta 状态一致
3. `suspicious == true` 时 verdict 不能为 `pass`

### 8.7 验证器增强总结

`delivery-schema.py` v1.1 新增的验证逻辑：

| 函数 | 新增检查 | 错误信息 |
|---|---|---|
| `validate_delivery()` | `verification_steps` 必须存在且非空 | "Missing or empty required field: verification_steps" |
| `validate_delivery()` | 每个 step 的 `status` 必须是 `success`/`failure`/`skipped` | "Invalid value for verification_steps[N].status" |
| `validate_delivery()` | `stdout_hash` 格式校验 | "verification_steps[N]: invalid stdout_hash format" |
| `validate_delivery()` | failure 步骤 vs 顶层 status 一致性 | "verification_steps contains failure but status is 'complete'" |
| `validate_delivery()` | pytest 步骤 metrics vs test_results 一致性 | "verification_steps pytest metrics mismatch with test_results" |
| `validate_delivery()` | `golden_dataset` (如果存在) 的 status/count 一致性 | "golden_dataset: passed + failed != test_count" |
| `validate_review()` | `independent_metrics` 必须存在 | "Missing required field: independent_metrics" |
| `validate_review()` | `cross_validation` 必须存在 | "Missing required field: cross_validation" |
| `validate_review()` | `suspicious` 与 match/delta 一致性 | "cross_validation: suspicious should be true" |
| `validate_review()` | `suspicious == true` 时 verdict 不能为 `pass` | "cross_validation suspicious but verdict is 'pass'" |
