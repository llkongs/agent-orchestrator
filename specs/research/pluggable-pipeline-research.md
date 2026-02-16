# Pluggable Agent Pipeline Framework: Industry Research Report

## Metadata
- Author: ARCH-001 (System Architect)
- Date: 2026-02-15
- Task: CEO-initiated research on pluggable agent pipeline framework
- Status: FINAL
- Supersedes: `pipeline-framework-research.md` (YAML template approach)

---

## Executive Summary

The CEO's vision is fundamentally different from our prior pipeline design. The prior work (`pipeline-framework-research.md`, `pipeline-engine-design.md`) defined **fixed YAML templates** where steps are pre-wired to specific agent roles. The new vision is a **Lego-like system**: Architect designs a pipeline topology (slots + data flow), HR fills each slot with an agent .md, and agents are hot-swappable without breaking the pipeline.

Key findings:

1. **The industry is converging on standardized inter-agent protocols** -- Google's A2A (Agent-to-Agent), Anthropic's MCP (Model Context Protocol), and Microsoft's Agent Framework all define capability-based agent interfaces. The trend is toward agents as "services" with discoverable capabilities, not hardcoded roles.

2. **No existing framework fully implements the "empty slot + HR fills" pattern.** CrewAI's YAML role definitions come closest (role/goal/backstory are swappable), but the pipeline topology is still coupled to role names. MetaGPT's SOP approach hardcodes roles. The CEO's vision is more radical: the pipeline has numbered, typed slots, and ANY agent .md that satisfies the slot's interface contract can be plugged in.

3. **The Unix pipe philosophy is the correct mental model.** Agents are like Unix commands: each reads from stdin (standardized input), writes to stdout (standardized output), and any command that conforms to the text interface can be swapped in. Our equivalent: each agent reads a `SlotInput` (standardized JSON/YAML), writes a `SlotOutput`, and any agent .md that satisfies the slot's type can fill it.

4. **Three inter-agent protocol patterns** are viable for our system: (a) Artifact-passing via filesystem (current, simple, proven), (b) Typed message envelopes (A2A-inspired, more structured), (c) Blackboard/shared-state (central knowledge store agents read/write). Recommended: **hybrid of (a) and (b)** -- filesystem artifacts for heavy content, typed message envelopes for coordination.

5. **Implementation complexity is moderate.** The slot abstraction adds one layer on top of our existing pipeline engine design. The key new concepts: SlotType (defines interface contract), SlotInstance (filled with an agent .md), and SlotProtocol (standardized I/O format). Estimated: ~300 lines of new Python, ~200 lines of YAML schema updates.

---

## 1. How the CEO's Vision Differs from Our Prior Design

| Aspect | Prior Design (YAML Templates) | CEO's Vision (Pluggable Slots) |
|--------|-------------------------------|-------------------------------|
| Pipeline definition | Steps hardcoded to roles (`role: ARCH-001`) | Slots defined by TYPE, not by who fills them |
| Agent assignment | Pipeline creator picks the agent | HR researches and fills each slot |
| Swappability | Change pipeline YAML to swap an agent | Swap the .md file, pipeline unchanged |
| Topology ownership | Pipeline template defines both topology AND roles | Architect defines topology; HR fills roles independently |
| Reuse | Templates are reused across similar projects | Topologies are reused; agents are mixed-and-matched |
| Analogy | Blueprint with named contractors | Blueprint with labeled sockets + any compatible plug |

**The core insight**: In the prior design, "step" = "specific agent role". In the CEO's vision, "slot" = "interface contract" and "agent" = "any .md that satisfies the contract". This separation of topology from personnel is the key innovation.

---

## 2. Industry Survey: Multi-Agent Orchestration Frameworks

### 2.1 Comprehensive Framework Comparison

| Framework | Agent Definition | Pluggability | Protocol | Topology | Dynamic Role | Relevance |
|-----------|-----------------|-------------|----------|----------|-------------|-----------|
| **LangGraph** | Python node functions | Medium -- swap node implementations | Typed state channels | Graph (DAG) with conditional edges | Low -- roles are code | Medium |
| **CrewAI** | YAML (role/goal/backstory) + tools | **High** -- YAML config is swappable | Hub-and-spoke via manager | Sequential / hierarchical | Medium -- YAML-driven roles | **High** |
| **AutoGen / MS Agent Framework** | Agent classes with typed I/O | Medium -- typed interfaces | Async messages (JSON-RPC) | Graph-based workflows | Medium -- A2A integration | High |
| **MetaGPT** | SOP-driven role classes | Low -- roles are Python classes | Shared message pool | Waterfall phases | Low -- roles are hardcoded | Low |
| **ChatDev** | Role prompts (CEO, CTO, etc.) | Medium -- prompts are swappable | Chat chain (turn-based) | Phase-based (design/code/test) | Low -- fixed phase structure | Medium |
| **CAMEL** | Inception prompts (role-playing) | **High** -- prompts define roles entirely | Direct message exchange | Dyadic (2-agent conversation) | High -- any prompt = any role | Medium |
| **AgentScope** | Modular components (message/model/memory/tool) | **High** -- components are decoupled | Message Hub + pipelines | Flexible (pipeline/group/broadcast) | High -- runtime composition | **High** |
| **A2A Protocol** | Agent Cards (capability advertisement) | **Highest** -- discovery-based | HTTP/SSE + JSON-RPC 2.0 | Peer-to-peer (no fixed topology) | **Highest** -- capability negotiation | High (protocol, not framework) |
| **OpenAI Swarm** | Python functions with handoff | Low -- functions are code | Direct function calls | No fixed topology (handoff-driven) | Low | Low |

