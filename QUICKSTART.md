# Pipeline Engine -- Quick Start

## Dependencies

- Python >= 3.11
- PyYAML >= 6.0

```bash
pip install pyyaml
```

## Directory Layout

```
agent-orchestrator/
  engineer/src/pipeline/   # Engine source code
  specs/pipelines/
    templates/             # Pipeline YAML templates
    slot-types/            # Slot type definitions
  agents/                  # Agent .md files with YAML front-matter
```

## Quick Start

```bash
cd /mnt/nvme0n1/Projects/agent-orchestrator/engineer
export PYTHONPATH=src
python3 -c "from pipeline import PipelineRunner; print('OK')"
```

## API: PipelineRunner

```python
import sys
sys.path.insert(0, "/mnt/nvme0n1/Projects/agent-orchestrator/engineer/src")

from pipeline import PipelineRunner

PROJECT_ROOT = "/mnt/nvme0n1/Projects/agent-orchestrator"

runner = PipelineRunner(
    project_root=PROJECT_ROOT,
    templates_dir=f"{PROJECT_ROOT}/specs/pipelines/templates",
    state_dir=f"{PROJECT_ROOT}/state/active",
    slot_types_dir=f"{PROJECT_ROOT}/specs/pipelines/slot-types",
    agents_dir=f"{PROJECT_ROOT}/agents",
)
```

### Lifecycle

```python
# 1. Prepare -- load template, resolve params, validate, init state
pipeline, state = runner.prepare(
    f"{PROJECT_ROOT}/specs/pipelines/templates/research-task.yaml",
    {"research_topic": "websocket-optimization", "research_brief": "Evaluate options for reducing WS latency"}
)

# 2. Get next executable slots
next_slots = runner.get_next_slots(pipeline, state)
print([s.id for s in next_slots])  # ['research']

# 3. Begin a slot (checks pre-conditions, sets IN_PROGRESS)
state = runner.begin_slot(next_slots[0], pipeline, state, agent_id="RES-001")

# 4. ... agent does work externally ...

# 5. Complete slot (checks post-conditions, sets COMPLETED)
state = runner.complete_slot("research", pipeline, state)

# 6. Get next slots (now unblocked)
next_slots = runner.get_next_slots(pipeline, state)
print([s.id for s in next_slots])  # ['architect-review']

# 7. Print summary
print(runner.get_summary(state))
```

### Other Operations

```python
# Skip a slot (CEO decision)
state = runner.skip_slot("ceo-decision", state)

# Fail a slot manually
state = runner.fail_slot("research", "Agent crashed", state)

# Resume from saved state
pipeline, state = runner.resume_with_pipeline(
    "/path/to/state.yaml",
    f"{PROJECT_ROOT}/specs/pipelines/templates/research-task.yaml",
    {"research_topic": "websocket-optimization", "research_brief": "..."}
)
```

## NL Matcher -- Match Natural Language to Templates

```python
from pipeline import NLMatcher

matcher = NLMatcher(f"{PROJECT_ROOT}/specs/pipelines/templates")

# English
results = matcher.match("I want to research websocket performance")
for r in results:
    print(f"{r.template_id} (confidence={r.confidence})")
# research-task (confidence=0.273)

# Chinese
results = matcher.match("开发一个新功能实现K线聚合")
print(results[0].template_id)  # standard-feature

# Extract parameters from text
params = matcher.extract_params(
    "implement feature kline-aggregator in phase5", "standard-feature"
)
print(params)
# {'feature_name': 'kline-aggregator', 'phase_id': 'phase5'}

# Generate human-readable summary
summary = matcher.generate_summary(results[0], params)
print(summary)
```

## Full Example: Run research-task Pipeline

```python
#!/usr/bin/env python3
"""Run a research-task pipeline end-to-end."""

import sys, os
sys.path.insert(0, "/mnt/nvme0n1/Projects/agent-orchestrator/engineer/src")

from pipeline import PipelineRunner

ROOT = "/mnt/nvme0n1/Projects/agent-orchestrator"

# Ensure state directory exists
os.makedirs(f"{ROOT}/state/active", exist_ok=True)

runner = PipelineRunner(
    project_root=ROOT,
    templates_dir=f"{ROOT}/specs/pipelines/templates",
    state_dir=f"{ROOT}/state/active",
    slot_types_dir=f"{ROOT}/specs/pipelines/slot-types",
    agents_dir=f"{ROOT}/agents",
)

# Prepare
pipeline, state = runner.prepare(
    f"{ROOT}/specs/pipelines/templates/research-task.yaml",
    {
        "research_topic": "websocket-optimization",
        "research_brief": "Evaluate WebSocket libraries for lower latency",
    },
)
print(runner.get_summary(state))
print()

# Execute slot by slot
while True:
    next_slots = runner.get_next_slots(pipeline, state)
    if not next_slots:
        print("No more executable slots.")
        break

    for slot in next_slots:
        print(f">> Starting: {slot.id} ({slot.slot_type})")
        state = runner.begin_slot(slot, pipeline, state, agent_id="SIMULATED")

        # Simulate agent work here...

        state = runner.complete_slot(slot.id, pipeline, state)
        print(f">> Completed: {slot.id}")

print()
print(runner.get_summary(state))
```

## Available Templates

| Template | Description | Required Parameters |
|---|---|---|
| `standard-feature.yaml` | Feature development end-to-end | `feature_name`, `phase_id` |
| `research-task.yaml` | Research and investigation | `research_topic`, `research_brief` |
| `hotfix.yaml` | Emergency bug fix | `bug_id`, `bug_description` |
| `quant-strategy.yaml` | Quant trading strategy | `strategy_name`, `target_symbol` |
| `security-hardening.yaml` | Security audit and hardening | `audit_scope` |

## Running Tests

```bash
cd /mnt/nvme0n1/Projects/agent-orchestrator/engineer
PYTHONPATH=src python3 -m pytest tests/test_pipeline/ -v --cov=src/pipeline --cov-report=term-missing
# 270 passed, 97% coverage
```
