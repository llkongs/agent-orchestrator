# Architecture Evaluation: Pipeline Bootstrap Problem

> Author: ARCH-001
> Date: 2026-02-17
> Status: EVALUATION COMPLETE
> Request: PMO-001 (via team-lead, from user)
> Verdict: **Option 1 (Built-in HR + PMO) with defaults/ integration**

---

## 1. Problem Statement

When a user first uses the pipeline system, it has no agent prompts, no running agents, and no pipeline history. The system needs a way to go from zero to operational. The question is: what comes pre-installed, and how does the system bootstrap itself?

---

## 2. Option Analysis

### Option 1: Built-in HR + PMO

```
System ships with:
  defaults/agents/00-hr-agent.md      (HR prompt)
  defaults/agents/06-pmo-agent.md     (PMO prompt)

First-use flow:
  1. User starts pipeline engine
  2. Engine copies defaults to agents/ if empty
  3. User says "I want to build X"
  4. Pipeline engine spawns HR to recruit needed roles
  5. HR produces .md prompts for Architect, Engineer, QA, etc.
  6. PMO manages gates for the resulting pipeline
  7. System is now fully operational
```

**Pros**:
- Clean separation of concerns: HR recruits, PMO governs
- HR and PMO are "meta-roles" -- they create and manage other roles, not domain work
- Aligns with existing architecture: HR and PMO are already the two roles that are role-agnostic
- Prompts are configurable YAML/Markdown files, not hardcoded
- User can customize the built-in HR/PMO prompts before first use

**Cons**:
- Two files to maintain as "system defaults"
- If HR prompt is poor quality, all downstream agents suffer
- User must understand the HR->recruit flow to get started

### Option 2: Single Bootstrap Role

```
System ships with:
  defaults/agents/bootstrap-agent.md  (bootstrap prompt)

First-use flow:
  1. User starts pipeline engine
  2. Engine spawns bootstrap agent
  3. Bootstrap agent creates HR .md and PMO .md
  4. Bootstrap agent exits
  5. System continues with HR + PMO
  6. HR recruits remaining roles
```

**Pros**:
- Minimal built-in content (one file)
- Bootstrap agent can be tailored to the specific project domain

**Cons**:
- **Violates single responsibility**: one agent writes prompts for two fundamentally different roles
- **Quality risk**: a generalist bootstrap agent will produce worse HR/PMO prompts than carefully crafted defaults
- **Extra step for no value**: the bootstrap agent's only job is to create HR + PMO prompts, then it's discarded. We can just ship those prompts directly.
- **Capability boundary is unclear**: "create agent prompts" is HR's core competency. A bootstrap agent doing this duplicates HR.
- **Recursive problem**: who validates the bootstrap agent's prompt quality? At least with Option 1, the HR prompt is a known, version-controlled artifact that can be reviewed.

### Decision Matrix

| Criterion | Weight | Option 1 (HR+PMO) | Option 2 (Bootstrap) |
|-----------|--------|-------------------|---------------------|
| Simplicity | 25% | 5/5 | 3/5 |
| Quality of first agents | 25% | 5/5 | 3/5 |
| Single responsibility | 20% | 5/5 | 2/5 |
| Minimal built-in content | 15% | 4/5 | 5/5 |
| Extensibility | 15% | 5/5 | 3/5 |
| **Weighted Total** | | **4.85** | **3.10** |

**Winner: Option 1** by a wide margin. The "extra indirection" of Option 2 adds complexity without value.

---

## 3. Answers to PMO's Questions

### Q1: Which option is architecturally more sound?

**Option 1 (Built-in HR + PMO)**. The reasoning:

1. **HR and PMO are the system's "firmware"** -- they are the two roles that exist outside the domain problem (trading, gaming, research, etc.). Every other role is domain-specific and should be recruited by HR after understanding the project's needs. HR and PMO are universal.

2. **The bootstrap problem maps exactly to compiler bootstrapping**: a compiler needs a compiler to compile itself. The solution is to ship a "stage 0" binary. Our "stage 0" is HR + PMO. They are the minimal viable team that can grow the team.