### 2.2 Deep Dive: Most Relevant Frameworks

#### 2.2.1 CrewAI -- Closest to "Swappable Roles via Config"

CrewAI defines agents in YAML with three core fields:
```yaml
# config/agents.yaml
senior_researcher:
  role: "Senior Data Researcher"
  goal: "Uncover cutting-edge developments in {topic}"
  backstory: "You're a seasoned researcher with a knack for uncovering..."
  tools:
    - SerperDevTool
    - ScrapeWebsiteTool
  allow_delegation: true
```

**Why this matters for us**: The agent definition is entirely in config. Swapping the YAML file changes the agent's identity, expertise, and behavior without changing the pipeline code. This is close to the CEO's vision of "swap the .md, swap the person."

**Gap**: CrewAI's task definitions still reference agent names directly (`agent: senior_researcher`). The pipeline topology is coupled to the agent identity. In the CEO's vision, the topology references SLOT TYPES, not agent names.

#### 2.2.2 AgentScope -- Most Modular Architecture

AgentScope divides agents into four decoupled modules: message, model, memory, and tool. This is the most modular decomposition in the industry. Key features:

- **Message Hub**: Agents publish/subscribe to topics, enabling many-to-many communication without direct coupling
- **Pipeline abstraction**: Sequential, conditional, and parallel execution patterns as first-class constructs
- **Runtime composition**: Agents can be assembled at runtime from independent components
- **Agent-as-API**: Each agent exposes a standard API interface (FastAPI-based in v1.0)

**Why this matters**: AgentScope's pipeline+message architecture is closest to the Unix pipe model. Agents are composable because they share a standardized message interface.

**Gap**: AgentScope is LLM-API-oriented (OpenAI/Anthropic API calls). Our agents are Claude Code CLI subprocesses, so the execution model is different.

#### 2.2.3 Google A2A -- The Standard for Agent Interoperability

A2A (Agent-to-Agent Protocol) is the most ambitious effort to standardize how agents discover, negotiate, and communicate:

- **Agent Cards**: Each agent publishes a capability manifest (skills, supported I/O formats, authentication)
- **Task-based interaction**: Agents exchange "Tasks" with structured input/output, not free-form text
- **Negotiation**: Agents negotiate interaction modalities (text, files, structured data) before collaboration
- **Discovery**: Agents find each other by capability, not by name
- **Transport**: HTTP + Server-Sent Events (SSE) + JSON-RPC 2.0

**Why this matters**: A2A's "Agent Card" is essentially a machine-readable version of our agent .md files. The discovery-by-capability model is exactly the CEO's vision: slots define what capability is needed, agents advertise what they can do, HR matches them.

**Gap**: A2A is a network protocol for distributed agents. Our agents are local subprocesses on a single machine. The concepts transfer, but the transport doesn't.

#### 2.2.4 CAMEL -- Role-Playing via Prompts

CAMEL's key innovation is "inception prompting": the ENTIRE agent role is defined by a prompt, and swapping the prompt swaps the role completely. This is the most extreme version of "pluggable agents."

- **Role prompts define everything**: identity, expertise, communication style, constraints
- **No external tools or code needed**: the prompt IS the agent
- **Inception prompting prevents role drift**: explicit instructions like "Never flip roles!" maintain boundaries

**Why this matters**: Our agent .md files ARE inception prompts. CAMEL validates that prompt-defined roles are a viable and proven approach.

#### 2.2.5 MetaGPT -- SOP-Driven but Rigid

MetaGPT's core philosophy is "Code = SOP(Team)": standardized operating procedures drive agent behavior.

- **SOPs as code**: Each role has a predefined action sequence (product manager writes PRD, architect writes design, etc.)
- **Shared message pool**: All agents read/write to a central message store
- **Phase-gated execution**: Design -> Coding -> Testing phases with quality gates

**Why this matters**: MetaGPT's SOP approach is similar to our existing delivery protocol. Their shared message pool is a form of blackboard pattern.

**Critical gap**: MetaGPT's roles are Python classes with hardcoded SOPs. You cannot "plug in" a new role without writing code. This is the opposite of pluggable.

---

## 3. Inter-Agent Protocol Patterns

### 3.1 Pattern A: Filesystem Artifact Passing

```
Agent A writes to:  /output/agent-a/result.yaml
Agent B reads from: /output/agent-a/result.yaml (declared as input dependency)
```

| Aspect | Assessment |
|--------|-----------|
| **Simplicity** | Highest -- just files on disk |
| **Debugging** | Easy -- inspect files directly |
| **Type safety** | Low unless schema-validated |
| **Coupling** | Low -- agents only share file paths |
| **Performance** | Fine for our use case (no real-time needs) |
| **Industry examples** | CI/CD artifacts (GitHub Actions, Azure Pipelines), our DELIVERY.yaml |

