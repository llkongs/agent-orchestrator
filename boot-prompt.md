# Boot Prompt

将以下内容复制粘贴到任意 Claude Code 新对话中，Claude 就能用 pipeline 引擎驱动工作。

把 `<YOUR_PROJECT_PATH>` 替换为你的实际项目路径。

---

## 复制粘贴这一段

```
读取 /home/coder/project/agent-orchestrator/CLAUDE.md 了解 pipeline 引擎。

本项目使用 pipeline 引擎编排多步工作流。CLI 工具用法：

PYTHONPATH=/home/coder/project/agent-orchestrator/engineer/src \
  /home/coder/project/agent-orchestrator/engineer/.venv/bin/python \
  -m pipeline.cli -P <YOUR_PROJECT_PATH> <command>

工作流程：
1. `pipeline templates`       — 查看可用模板
2. `pipeline prepare xxx.yaml` — 创建流水线实例
3. `pipeline next`            — 查看下一步该做什么
4. `pipeline begin <slot_id>` — 开始执行某个槽位
5. （你做实际工作：写代码、审查等）
6. `pipeline complete <slot_id>` — 标记完成
7. 重复 3-6 直到所有槽位完成
8. `pipeline summary`         — 查看最终状态

现在请执行 `pipeline -P <YOUR_PROJECT_PATH> templates` 查看可用模板，然后根据任务选择合适的模板开始。
```

---

## 完整示例

假设你在 `/home/coder/project/my-app` 上开发登录功能：

```
读取 /home/coder/project/agent-orchestrator/CLAUDE.md 了解 pipeline 引擎。

本项目使用 pipeline CLI 编排工作流。执行以下命令初始化：

PYTHONPATH=/home/coder/project/agent-orchestrator/engineer/src \
  /home/coder/project/agent-orchestrator/engineer/.venv/bin/python \
  -m pipeline.cli -P /home/coder/project/my-app prepare standard-feature.yaml -p feature_name=login

然后执行 `pipeline next` 查看第一步该做什么。每完成一步用 `pipeline complete <slot_id>` 标记，然后 `pipeline next` 看下一步。
```

---

## 可用命令一览

| 命令 | 说明 |
|------|------|
| `templates` | 列出所有流水线模板 |
| `match <text>` | 自然语言匹配模板（预览，不执行） |
| `prepare <template> [-p key=val]` | 从模板创建流水线实例 |
| `status` | 显示流水线状态 |
| `next` | 显示待执行的槽位 |
| `begin <slot_id>` | 开始一个槽位 |
| `complete <slot_id>` | 完成一个槽位 |
| `fail <slot_id> <error>` | 标记槽位失败 |
| `skip <slot_id>` | 跳过一个槽位 |
| `summary` | 人类可读的完整摘要 |

## 设置别名（可选）

在 `.bashrc` 或 CLAUDE.md 中添加：

```bash
alias pipeline="PYTHONPATH=/home/coder/project/agent-orchestrator/engineer/src \
  /home/coder/project/agent-orchestrator/engineer/.venv/bin/python -m pipeline.cli"
```

之后直接用 `pipeline -P /path/to/project <command>` 即可。
