# Agent Orchestrator -- Directory Structure Standard

> Version: 2.0.0
> Date: 2026-02-16
> Author: ARCH-001 (Pipeline Architect)
> Status: ACTIVE
> **MANDATORY READING FOR ALL AGENTS**

This document is a **guideline**, not a snapshot. It defines the rules for where files go, how directories are created, and how naming works. When you encounter "where should this new thing go?", the answer is in this document.

---

## 1. General Principles

### 1.1 Directory Naming

- All directory names use **kebab-case**: `^[a-z][a-z0-9-]*$`
- Examples: `slot-types/`, `test-pipeline/`, `security-hardening/`
- Exception: Python package directories use **snake_case** (Python convention): `test_pipeline/`, `slot_registry/`

### 1.2 File Naming

| File Type | Convention | Pattern | Example |
|-----------|-----------|---------|---------|
| Python source | snake_case | `{name}.py` | `slot_registry.py` |
| Python test | snake_case with `test_` prefix | `test_{module}.py` | `test_models.py` |
| YAML config/schema | kebab-case | `{name}.yaml` | `standard-feature.yaml` |
| Markdown docs | kebab-case | `{name}.md` | `implementation-guide.md` |
| Agent prompts | numbered + kebab-case | `{NN}-{role}-agent.md` | `06-pmo-agent.md` |
| Delivery manifest | uppercase | `DELIVERY.yaml` | `DELIVERY.yaml` |
| Review manifest | uppercase | `REVIEW.yaml` | `REVIEW.yaml` |

### 1.3 ID Conventions

- All pipeline/slot/step IDs: **kebab-case** `^[a-z][a-z0-9-]*$`
- All versions: **semver** `^\d+\.\d+\.\d+$`
- Agent IDs: **uppercase** `{ROLE}-{NNN}` (e.g., `ENG-001`, `PMO-001`)

### 1.4 Ownership Principle

**Every directory has exactly one write-owner.** An agent writes ONLY to its own directory. Reading other directories is encouraged. Writing to another agent's directory is a violation (see `specs/delivery-protocol.md` Section 6).

### 1.5 Self-Service Principle

Any agent that needs a new file or directory should be able to determine its correct location from this document alone, without asking the Architect. If this document does not answer the question, the Architect must update it.

---

## 2. Project Root Layout

```
agent-orchestrator/
|
|-- README.md                    # Project overview
|-- FILE-STANDARD.md             # THIS FILE
|
|-- specs/                       # Specifications (Architect owns)
|-- agents/                      # Agent prompts (HR produces, Team Lead manages)
|
|-- architect/                   # Architect working directory
|-- engineer/                    # Engineer working directory
|-- qa/                          # QA working directory
|-- pmo/                         # PMO working directory
|-- {role}/                      # (Any future role -- see Section 4)
|
`-- state/                       # Pipeline runtime state (Engine manages)
```

There are three categories of top-level directories:

1. **Shared directories**: `specs/`, `agents/`, `state/` -- serve the whole project
2. **Role working directories**: `architect/`, `engineer/`, `qa/`, `pmo/`, etc. -- one per role
3. **Project-level files**: `README.md`, `FILE-STANDARD.md`

---

## 3. Shared Directories

### 3.1 `specs/` -- Specifications (Architect owns)

All specifications, schemas, contracts, designs, and research live here. The Architect is the write-owner, but all agents read from it.

```
specs/
|-- pipelines/
|   |-- schema.yaml                # Pipeline definition schema
|   |-- implementation-guide.md    # Module-by-module spec for Engineer
|   |-- slot-types/                # SlotType interface contracts
|   |   |-- designer.yaml
|   |   |-- researcher.yaml
|   |   |-- implementer.yaml
|   |   |-- reviewer.yaml
|   |   |-- approver.yaml
|   |   `-- {new-type}.yaml        # (see Section 7)
|   `-- templates/                 # Reusable pipeline templates
|       |-- standard-feature.yaml
|       |-- research-task.yaml
|       |-- quant-strategy.yaml
|       |-- security-hardening.yaml
|       |-- hotfix.yaml
|       `-- {new-template}.yaml    # (see Section 8)
|
|-- delivery-protocol.md           # DELIVERY/REVIEW anti-hallucination protocol
|-- delivery-schema.py             # Validation functions
|-- integration-contract.md        # Module interface specifications
|
|-- designs/                       # Feature-level architecture designs
|   `-- {feature-name}-design.md   # (see Section 9)
|
|-- research/                      # Research reports
|   `-- {topic}-research.md        # (see Section 9)
|
`-- diagrams/                      # Architecture diagrams
    `-- *.drawio / *.mermaid       # (see Section 9)
```