**Pros**:
- Already proven in our system (DELIVERY.yaml, REVIEW.yaml)
- Human-inspectable at every stage
- No new infrastructure
- Works perfectly with Claude Code CLI (agents read/write files natively)

**Cons**:
- No schema enforcement unless explicitly added
- No notification mechanism (polling or manual sequencing)
- Large artifacts consume disk

### 3.2 Pattern B: Typed Message Envelopes

```python
@dataclass
class SlotMessage:
    slot_id: str           # Which slot produced this
    message_type: str      # "design_output" | "code_output" | "review_output"
    schema_version: str    # "1.0"
    payload: dict          # The actual content (structured)
    artifacts: list[str]   # File paths to associated artifacts
    metadata: dict         # Timestamp, producer info, etc.
```

| Aspect | Assessment |
|--------|-----------|
| **Simplicity** | Medium -- requires message schema definition |
| **Debugging** | Medium -- structured but more complex than plain files |
| **Type safety** | High -- schema validates message structure |
| **Coupling** | Very low -- agents only know message types, not each other |
| **Performance** | Fine for our use case |
| **Industry examples** | A2A protocol, AutoGen messages, AgentScope Message Hub |

**Pros**:
- Schema enforcement at message boundaries
- Agents are truly decoupled (communicate via typed messages, not file paths)
- Versioned schemas allow backward compatibility
- Maps to A2A Task concept

**Cons**:
- Additional abstraction layer to implement
- Our agents are Claude Code CLI subprocesses -- message passing is via files/SendMessage anyway

### 3.3 Pattern C: Blackboard / Shared State

```
Central Blackboard (shared knowledge store)
  ├── /project-context     (read by all agents)
  ├── /slot-1-output       (written by slot 1 agent, read by slot 2+)
  ├── /slot-2-output       (written by slot 2 agent)
  └── /pipeline-state      (written by orchestrator)

Agents read the blackboard, do work, write results back to blackboard.
```

| Aspect | Assessment |
|--------|-----------|
| **Simplicity** | Medium -- requires shared state management |
| **Debugging** | Good -- all state visible in one place |
| **Type safety** | Depends on implementation |
| **Coupling** | Low -- agents know the blackboard schema, not each other |
| **Performance** | Fine for our use case |
| **Industry examples** | LbMAS, agent-blackboard framework, MetaGPT shared message pool |

**Pros**:
- All agents share context naturally (no explicit message routing)
- New agents can read all prior context without explicit wiring
- Closest to "shared memory" model used in human teams (everyone reads the project wiki)
- Easy to add observability (just inspect the blackboard)

**Cons**:
- Risk of state corruption if multiple agents write concurrently
- Requires conventions on who writes where
- Can become a "god object" if not structured

### 3.4 Recommendation: Hybrid (A + B)

For our specific constraints (Claude Code CLI, file-based agent execution, Agent Teams):

**Use filesystem artifacts (Pattern A) as the transport**, but wrap them in **typed message envelopes (Pattern B) for schema enforcement**.

In practice:
1. Each slot produces a standardized output file (`slot-output.yaml`) with a typed envelope
2. The envelope contains: slot ID, output type, schema version, payload, artifact paths
3. The downstream slot reads the upstream output file
4. A validator checks the envelope schema before the downstream slot starts

This gives us:
- No new infrastructure (files on disk)
- Schema enforcement (typed envelopes)
- Human-inspectable (YAML files)
- Decoupling (agents know message types, not each other)

---

## 4. Pluggable Agent Slot Design Patterns

### 4.1 The Slot Abstraction

The core innovation: separate **what the slot needs** from **who fills it**.

```
SlotType (the "socket")          AgentDefinition (the "plug")
========================         =============================
- input_schema: {...}            - role: "Senior Researcher"
- output_schema: {...}           - goal: "..."
- required_capabilities: [...]   - backstory: "..."
- constraints: [...]             - capabilities: [...]
                                 - tools: [...]

HR matches: agent.capabilities SATISFIES slot.required_capabilities
```

#### SlotType Definition

```yaml
# A slot type defines WHAT is needed, not WHO does it
slot_type:
  id: "researcher"                          # Slot type identifier
  name: "Research Analyst"                  # Human-readable label
  category: "research"                      # Functional category

  # Interface contract -- what this slot receives and produces
  input_schema:
    type: "object"
    required: ["research_brief"]
    properties:
      research_brief:
        type: "string"
        description: "The research question and scope"
      context_artifacts:
        type: "array"
        items: { type: "string" }
        description: "Paths to existing context files"

  output_schema:
    type: "object"
    required: ["research_report", "confidence_level"]
    properties:
      research_report:
        type: "string"
        description: "Path to the research report file"
      confidence_level:
        type: "string"
        enum: ["high", "medium", "low"]
      key_findings:
        type: "array"
        items: { type: "string" }

  # What capabilities the agent filling this slot must have
  required_capabilities:
    - "web_search"                          # Must be able to search the internet
    - "technical_analysis"                  # Must understand technical topics
    - "structured_report_writing"           # Must produce structured reports

  # Behavioral constraints for this slot
  constraints:
    - "Must cite sources for all claims"
    - "Must produce output within 4 hours"
    - "Must write output to the designated slot output path"
```

