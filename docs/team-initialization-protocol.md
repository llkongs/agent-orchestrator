# Team Initialization Protocol

**Version**: 1.0
**Date**: 2026-02-22
**Author**: PM-FS-001
**Status**: Mandatory standard for all new projects and major feature initiatives

---

## 1. Initial Required Roles

These 4 roles must be in place **before any work begins**. They form the management backbone that ensures all subsequent work is correctly scoped, staffed, and tracked.

| Order | Role | Responsibility | Why First |
|-------|------|---------------|-----------|
| 1 | **CEO** | Strategic coordination, task assignment, final acceptance | Decision authority; without CEO, no one can approve scope or resolve conflicts |
| 2 | **HR** | Research roles, write agent prompts, recruit specialists | Specialists need well-crafted prompts; poor prompts produce poor agents |
| 3 | **PM (Product Manager)** | Requirements understanding, PRD authoring, requirements acceptance | Translates user intent into precise specs; prevents the "build the wrong thing" failure |
| 4 | **PMO** | Task decomposition, progress tracking, resource coordination | Ensures work is ordered, dependencies are explicit, and no agent wastes context on blocked tasks |

---

## 2. Initialization Workflow

```
Step 1: User states the need
    |
    v
Step 2: PM + PMO discuss together
    |   - What exactly needs to be done? (requirements clarification)
    |   - What are the options? (solution comparison)
    |   - What comes first? (priority ordering)
    |
    v
Step 3: PM produces initial PRD, user confirms
    |   - PM restates understanding, asks clarifying questions
    |   - User confirms or corrects
    |   - PRD includes worked examples, acceptance criteria, negative scope
    |
    v
Step 4: HR recruits the first specialist: an Architect suited to this domain
    |   - HR researches what kind of architect is needed
    |   - HR writes a tailored agent prompt (role handbook)
    |   - Architect is spawned with the PRD as required reading
    |
    v
Step 5: Architect researches technical approach, produces architecture design doc
    |   - Technology selection, data model, API design, deployment strategy
    |   - Reviews architecture with PM to ensure it satisfies PRD requirements
    |
    v
Step 6: HR recruits remaining specialists based on architecture + PMO work breakdown
    |   - Engineers (backend, frontend, as needed)
    |   - QA
    |   - UX Designer (if UI work is involved)
    |   - Each role gets a tailored agent prompt from HR
    |
    v
Step 7: PM distributes PRD to all relevant roles; PMO creates tasks with dependencies
    |   - Each agent receives: PRD + architecture doc + team communication standards
    |   - PMO creates task graph with explicit blockedBy relationships
    |   - Work begins in dependency order
```

---

## 3. Why You Cannot Skip Steps

| Skipped Step | Consequence | Real Example |
|-------------|-------------|--------------|
| **Skip PM** | Requirements misunderstood. Engineers build based on their own interpretation of user's words. Result: the delivered product is not what the user wanted. | Triplicate paper incident: no one asked about printer type. "一式两份" interpreted as software copies instead of carbon paper label. 3 rounds of rework. |
| **Skip Architect, recruit Engineers first** | No technical blueprint. Engineers make ad-hoc architecture decisions that conflict with each other. Integration fails. Rework cost is 3-5x higher than doing architecture first. | Building on wrong source directory (src vs src2); CSS changes not deployed because no one mapped the build pipeline. |
| **Skip PMO** | Tasks are unordered. Agents work on blocked items, waste context window, duplicate effort, or work on low-priority items while blockers remain unresolved. | Agent context exhaustion from uncoordinated parallel work; engineers fixing symptoms while root causes remain unaddressed. |
| **Skip HR (use generic prompts)** | Agents lack domain knowledge, role boundaries, and quality standards. They drift into other roles' responsibilities or produce generic, low-quality output. | Engineer writing PRD-level requirements analysis; PM writing CSS code; QA only reading code instead of testing with real data. |

---

## 4. Required Reading for All Agents at Spawn

Every agent, regardless of role, must read the following documents upon initialization:

1. **Their role handbook** (written by HR, stored in `agents/` directory)
2. **Team Communication Standards** (`docs/team-communication-standards.md`) -- the "ask, never guess" protocol
3. **This document** (`docs/team-initialization-protocol.md`) -- so they understand their place in the workflow
4. **The active PRD** for their assigned task (stored in `docs/` or `prd/` directory)

---

## 5. Checklist: Before Starting Any New Initiative

- [ ] CEO is available and has approved the initiative scope
- [ ] PM has produced a PRD with user confirmation (Steps 2-3 complete)
- [ ] PRD contains: worked examples, acceptance criteria, negative scope, data dependencies
- [ ] HR has written a role handbook for the first specialist needed
- [ ] Architect has produced an architecture design doc (Step 5 complete)
- [ ] PMO has created a task graph with dependencies
- [ ] All agents have read: role handbook + communication standards + PRD
- [ ] Team communication standards doc is included in every agent's required reading

---

*This protocol applies to all projects under the agent-orchestrator framework. Deviations require explicit CEO approval with documented justification.*