### 3.2 `agents/` -- Agent Prompts (HR produces, Team Lead manages)

One file per agent role. HR creates these based on industry research. Team Lead manages the directory.

```
agents/
|-- 00-hr-agent.md
|-- 01-architect-agent.md
|-- 02-engineer-agent.md
|-- 03-qa-agent.md
|-- 04-security-auditor-agent.md    # (if recruited)
|-- 05-signal-researcher-agent.md   # (if recruited)
|-- 06-pmo-agent.md
`-- {NN}-{role}-agent.md            # (see Section 4.3)
```

Numbering rule: assign the next available two-digit number. Numbers do not need to be contiguous if agents are removed.

Every agent .md file MUST have YAML front-matter with capability metadata:

```yaml
---
agent_id: "PMO-001"
version: "1.0"
capabilities:
  - project_tracking
  - risk_assessment
  - status_reporting
compatible_slot_types:
  - approver
  - coordinator
---
```

### 3.3 `state/` -- Pipeline Runtime State (Engine manages)

No agent writes here directly. The pipeline engine manages this directory.

```
state/
|-- active/                        # Running pipelines
|   |-- *.state.yaml               # {pipeline-id}-{timestamp}.state.yaml
|   `-- artifacts/                 # Slot I/O artifacts
|       `-- {slot-id}/
|           |-- slot-input.yaml
|           |-- slot-output.yaml
|           `-- (produced artifacts)
`-- archive/                       # Completed pipelines
    `-- *.state.yaml
```

---

## 4. Role Working Directories -- Rules for New Roles

### 4.1 The Rule

**When HR recruits a new agent role X, that role gets a top-level working directory named `{role}/` in kebab-case.**

Examples:
- Architect -> `architect/`
- Engineer -> `engineer/`
- QA -> `qa/`
- PMO -> `pmo/`
- Security Auditor -> `security-auditor/`
- DevOps -> `devops/`

### 4.2 What Goes in a Role Directory

Every role directory follows this structure:

```
{role}/
|-- DELIVERY.yaml              # Role's delivery manifest (required for producers)
|-- REVIEW.yaml                # Only for QA-type roles
`-- (role-specific artifacts)  # Whatever the role produces
```

**Minimum contents**: The role's `DELIVERY.yaml` when it delivers work.

**Role-specific contents**: Whatever artifacts the role produces during pipeline execution. For example:
- `engineer/src/` and `engineer/tests/` for code
- `qa/additional-tests/` for QA-written supplementary tests
- `pmo/reports/` for status reports and risk assessments

### 4.3 Checklist: Adding a New Role

When HR recruits a new role, the following must happen:

1. **HR** creates `agents/{NN}-{role}-agent.md` with YAML front-matter
2. **Team Lead** creates the top-level directory: `mkdir {role}/`
3. **Architect** updates the permission matrix in this file (Section 5)
4. **Architect** adds role-specific mandatory reads to Section 6 (if any)

### 4.4 Current Role Directories

| Directory | Role | Primary Outputs |
|-----------|------|-----------------|
| `architect/` | Architect | Design artifacts, DELIVERY.yaml |
| `engineer/` | Engineer | Source code, tests, DELIVERY.yaml |
| `qa/` | QA | REVIEW.yaml, additional tests |
| `pmo/` | PMO | Status reports, risk assessments, pipeline tracking |

---

## 5. Read/Write Permission Matrix

### 5.1 Permission Rules

1. **Every role has RW on its own directory** (e.g., Engineer has RW on `engineer/`)
2. **Every role has R on all other directories** (read is always allowed)
3. **Architect has RW on `specs/`** (owns all specifications)
4. **HR and Team Lead have RW on `agents/`** (HR produces prompts, Team Lead manages)
5. **Engine has RW on `state/`** (automated pipeline state)
6. **Team Lead has RW on project root** (`README.md`, `FILE-STANDARD.md`)

### 5.2 Current Matrix

| Agent | `specs/` | `agents/` | `architect/` | `engineer/` | `qa/` | `pmo/` | `state/` |
|-------|----------|-----------|--------------|-------------|-------|--------|----------|
| **Team Lead** | R | **RW** | R | R | R | R | R |
| **Architect** | **RW** | R | **RW** | R | R | R | R |
| **Engineer** | R | R | R | **RW** | R | R | R |
| **QA** | R | R | R | R | **RW** | R | R |
| **PMO** | R | R | R | R | R | **RW** | R |
| **HR** | R | **RW** | R | R | R | R | R |
| **Engine** | R | R | R | R | R | R | **RW** |

### 5.3 Adding a New Role to the Matrix

When a new role is added, insert a row following the same pattern:
- **RW** on its own directory
- **R** on everything else
- Add a column for its directory with R for all other roles

---

## 6. Mandatory Reads Per Role

### 6.1 All Agents (universal)

Every agent MUST read before starting any work:

1. Their own agent prompt: `agents/{NN}-{role}-agent.md`
2. This file: `FILE-STANDARD.md`
3. Delivery protocol: `specs/delivery-protocol.md`

### 6.2 Role-Specific

| Role | Additional Mandatory Reads |
|------|---------------------------|
| **Architect** | `specs/pipelines/schema.yaml`, `specs/pipelines/implementation-guide.md`, `specs/research/pluggable-pipeline-research.md`, `architect/architecture.md` |
| **Engineer** | `architect/architecture.md`, `specs/pipelines/implementation-guide.md`, `specs/integration-contract.md`, relevant `specs/designs/*.md` |
| **QA** | `specs/delivery-protocol.md` (Sections 3 + 8), `specs/delivery-schema.py`, the DELIVERY.yaml being reviewed |
| **HR** | `specs/pipelines/slot-types/` (all), existing `agents/*.md` |
| **PMO** | `architect/architecture.md`, active `state/active/*.state.yaml` files |

### 6.3 Adding Mandatory Reads for a New Role

When the Architect adds a new role to this table, consider:
- Does the role need to understand the overall architecture? -> add `architect/architecture.md`
- Does the role produce deliverables? -> `specs/delivery-protocol.md` is already in the universal list
- Does the role consume specific specs? -> add those specs

---

## 7. SlotType Definitions -- Rules for New Slot Types

### 7.1 Location

All SlotType definitions live in: `specs/pipelines/slot-types/`

### 7.2 File Naming

Pattern: `{slot-type-id}.yaml` in kebab-case.

Examples: `designer.yaml`, `reviewer.yaml`, `signal-expert.yaml`

### 7.3 Required Fields

Every SlotType YAML file MUST contain:

```yaml
slot_type:
  id: "signal-expert"                    # kebab-case, matches filename
  name: "Signal Analysis Expert"         # Human-readable
  category: "research"                   # Functional grouping
  description: "..."                     # What this slot does

  input_schema:
    type: object
    required: [...]                      # At least one required field
    properties:
      ...

  output_schema:
    type: object
    required: [...]                      # At least one required field
    properties:
      ...

  required_capabilities:                 # List of capability strings
    - capability_a
    - capability_b

  constraints:                           # Optional behavioral constraints
    - "..."
```

### 7.4 Who Creates SlotType Definitions

The **Architect** creates and maintains SlotType definitions. Other agents may request new types via SendMessage to the Architect. HR references slot types when producing agent prompts.

### 7.5 Adding a New SlotType -- Checklist

1. Architect creates `specs/pipelines/slot-types/{type-id}.yaml`
2. Architect ensures the file passes `yaml.safe_load()` and has all required fields
3. Architect notifies HR so compatible agents can be produced
4. No engine code changes needed (SlotRegistry auto-discovers)

### 7.6 Current Core SlotTypes

| ID | Category | Purpose |
|----|----------|---------|
| `designer` | architecture | Design documents, interface definitions |
| `researcher` | research | Investigation, analysis, structured reports |
| `implementer` | engineering | Production code + tests |
| `reviewer` | quality | Independent verification, REVIEW.yaml |
| `approver` | governance | Go/No-Go decisions |

---

## 8. Pipeline Templates -- Rules for New Templates

### 8.1 Location

All pipeline templates live in: `specs/pipelines/templates/`

### 8.2 File Naming

Pattern: `{pipeline-id}.yaml` in kebab-case.

Examples: `standard-feature.yaml`, `quant-strategy.yaml`, `incident-response.yaml`

### 8.3 Who Creates Pipeline Templates

The **Architect** designs and maintains pipeline templates. Templates must conform to `specs/pipelines/schema.yaml`.

### 8.4 Adding a New Template -- Checklist

1. Architect creates `specs/pipelines/templates/{template-id}.yaml`
2. Template must pass `PipelineValidator.validate()` with zero errors
3. All `slot_type` references must exist in `specs/pipelines/slot-types/`
4. Architect updates `nl_matcher.py` keyword registry (or notifies Engineer to do so)
5. No other changes needed

### 8.5 Current Templates

| Template | Slots | Use Case |
|----------|-------|----------|
| `standard-feature` | design -> implement -> review -> approve -> deploy | New features |
| `research-task` | research -> architect-review -> decision | Investigation tasks |
| `quant-strategy` | scope -> signal + market (parallel) -> implement -> review -> approve | Trading strategies |
| `security-hardening` | audit -> design -> implement -> review -> approve | Security work |
| `hotfix` | implement -> review -> approve -> deploy | Urgent fixes |

---

## 9. Documentation -- Rules for New Documents

### 9.1 Architecture Documents

- **Location**: `architect/architecture.md` (main), `specs/designs/` (feature-level)
- **Author**: Architect only
- **Naming**: `{feature-name}-design.md` in kebab-case
- **Required sections**: metadata (version, date, author, status), interface definitions, data models, dependency diagram

### 9.2 Research Reports

- **Location**: `specs/research/`
- **Author**: Researcher role (via pipeline), or Architect for architecture-related research
- **Naming**: `{topic}-research.md` in kebab-case
- **Required sections**: metadata, executive summary, findings, recommendations, references

### 9.3 Architecture Diagrams

- **Location**: `specs/diagrams/`
- **Author**: Architect
- **Formats**: `.drawio` (preferred) or `.mermaid`
- **Naming**: `{subject}.drawio` or `{subject}.mermaid` in kebab-case

### 9.4 Integration Contract

- **Location**: `specs/integration-contract.md` (single file)
- **Author**: Architect
- **Rule**: There is ONE integration contract file. It grows as modules are added. Never split into multiple files.

---

## 10. Python Code -- Rules for New Modules

### 10.1 Source Code Location

All source code lives under: `engineer/src/`

Each logical package gets its own directory:

```
engineer/src/
|-- pipeline/           # Pipeline engine package
|   |-- __init__.py
|   |-- models.py
|   `-- ...
|-- {new-package}/      # Future packages
|   |-- __init__.py
|   `-- ...
`-- (no loose .py files at src/ level)
```

### 10.2 Adding a New Python Module

When the Engineer needs to add a new module to an existing package:

1. Create `engineer/src/{package}/{module_name}.py` (snake_case)
2. Create corresponding test file `engineer/tests/test_{package}/test_{module_name}.py`
3. Add public exports to `engineer/src/{package}/__init__.py`
4. The module must follow the dependency constraints in `specs/pipelines/implementation-guide.md`

### 10.3 Adding a New Python Package

When the Engineer needs to create a new package:

1. Create directory `engineer/src/{package_name}/` (snake_case)
2. Create `engineer/src/{package_name}/__init__.py`
3. Create test directory `engineer/tests/test_{package_name}/`
4. Create `engineer/tests/test_{package_name}/__init__.py`
5. Create `engineer/tests/test_{package_name}/conftest.py` for shared fixtures

### 10.4 Test File Correspondence

Every source module has a corresponding test file:

| Source | Test |
|--------|------|
| `src/pipeline/models.py` | `tests/test_pipeline/test_models.py` |
| `src/pipeline/loader.py` | `tests/test_pipeline/test_loader.py` |
| `src/{pkg}/{mod}.py` | `tests/test_{pkg}/test_{mod}.py` |

### 10.5 Test Fixtures

Shared test fixtures (sample YAML files, temp directories, mock objects) go in:

```
engineer/tests/test_{package}/fixtures/
```

### 10.6 Dependency Constraints

The pipeline engine must NOT import from any code outside `src/pipeline/`. It imports only from:
- Python standard library
- PyYAML (`yaml`)
- Its own submodules

This rule applies to all future packages as well: each package declares its allowed imports in the implementation guide.

---

## 11. Special Files

| File | Location | Purpose | Created By |
|------|----------|---------|------------|
| `DELIVERY.yaml` | `{role}/DELIVERY.yaml` | Producer's delivery manifest | Any producing role |
| `REVIEW.yaml` | `qa/REVIEW.yaml` | QA's review manifest | QA only |
| `slot-input.yaml` | `state/active/artifacts/{slot-id}/` | Engine-generated slot input | Engine |
| `slot-output.yaml` | `state/active/artifacts/{slot-id}/` | Agent-written slot output | Executing agent |
| `*.state.yaml` | `state/active/` or `state/archive/` | Pipeline runtime state | Engine |
| `FILE-STANDARD.md` | Project root | This file | Architect + Team Lead |
| `README.md` | Project root | Project overview | Team Lead |

---

## 12. Files That Must Not Be Modified

| File | Protected From | Reason |
|------|---------------|--------|
| `specs/delivery-protocol.md` | All except Architect + Team Lead | Core protocol |
| `specs/delivery-schema.py` | All except Architect + Engineer | Validation logic |
| `FILE-STANDARD.md` | All except Architect + Team Lead | Project standard |
| Any file in an active `DELIVERY.yaml` | All agents | File-freeze during review |
| `specs/pipelines/schema.yaml` | All except Architect | Master schema |

---

## 13. Changelog Requirements

Any file move, delete, or rename MUST be recorded:

1. Note the change in the agent's `DELIVERY.yaml` or send via SendMessage
2. Include: old path, new path, reason
3. Notify Team Lead

This prevents downstream agents from referencing stale paths.

---

## 14. Quick Reference: "Where Does X Go?"

| I need to... | Put it in... | Named as... |
|--------------|-------------|-------------|
| Add a new agent prompt | `agents/` | `{NN}-{role}-agent.md` |
| Add a new SlotType | `specs/pipelines/slot-types/` | `{type-id}.yaml` |
| Add a new pipeline template | `specs/pipelines/templates/` | `{template-id}.yaml` |
| Add a new Python module | `engineer/src/{package}/` | `{module_name}.py` |
| Add a test for a module | `engineer/tests/test_{package}/` | `test_{module_name}.py` |
| Add test fixtures | `engineer/tests/test_{package}/fixtures/` | descriptive name |
| Write a design document | `specs/designs/` | `{feature-name}-design.md` |
| Write a research report | `specs/research/` | `{topic}-research.md` |
| Add an architecture diagram | `specs/diagrams/` | `{subject}.drawio` |
| Create a new role directory | Project root | `{role}/` (kebab-case) |
| Store pipeline state | `state/active/` | `{pipeline-id}-{timestamp}.state.yaml` |
| Store slot artifacts | `state/active/artifacts/{slot-id}/` | varies |
| Write a delivery manifest | Own role directory | `DELIVERY.yaml` |
| Write a review manifest | `qa/` | `REVIEW.yaml` |
| Update integration contract | `specs/integration-contract.md` | (single file, append) |