3. **Option 2 is architecturally a "meta-bootstrap" that adds a needless layer**. It's equivalent to saying: "we need a compiler to build our compiler that builds our compiler." Ship the first compiler directly.

### Q2: Relationship between built-in roles and SlotType system

Built-in roles do **NOT** need special SlotTypes. Here's why:

```
SlotType System (Layer 3):     Defines WHAT a slot needs
Agent Prompts (Layer 2):       Defines WHO fills a slot
Pipeline Engine (Layer 1):     Orchestrates execution

Built-in agents (HR, PMO) operate at Layer 2.
They are agents that can fill standard SlotTypes:
  - HR fills the "hr_recruit" step type (already in schema)
  - PMO fills the "compliance_audit" slot type (from WP-5.2)
  - PMO also fills gate enforcement roles (built into runner)
```

The built-in agents are not "special" -- they are regular agents whose prompts happen to be shipped with the system. They use standard SlotTypes and standard pipeline steps. The only difference is their prompts come from `defaults/` instead of being produced by HR.

However, their capabilities should be declared in YAML front-matter (per the slot system design), so the engine can verify compatibility:

```yaml
# In defaults/agents/00-hr-agent.md front-matter:
---
agent_id: "HR-001"
version: "1.0"
is_bootstrap: true               # Flag for engine: this agent is pre-installed
capabilities:
  - "web_search"
  - "structured_report_writing"
  - "stakeholder_communication"
compatible_slot_types:
  - "hr_recruit"
---
```

### Q3: Integration with PipelineRunner

**Semi-automatic bootstrap, triggered on first `prepare()` call**:

```python
class PipelineRunner:
    def prepare(self, yaml_path, params):
        # Auto-bootstrap on first use
        if not self._is_bootstrapped():
            self._bootstrap()
        # ... existing prepare logic ...

    def _is_bootstrapped(self) -> bool:
        """Check if minimum viable agents exist."""
        agents_dir = self._project_root / "agents"
        return (
            (agents_dir / "00-hr-agent.md").exists()
            and (agents_dir / "06-pmo-agent.md").exists()
        )

    def _bootstrap(self) -> None:
        """Copy default agents and slot types to project."""
        # 1. Copy defaults/agents/* -> agents/ (if not exist)
        # 2. Copy defaults/slot_types/* -> slot_types/ (if not exist)
        # 3. Create directory structure (active/, archive/, audit/)
        # This is the same bootstrap_pipeline_engine() from WP-5.4
        bootstrap_pipeline_engine(str(self._project_root))
```

This integrates naturally with the WP-5.4 bootstrap design. The flow is:

```
User: runner.prepare("templates/standard-feature.yaml", params)
  |
  v
Runner: _is_bootstrapped()? NO
  |
  v
Runner: _bootstrap()
  -> Copy defaults/agents/00-hr-agent.md -> agents/
  -> Copy defaults/agents/06-pmo-agent.md -> agents/
  -> Copy defaults/slot-types/*.yaml -> slot-types/
  -> Create directories
  |
  v
Runner: Proceed with normal prepare() flow
  -> If pipeline needs roles that don't exist yet:
     -> Pipeline includes hr_recruit step
     -> HR produces the needed agent .md files
```

### Q4: Where to put built-in prompt files

**`defaults/agents/` directory, copied to `agents/` on first use.**

```
specs/pipelines/
├── defaults/
│   ├── agents/                     # Built-in agent prompts (source of truth)
│   │   ├── 00-hr-agent.md          # HR prompt (version-controlled default)
│   │   └── 06-pmo-agent.md         # PMO prompt (version-controlled default)
│   ├── slot-types/                 # Default slot types (from WP-5.4)
│   ├── config.yaml                 # Engine config (from WP-5.4)
│   └── capabilities.yaml           # Capability registry (from WP-5.4)
│
agents/                             # Active agents (project-level, may be customized)
├── 00-hr-agent.md                  # Copied from defaults on bootstrap
├── 06-pmo-agent.md                 # Copied from defaults on bootstrap
├── 01-architect-agent.md           # Produced by HR
├── 02-engineer-agent.md            # Produced by HR
└── ...                             # Other HR-recruited agents
```