#### AgentDefinition (.md file with capability metadata)

```yaml
# Front-matter in agent .md file (machine-parseable header)
---
agent_id: "SIG-001"
version: "1.0"
capabilities:
  - "web_search"
  - "technical_analysis"
  - "structured_report_writing"
  - "market_data_analysis"
  - "signal_processing"
compatible_slot_types:
  - "researcher"
  - "analyst"
  - "signal_expert"
---

# Signal Research Agent

You are a signal research specialist...
(rest of the .md is the prompt)
```

#### Matching Rule

```
An agent .md can fill a slot if and only if:
  agent.capabilities SUPERSET_OF slot.required_capabilities
```

This is analogous to:
- Java interfaces: a class can implement an interface if it provides all required methods
- USB ports: a device can plug in if it conforms to the USB spec
- A2A Agent Cards: an agent can handle a task if its capabilities match

### 4.2 How HR Fills a Slot

```
CEO/Architect defines pipeline:
  slot[0]: type=designer, input=requirements, output=design_doc
  slot[1]: type=researcher, input=design_brief, output=research_report
  slot[2]: type=implementer, input=design+research, output=code+delivery
  slot[3]: type=reviewer, input=code+delivery, output=review
  slot[4]: type=approver, input=review, output=approval

HR receives slot manifest:
  "We need: 1 designer, 1 researcher, 1 implementer, 1 reviewer, 1 approver"

HR workflow for each slot:
  1. Read slot type definition (required_capabilities, constraints)
  2. WebSearch: "What does a world-class {slot.name} look like?"
  3. WebSearch: "Best practices for {slot.category} in {domain}"
  4. Produce agent .md with:
     - Capability metadata matching slot requirements
     - Prompt based on industry research
  5. Validate: agent.capabilities SUPERSET_OF slot.required_capabilities
  6. Register agent as compatible with slot type

Pipeline instantiation:
  For each slot:
    1. Find agents compatible with this slot type
    2. If exactly 1: auto-assign
    3. If multiple: HR/CEO picks (or best-match scoring)
    4. If none: HR must recruit (produce new .md)
```

### 4.3 How This Enables Swappability

**Scenario: Swap a researcher without changing the pipeline**

Before:
```
Pipeline: strategy-optimization
  slot[1] type=researcher -> filled by SIG-001 (Signal Researcher)
```

After:
```
Pipeline: strategy-optimization  (UNCHANGED)
  slot[1] type=researcher -> filled by STRAT-001 (Strategy Researcher)
```

Both SIG-001 and STRAT-001 have `capabilities: [web_search, technical_analysis, structured_report_writing]`. They both satisfy the `researcher` slot type. The pipeline definition is identical -- only the slot assignment changes.

**Scenario: Same agent fills different slot types**

An agent with capabilities `[web_search, technical_analysis, structured_report_writing, code_review]` could fill BOTH a `researcher` slot and a `reviewer` slot in different pipelines (or even the same pipeline, if the topology allows).

---

## 5. The Pipeline Topology (Architect's Domain)

### 5.1 Topology = Slots + Data Flow + Ordering

The Architect defines:
1. **Slots**: How many, what types, in what order
2. **Data flow**: Which slot's output feeds into which slot's input
3. **Parallelism**: Which slots can execute concurrently
4. **Gates**: What conditions must pass between slots

