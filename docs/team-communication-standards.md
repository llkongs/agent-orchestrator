# Team Communication Standards

**Version**: 1.0
**Date**: 2026-02-22
**Author**: PM-FS-001
**Status**: Mandatory for all agents
**Scope**: All Family Store project agents (Engineer, QA, UX, Architect, PM, PMO)

---

## Core Principle

**When in doubt, ask. Never guess.**

If any requirement, term, environment detail, or business logic is unclear, you MUST stop and ask for clarification before proceeding. A 5-minute question prevents hours of rework. Guessing is not initiative -- it is a failure mode.

---

## What You Must Ask About

| Category | Examples | Why |
|----------|----------|-----|
| Physical environment | Printer type, paper type, screen size, network setup | Software behavior depends on hardware. A triplicate carbon form printer behaves completely differently from a laser printer. |
| Business terminology | "一式两份", "对账", "件规", "flag" values | Domain terms have precise meanings that differ from their literal/technical interpretation. |
| Deployment environment | Which directory is live (src vs src2), build process, symlinks, bind mounts | Code changes that aren't deployed don't exist. |
| Boundary conditions | Max rows, empty states, error handling, what happens at exactly N items | Unstated boundaries lead to different assumptions across team members. |
| User workflow | Physical sequence of actions, who touches the paper, where signatures go | Software must match the physical workflow, not the other way around. |

---

## How to Ask

1. **State what you currently understand**: "My understanding is X."
2. **State the ambiguity**: "But I'm not sure whether Y or Z."
3. **Offer concrete options**: "Is it (A) ... or (B) ...?"
4. **Wait for confirmation**: Do not proceed until you receive a clear answer.

**Route questions through PM or CEO (team-lead)**. Do not guess and implement both options. Do not pick one and hope for the best.

**Bad**: Engineer sees "打印两份" and implements `for (copy = 1; copy <= 2; copy++)` without asking.

**Good**: Engineer asks PM: "Does '打印两份' mean (A) software renders 2 copies, or (B) the document header shows '一式两份' as a label, or (C) the physical printer produces duplicates via carbon paper?"

---

## Historical Lessons

### Lesson 1: The Triplicate Form Incident

**What happened**: The user uses triplicate carbon copy paper (三联复写纸). The printer physically produces 3 copies in one pass. No one on the team asked what kind of printer or paper the user has. Engineers assumed software-controlled copies and implemented `PRINT_COPIES = 2`, causing every order to print twice (x3 carbon copies = 6 physical sheets instead of 3). This error persisted through 3 rounds of fixes because the root assumption was never questioned.

**Root cause**: No one asked: "What kind of printer do you use? How does the paper work?"

**Rule**: Always ask about the physical environment before implementing anything that interacts with hardware.

### Lesson 2: The "一式两份" Misinterpretation

**What happened**: User said "一式两份" (a standard Chinese business document term meaning "document produced in duplicate"). Engineer interpreted this literally as "print two copies" and hardcoded `PRINT_COPIES = 2`. The user actually meant the document header should show the label "一式两份" -- the physical duplication is handled by the carbon paper.

**Root cause**: Engineer applied a technical interpretation to a domain-specific business term without asking for clarification.

**Rule**: When you encounter domain terminology, ask PM for the precise product definition. Do not interpret business terms through a technical lens.

### Lesson 3: CSS Changes Not Deployed

**What happened**: Engineer made visual changes to print CSS but the user reported no visual changes. The logic changes (JavaScript) took effect but CSS did not. Root cause: changes were made in the wrong source directory, or build was not refreshed.

**Root cause**: No one verified which source directory is currently deployed before making changes.

**Rule**: Before modifying any file, confirm you are editing the file that is actually being served in production.

---

## Enforcement

- **PM** will include a "Clarification Questions" section in every PRD. Engineers should read this section first.
- **Engineers** must list their assumptions in their implementation plan. PM reviews assumptions before coding begins.
- **QA** tests against real user scenarios (actual data, actual printer, actual paper), not synthetic test cases.
- **Any agent** that encounters an ambiguous requirement and proceeds without asking will have their implementation rejected at review.

---

*This document is required reading for all agents at spawn time.*