**Rationale**:
- `defaults/agents/` is the **system-level** source of truth (version-controlled, never modified by agents)
- `agents/` is the **project-level** working directory (may be customized by user or HR)
- On bootstrap, files are COPIED (not symlinked) so the user can freely modify them
- If user deletes or corrupts `agents/00-hr-agent.md`, re-running bootstrap restores it from defaults
- This follows the same pattern as WP-5.4's slot type handling

---

## 4. Complete Bootstrap Sequence

```
FIRST USE (user has just cloned the project or started fresh):

1. User: "I want to build a crypto trading system"
   |
   v
2. PipelineRunner.prepare() detects no agents/ -> runs bootstrap
   - Copies defaults/agents/00-hr-agent.md -> agents/
   - Copies defaults/agents/06-pmo-agent.md -> agents/
   - Copies defaults/slot-types/*.yaml -> slot-types/
   - Creates active/, archive/, audit/ directories
   |
   v
3. User selects pipeline template (e.g., "standard-feature")
   |
   v
4. Runner validates pipeline: ARCH-001 prompt missing!
   - Pipeline has step with role: ARCH-001
   - agents/01-architect-agent.md does not exist
   |
   v
5. Runner automatically prepends an "hr-recruit" step:
   - HR-001 reads the pipeline's slot requirements
   - HR-001 researches and produces the needed agent .md files
   - Pipeline continues once all required agents exist
   |
   v
6. Pipeline executes normally with recruited agents

SUBSEQUENT USES:
- agents/ already populated -> bootstrap skipped
- HR only recruited for new roles not yet in agents/
```

---

## 5. Relationship to Compliance Auditor

The compliance auditor (WP-5.2) fits naturally into this bootstrap:

1. **Auditor SlotType** is shipped in `defaults/slot-types/auditor.yaml` (already done)
2. **PMO fills the auditor slot** as interim (no separate COMP-001 prompt needed for bootstrap)
3. When hiring criteria are met (Section 6 of the compliance auditor eval), HR produces `agents/XX-compliance-auditor-agent.md`
4. The auditor SlotType's capability matching validates that the new agent has the required capabilities
5. PMO stops filling the auditor slot; COMP-001 takes over

This is exactly the "plug-in" model the slot system was designed for: the slot (auditor) exists from day one; the plug (agent) is swapped when ready.

---

## 6. Implementation Impact

| Component | Change | LOC |
|-----------|--------|-----|
| `defaults/agents/00-hr-agent.md` | Copy existing agent prompt | 0 (copy) |
| `defaults/agents/06-pmo-agent.md` | Copy existing agent prompt | 0 (copy) |
| `pipeline/bootstrap.py` | Add agent copying logic | ~15 |
| `pipeline/runner.py` | Add `_is_bootstrapped()` check in `prepare()` | ~10 |
| **Total new code** | | **~25 LOC** |

The WP-5.4 bootstrap design already handles slot types, config, and directories. This evaluation adds agent prompt copying to the same function.

---

## 7. Summary

| Question | Answer |
|----------|--------|
| **Which option?** | Option 1: Built-in HR + PMO |
| **Why not Option 2?** | Violates SRP, adds indirection without value, quality risk |
| **Special SlotTypes needed?** | No. HR uses `hr_recruit` step type, PMO uses standard gate enforcement + `compliance_audit` slot |
| **Integration method** | Semi-automatic: `prepare()` checks `_is_bootstrapped()`, copies defaults if needed |
| **File location** | Source of truth in `defaults/agents/`, copied to `agents/` on bootstrap |
| **Prompt maintenance** | Version-controlled in `defaults/`, user can customize in `agents/` |