The Architect does NOT define:
- Which agent fills which slot (that's HR's job)
- The internal behavior of agents (that's defined in the .md prompt)
- The specific content of artifacts (that's defined by the slot type schemas)

### 5.2 Topology Definition

```yaml
# topology.yaml -- Architect defines this
topology:
  id: "strategy-optimization"
  name: "Quantitative Strategy Optimization"
  version: "1.0"
  description: "End-to-end pipeline for optimizing a trading strategy"

  # Slot definitions (typed placeholders)
  slots:
    - id: "slot-design"
      type: "designer"                # References a SlotType definition
      name: "Strategy Design"

    - id: "slot-research-a"
      type: "researcher"
      name: "Signal Research"

    - id: "slot-research-b"
      type: "researcher"              # Same type as slot-research-a!
      name: "Market Research"

    - id: "slot-implement"
      type: "implementer"
      name: "Code Implementation"

    - id: "slot-review"
      type: "reviewer"
      name: "Quality Review"

    - id: "slot-approve"
      type: "approver"
      name: "CEO Approval"

  # Data flow (edges in the DAG)
  data_flow:
    - from: "slot-design"
      to: "slot-research-a"
      artifact: "design_brief"

    - from: "slot-design"
      to: "slot-research-b"
      artifact: "design_brief"

    - from: "slot-research-a"
      to: "slot-implement"
      artifact: "signal_report"

    - from: "slot-research-b"
      to: "slot-implement"
      artifact: "market_report"

    - from: "slot-design"
      to: "slot-implement"
      artifact: "design_doc"

    - from: "slot-implement"
      to: "slot-review"
      artifact: "delivery"

    - from: "slot-review"
      to: "slot-approve"
      artifact: "review"

  # Execution constraints
  execution:
    parallel_groups:
      - ["slot-research-a", "slot-research-b"]  # Run in parallel

    gates:
      - after: "slot-implement"
        check: "delivery_valid"
      - after: "slot-review"
        check: "review_valid"
```

### 5.3 Topology Visualization

```
                    ┌──────────────┐
                    │  slot-design │
                    │  (designer)  │
                    └──┬─────┬──┬──┘
                       │     │  │
              ┌────────┘     │  └────────┐
              v              │           v
   ┌──────────────────┐     │  ┌──────────────────┐
   │ slot-research-a  │     │  │ slot-research-b  │
   │ (researcher)     │     │  │ (researcher)     │
   └────────┬─────────┘     │  └────────┬─────────┘
            │               │           │
            └───────┬───────┘───────────┘
                    v
           ┌──────────────────┐
           │  slot-implement  │
           │  (implementer)   │
           └────────┬─────────┘
                    │
                    v
           ┌──────────────────┐
           │   slot-review    │
           │   (reviewer)     │
           └────────┬─────────┘
                    │
                    v
           ┌──────────────────┐
           │   slot-approve   │
           │   (approver)     │
           └──────────────────┘
```

Note: `slot-research-a` and `slot-research-b` are both of type `researcher` but can be filled by DIFFERENT agents. One could be a signal researcher, the other a market structure researcher. The topology doesn't care -- they both satisfy the `researcher` interface.

---

## 6. The Standardized Protocol

### 6.1 Slot Protocol: How Every Agent Interacts with the Pipeline

Every agent, regardless of role, follows the same protocol:

```
┌─────────────────────────────────────────────────┐
│                SLOT PROTOCOL                      │
│                                                   │
│  1. READ: Agent reads its slot-input.yaml         │
│     - Contains: input artifacts from upstream      │
│     - Contains: task objective and constraints     │
│     - Contains: output schema requirements        │
│                                                   │
│  2. READ: Agent reads its own .md prompt          │
│     - Contains: role identity, capabilities       │
│     - Contains: behavioral instructions           │
│                                                   │
│  3. EXECUTE: Agent does its work                  │
│     - Reads context files as needed               │
│     - Performs analysis/coding/review/etc.         │
│     - Writes output files to designated paths     │
│                                                   │
│  4. WRITE: Agent writes slot-output.yaml          │
│     - Must conform to slot type's output_schema   │
│     - Contains: artifact paths + metadata         │
│     - Contains: completion status                 │
│                                                   │
│  5. SIGNAL: Pipeline detects completion           │
│     - Validates slot-output against schema        │
│     - Runs post-condition gates                   │
│     - Unblocks downstream slots                   │
└─────────────────────────────────────────────────┘
```

### 6.2 Slot Input/Output File Format

```yaml
# slot-input.yaml (auto-generated by pipeline engine)
slot_id: "slot-research-a"
slot_type: "researcher"
pipeline_id: "strategy-optimization-2026-02-15"
timestamp: "2026-02-15T10:00:00Z"

# What the agent must do
task:
  objective: "Research signal patterns for BTC/USDT momentum strategy"
  constraints:
    - "Must cite sources for all claims"
    - "Must produce report within 4 hours"
  deliverables:
    - "Research report (Markdown, >2000 words)"
    - "Summary of key findings (structured YAML)"

# What the agent receives from upstream
inputs:
  design_brief:
    from_slot: "slot-design"
    path: "architect/pipelines/active/artifacts/slot-design/design_brief.md"
    schema_version: "1.0"

# What the agent must produce
output_requirements:
  schema: "researcher_output_v1"
  required_fields:
    - "research_report"
    - "confidence_level"
  output_path: "architect/pipelines/active/artifacts/slot-research-a/"

# Agent prompt reference
agent_prompt: "agents/05-signal-researcher-agent.md"
```

```yaml
# slot-output.yaml (written by the agent upon completion)
slot_id: "slot-research-a"
slot_type: "researcher"
pipeline_id: "strategy-optimization-2026-02-15"
completed_at: "2026-02-15T13:45:00Z"
status: "completed"  # "completed" | "failed" | "needs_review"

# Output artifacts
output:
  research_report: "architect/pipelines/active/artifacts/slot-research-a/report.md"
  confidence_level: "high"
  key_findings:
    - "BTC/USDT shows strong momentum signals on 4H timeframe"
    - "RSI divergence detected at key support levels"
    - "Volume profile suggests accumulation phase"

# Metadata for audit trail
metadata:
  agent_id: "SIG-001"
  execution_time_minutes: 225
  tools_used: ["web_search", "data_analysis"]
  sources_cited: 12
```

### 6.3 Protocol Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| **Input completeness** | Pipeline engine only starts a slot when all input artifacts exist |
| **Output conformance** | Pipeline engine validates slot-output.yaml against output_schema before passing downstream |
| **Type safety** | SlotType definitions enforce input/output schemas |
| **Isolation** | Each slot writes to its own output directory |
| **Auditability** | All slot-input.yaml and slot-output.yaml files are retained for audit |
| **Idempotency** | Re-running a slot regenerates its output directory from scratch |

---

## 7. Recommended Approach for Our System

### 7.1 Design: Layered Architecture

Build the pluggable pipeline as a layer on top of the existing pipeline engine design:

```
Layer 3: Pluggable Slot Framework (NEW)
  - SlotType definitions (YAML)
  - Agent capability metadata (YAML front-matter in .md files)
  - Slot-agent matching engine
  - HR slot-filling workflow

Layer 2: Pipeline Engine (EXISTING -- pipeline-engine-design.md)
  - Pipeline YAML definition
  - DAG validation
  - Gate checking
  - State tracking
  - Step execution

Layer 1: Execution Substrate (EXISTING)
  - Claude Code Agent Teams
  - Task system
  - SendMessage
  - File system
```

### 7.2 What Changes from the Prior Design

| Component | Prior Design | Pluggable Design | Change Effort |
|-----------|-------------|-------------------|---------------|
| Pipeline YAML | Steps reference `role: ARCH-001` directly | Steps reference `slot_type: designer` | Small (rename) |
| Agent .md files | No machine-readable metadata | Add YAML front-matter with capabilities | Small |
| Pipeline validator | Checks role availability | Checks slot-agent compatibility | Small |
| New: SlotType registry | N/A | YAML files defining slot types | Medium (new) |
| New: Slot-agent matcher | N/A | Capability matching logic | Small (new) |
| New: HR workflow integration | N/A | HR reads slot manifest, produces matching .md | Process (no code) |
| Pipeline engine | Steps executed directly | Steps resolved through slot→agent mapping | Small |

### 7.3 Concrete Design Sketch

#### SlotType Registry

```
architect/pipelines/
  slot-types/
    designer.yaml           # SlotType: designer
    researcher.yaml         # SlotType: researcher
    implementer.yaml        # SlotType: implementer
    reviewer.yaml           # SlotType: reviewer
    approver.yaml           # SlotType: approver
    auditor.yaml            # SlotType: security auditor
    signal-expert.yaml      # SlotType: signal analysis expert
    strategy-expert.yaml    # SlotType: strategy design expert
```

#### Pipeline with Slots (vs. Pipeline with Roles)

Before (fixed roles):
```yaml
steps:
  - id: "design"
    role: "ARCH-001"
    agent_prompt: "agents/01-architect-agent.md"
```

After (pluggable slots):
```yaml
slots:
  - id: "design"
    type: "designer"  # References slot-types/designer.yaml
    # agent_prompt is resolved at runtime by matching
```

#### Slot Assignment Manifest (HR produces this)

```yaml
# slot-assignments.yaml (produced by HR for a specific pipeline instance)
pipeline_id: "strategy-optimization-2026-02-15"
assignments:
  - slot_id: "slot-design"
    slot_type: "designer"
    agent_id: "ARCH-001"
    agent_prompt: "agents/01-architect-agent.md"
    reason: "Only architect with trading system design experience"

  - slot_id: "slot-research-a"
    slot_type: "researcher"
    agent_id: "SIG-001"
    agent_prompt: "agents/05-signal-researcher-agent.md"
    reason: "Signal analysis specialist, proven track record in Phase 4"

  - slot_id: "slot-research-b"
    slot_type: "researcher"
    agent_id: "STRAT-002"
    agent_prompt: "agents/06-strategy-researcher-agent.md"
    reason: "Strategy optimization expertise, complementary to SIG-001"

  - slot_id: "slot-implement"
    slot_type: "implementer"
    agent_id: "ENG-001"
    agent_prompt: "agents/02-engineer-agent.md"
    reason: "Primary engineer, familiar with codebase"

  - slot_id: "slot-review"
    slot_type: "reviewer"
    agent_id: "QA-001"
    agent_prompt: "agents/03-qa-agent.md"
    reason: "Independent QA, proven Phase 1-4 track record"

  - slot_id: "slot-approve"
    slot_type: "approver"
    agent_id: "CEO"
    agent_prompt: null
    reason: "Human approval required"
```

### 7.4 The Complete Flow

```
1. CEO: "I want to optimize the momentum strategy for BTC/USDT"
         |
         v
2. ARCHITECT designs topology:
   - Reads requirement
   - Selects/creates pipeline topology
   - Defines: 6 slots (designer, 2x researcher, implementer, reviewer, approver)
   - Defines: data flow between slots
   - Defines: gates and constraints
   - Produces: topology.yaml
         |
         v
3. PIPELINE ENGINE generates slot manifest:
   - Parses topology.yaml
   - Lists required slot types and their capabilities
   - Produces: slot-manifest.yaml
         |
         v
4. HR reads slot manifest:
   - For each slot type:
     a. Check existing agents for capability match
     b. If match: recommend agent
     c. If no match: research and produce new agent .md
   - Produces: slot-assignments.yaml
         |
         v
5. CEO reviews slot assignments:
   - Confirms or modifies agent assignments
   - "Why did you pick SIG-001 for signal research?"
   - "I want a different researcher for market research"
         |
         v
6. PIPELINE ENGINE instantiates:
   - Merges topology + slot assignments
   - Generates slot-input.yaml for the first slot(s)
   - Begins execution
         |
         v
7. Execution:
   - Each slot's agent:
     a. Reads slot-input.yaml
     b. Reads its own .md prompt
     c. Does work
     d. Writes slot-output.yaml
   - Pipeline engine validates outputs
   - Pipeline engine generates next slot's inputs
   - Continues until all slots complete
         |
         v
8. Pipeline COMPLETE
   - All artifacts archived
   - Execution record saved
```

---

## 8. Feasibility Assessment

### 8.1 Technical Feasibility

| Aspect | Assessment | Score |
|--------|-----------|-------|
| SlotType YAML definitions | Straightforward YAML schema | 5/5 |
| Agent capability metadata | YAML front-matter in .md files -- trivial to add | 5/5 |
| Capability matching | Simple set containment check | 5/5 |
| Slot-input/output generation | YAML templating from topology | 4/5 |
| Integration with existing pipeline engine | Adds a resolution layer on top | 4/5 |
| HR workflow integration | Process change, no code | 4/5 |
| Topology visualization | ASCII art / Mermaid from YAML | 4/5 |
| **Overall** | | **4.4/5** |

### 8.2 Organizational Feasibility

| Aspect | Assessment | Score |
|--------|-----------|-------|
| Separation of concerns (Architect vs HR) | Clear division; each owns their artifact | 5/5 |
| CEO workflow compatibility | CEO reviews topology + assignments; familiar pattern | 5/5 |
| Agent .md backward compatibility | Add front-matter to existing .md files; no content changes | 5/5 |
| Learning curve for slot concepts | SlotType = interface, Agent = implementation; universal pattern | 4/5 |
| Existing pipeline reuse | Prior pipeline templates can be converted to topologies | 4/5 |
| **Overall** | | **4.6/5** |

### 8.3 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Over-abstraction: slot system adds complexity without benefit for small team | Medium | Medium | Start with 5 core slot types; add more only when needed |
| HR produces .md that technically matches capabilities but is low quality | Medium | High | QA reviews agent .md; capability match is necessary but not sufficient |
| Pipeline topology becomes stale | Low | Low | Topology is versioned; old versions remain usable |
| Schema evolution breaks compatibility | Low | Medium | Schema versions with backward-compatible evolution |
| Agent cannot fulfill slot despite matching capabilities | Medium | Medium | Post-condition gates catch quality failures; retry or re-assign |

### 8.4 Implementation Complexity

| Component | Lines of Code | Effort | Priority |
|-----------|--------------|--------|----------|
| SlotType YAML schema definition | ~50 YAML | Small | P0 |
| 5 core SlotType definitions | ~250 YAML (5 x ~50) | Small | P0 |
| Agent .md front-matter additions | ~30 YAML per .md (x6 existing agents) | Small | P0 |
| Capability matcher (`slot_matcher.py`) | ~100 Python | Small | P1 |
| Slot input/output generator | ~150 Python | Small | P1 |
| Topology-to-pipeline resolver | ~200 Python | Medium | P1 |
| HR slot-filling workflow documentation | ~100 lines Markdown | Small | P0 |
| Slot manifest generator | ~80 Python | Small | P1 |
| Update pipeline validator for slots | ~50 Python (modification) | Small | P1 |
| **Total new code** | **~630 Python + ~480 YAML** | **Medium** | |

---

## 9. Comparison: What This Enables That the Prior Design Cannot

### 9.1 Scenario: Rapid Agent Iteration

**Prior design**: To try a different researcher, edit the pipeline YAML, change `role: SIG-001` to `role: STRAT-001`, re-validate.

**Pluggable design**: Keep the pipeline topology unchanged. Update slot-assignments.yaml. The pipeline definition itself never changes.

**Why this matters**: Pipeline topology is an architecture artifact (stable, reviewed, tested). Agent assignments are a personnel decision (frequent, context-dependent). They should be separate.

### 9.2 Scenario: Novel Pipeline for Unfamiliar Domain

**Prior design**: Architect writes a new pipeline template from scratch, manually specifying all roles.

**Pluggable design**: Architect designs the topology (slots + data flow). HR receives the slot manifest and researches what kind of agent each slot needs. The Architect never needs to know the details of agent prompts.

**Why this matters**: The Architect focuses on STRUCTURE. HR focuses on PEOPLE. Neither needs to understand the other's domain deeply.

### 9.3 Scenario: Multi-Scenario Pipeline Reuse

**Prior design**: The "standard-feature" template is used for all features. Different types of features require different templates.

**Pluggable design**: A single topology (e.g., `design -> research -> implement -> review -> approve`) serves many scenarios. The DIFFERENCE is which agents fill the slots. A security-focused feature uses a security researcher in the research slot. A UI feature uses a UX researcher in the research slot. Same topology, different plugs.

### 9.4 Scenario: Agent Quality Improvement

**Prior design**: To improve an agent, edit its .md file. Risk: the edited prompt may no longer fit the pipeline's expectations.

**Pluggable design**: To improve an agent, edit its .md file. As long as it still declares the same capabilities, it remains compatible with all pipelines that use those slot types. The pipeline engine validates compatibility.

---

## 10. Open Questions for CEO Decision

1. **Capability granularity**: How fine-grained should capabilities be? `["web_search"]` vs. `["web_search_market_data", "web_search_academic_papers"]`? Recommendation: start coarse, refine based on experience.

2. **Multi-agent slots**: Can a single slot be filled by MULTIPLE agents collaborating? (e.g., two researchers working in parallel within one research slot). Recommendation: model this as two separate slots of the same type, connected in parallel.

3. **Self-adaptive pipelines**: Should the pipeline be able to add/remove slots at runtime based on intermediate results? (e.g., "this requires extra research -- add another research slot"). Recommendation: defer to Phase 2. Start with static topologies.

4. **Slot type hierarchy**: Should there be inheritance? (e.g., `signal_researcher` IS-A `researcher`). Recommendation: use capability sets, not inheritance. A signal_researcher has `researcher` capabilities PLUS additional ones.

5. **HR automation**: Should capability matching be fully automated (HR produces .md, system auto-validates), or should HR explicitly declare compatibility? Recommendation: HR declares compatibility in the .md front-matter; system validates at pipeline startup.

---

## 11. References

### Multi-Agent Frameworks
1. LangGraph Agent Orchestration. https://www.langchain.com/langgraph
2. CrewAI Framework (role/goal/backstory YAML). https://docs.crewai.com/en/concepts/agents
3. Microsoft Agent Framework (AutoGen + Semantic Kernel merger). https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview
4. MetaGPT SOP-driven multi-agent. https://docs.deepwisdom.ai/main/en/guide/get_started/introduction.html
5. ChatDev communicative agents. https://github.com/OpenBMB/ChatDev
6. CAMEL role-playing framework. https://github.com/camel-ai/camel
7. AgentScope modular multi-agent platform. https://github.com/agentscope-ai/agentscope
8. OpenAI Swarm (educational). https://github.com/openai/swarm

### Inter-Agent Protocols
9. Google A2A (Agent-to-Agent) Protocol. https://a2a-protocol.org/latest/
10. Anthropic MCP (Model Context Protocol). https://modelcontextprotocol.io/specification/2025-11-25
11. A2A Protocol Specification v0.3 (gRPC + JSON-RPC). https://a2a-protocol.org/latest/specification/

### Orchestration Patterns
12. Azure AI Agent Design Patterns. https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns
13. Temporal Workflow Engine. https://github.com/temporalio/temporal
14. Confluent Event-Driven Multi-Agent Patterns. https://www.confluent.io/blog/event-driven-multi-agent-systems/
15. Blackboard Pattern for Multi-Agent Systems. https://medium.com/@dp2580/building-intelligent-multi-agent-systems-with-mcps-and-the-blackboard-pattern-to-build-systems-a454705d5672
16. LbMAS (Blackboard-based Multi-Agent LLM System). https://arxiv.org/html/2507.01701v1

### Claude Code Specific
17. Claude Code Sub-agents Documentation. https://code.claude.com/docs/en/sub-agents
18. Claude Code Agent Teams (experimental). VentureBeat, Feb 2026.
19. Claude Flow Agent Orchestration. https://github.com/ruvnet/claude-flow

### Design Patterns
20. CrewAI YAML Agent Configuration. https://docs.crewai.com/en/concepts/agents
21. Semantic Kernel Agent Orchestration Patterns. https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/
22. Google ADK Multi-Agent Patterns. https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/
23. Unix Pipe Philosophy & MCP. https://www.openlinksw.com/data/html/unix-mindset-pipes-mcp.html

### Workflow Engines
24. Airflow TaskFlow API. https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html
25. Prefect Workflow Orchestration. https://www.prefect.io/

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **Slot** | A typed placeholder in a pipeline that accepts any compatible agent |
| **SlotType** | The interface contract for a slot (input schema, output schema, required capabilities) |
| **Agent Definition** | The .md file that defines an agent's identity, capabilities, and behavior |
| **Topology** | The pipeline structure: slots + data flow + ordering + gates (without agent assignments) |
| **Slot Assignment** | The mapping from slot to agent (produced by HR, reviewed by CEO) |
| **Slot Protocol** | The standardized sequence: read input -> execute -> write output |
| **Capability** | A discrete skill an agent possesses (e.g., "web_search", "code_review") |
| **Slot Manifest** | The list of slots and their required capabilities, used by HR to fill the pipeline |

## Appendix B: Framework Feature Matrix (Extended)

| Feature | LangGraph | CrewAI | AutoGen/MAF | MetaGPT | ChatDev | CAMEL | AgentScope | A2A |
|---------|-----------|--------|-------------|---------|---------|-------|-----------|-----|
| Agent defined in config (not code) | No | **Yes (YAML)** | Partial | No | Partial (prompts) | **Yes (prompts)** | Partial | **Yes (Agent Cards)** |
| Typed agent I/O | **Yes (state channels)** | No | **Yes** | No | No | No | **Yes (messages)** | **Yes (Tasks)** |
| Pluggable agent swap | Medium | **High** | Medium | Low | Medium | **High** | **High** | **Highest** |
| Discovery by capability | No | No | Partial (A2A) | No | No | No | No | **Yes** |
| Pipeline as graph | **Yes** | No (sequential/hierarchical) | **Yes** | No (waterfall) | No (phases) | No (dyadic) | **Yes** | No (peer-to-peer) |
| Parallel execution | **Yes** | **Yes (hierarchical)** | **Yes** | No | No | No | **Yes** | N/A |
| Human-in-the-loop | **Yes** | **Yes** | **Yes** | No | No | No | **Yes** | N/A |
| Pre/post conditions | **Yes (conditional edges)** | No | **Yes** | Partial | No | No | Partial | N/A |
| State persistence | **Yes** | No | **Yes** | No | No | No | **Yes** | N/A |
