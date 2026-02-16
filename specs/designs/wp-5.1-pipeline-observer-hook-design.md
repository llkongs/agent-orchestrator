# WP-5.1: PipelineObserver Hook Design

> Author: ARCH-001
> Date: 2026-02-17
> Status: DESIGN COMPLETE
> For: ENG-001 (implementation), PMO-001 (interim compliance usage)
> Dependencies: `specs/pipelines/implementation-guide.md`, `specs/pipelines/schema.yaml`

---

## 1. Overview

The PipelineObserver is a **passive, non-blocking hook system** that allows external agents (compliance auditor, metrics collector, future dashboard) to observe pipeline execution events without being in the critical path.

**Design philosophy**: The observer pattern. Pipeline execution emits events; observers subscribe and react. Observers cannot delay, block, or veto pipeline steps.

**Key constraints**:
- No veto power: observers receive events but cannot reject steps
- No critical-path impact: observer failures are logged, not propagated
- File-based transport: events written as YAML, consistent with existing protocol
- Backward compatible: pipelines without observers work identically

---

## 2. Architecture

```
Pipeline Runner
    |
    |-- on_step_start(step_id, step, state)
    |-- on_step_complete(step_id, step, state, result)
    |-- on_step_fail(step_id, step, state, error)
    |-- on_gate_check(step_id, gate_type, results)
    |-- on_pipeline_start(pipeline, state)
    |-- on_pipeline_complete(pipeline, state)
    |-- on_pipeline_fail(pipeline, state, error)
    |
    v
PipelineObserver (abstract)
    |
    +-- ComplianceObserver     (writes event log for post-hoc audit)
    +-- MetricsObserver        (future: collects timing/throughput data)
    +-- DashboardObserver      (future: pushes status to dashboard)
```

---

## 3. Data Models

Add to `pipeline/models.py`:

```python
class PipelineEventType(StrEnum):
    PIPELINE_START = "pipeline_start"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_FAIL = "pipeline_fail"
    PIPELINE_PAUSE = "pipeline_pause"
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_FAIL = "step_fail"
    STEP_SKIP = "step_skip"
    STEP_RETRY = "step_retry"
    GATE_PRE_CHECK = "gate_pre_check"
    GATE_POST_CHECK = "gate_post_check"


@dataclass
class PipelineEvent:
    event_type: PipelineEventType
    pipeline_id: str
    timestamp: str                  # ISO 8601
    step_id: str | None = None      # None for pipeline-level events
    data: dict[str, Any] = field(default_factory=dict)
```

Impact: ~20 LOC addition to `models.py`.

---

## 4. Observer Interface

New file: `pipeline/observer.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod

from src.pipeline.models import (
    Pipeline,
    PipelineEvent,
    PipelineState,
    Step,
    GateCheckResult,
)


class PipelineObserver(ABC):
    """Abstract base class for pipeline execution observers.

    Observers are called synchronously during pipeline execution
    but MUST NOT raise exceptions or block for extended periods.
    Any exception from an observer is caught, logged, and ignored.

    Observers have read-only access to pipeline state.
    They cannot modify state or veto steps.
    """

    @abstractmethod
    def on_event(self, event: PipelineEvent) -> None:
        """Handle a pipeline event.

        This is the single entry point for all events.
        Implementations should dispatch based on event.event_type.

        MUST NOT raise exceptions.
        MUST NOT block for more than 1 second.
        MUST NOT modify pipeline state.
        """
        ...

    def on_pipeline_start(
        self, pipeline: Pipeline, state: PipelineState
    ) -> None:
        """Called when pipeline execution begins. Optional override."""
        pass

    def on_pipeline_complete(
        self, pipeline: Pipeline, state: PipelineState
    ) -> None:
        """Called when pipeline execution completes successfully."""
        pass

    def on_pipeline_fail(
        self, pipeline: Pipeline, state: PipelineState, error: str
    ) -> None:
        """Called when pipeline fails."""
        pass

    def on_step_start(
        self, step: Step, pipeline: Pipeline, state: PipelineState
    ) -> None:
        """Called when a step begins execution."""
        pass

    def on_step_complete(
        self, step: Step, pipeline: Pipeline, state: PipelineState
    ) -> None:
        """Called when a step completes successfully."""
        pass

    def on_step_fail(
        self, step: Step, pipeline: Pipeline, state: PipelineState, error: str
    ) -> None:
        """Called when a step fails."""
        pass

    def on_gate_check(
        self,
        step: Step,
        gate_type: str,  # "pre" or "post"
        results: list[GateCheckResult],
    ) -> None:
        """Called after gate conditions are evaluated."""
        pass
```

Impact: ~65 LOC new file.

---

## 5. Observer Registry in PipelineRunner

Modify `pipeline/runner.py` to support observers:

```python
class PipelineRunner:
    def __init__(
        self,
        project_root: str,
        templates_dir: str,
        state_dir: str,
    ):
        # ... existing init ...
        self._observers: list[PipelineObserver] = []

    def add_observer(self, observer: PipelineObserver) -> None:
        """Register a pipeline observer."""
        self._observers.append(observer)

    def remove_observer(self, observer: PipelineObserver) -> None:
        """Unregister a pipeline observer."""
        self._observers.remove(observer)

    def _notify(self, event: PipelineEvent) -> None:
        """Notify all observers of an event.

        Catches and logs any observer exceptions.
        Never propagates observer errors to the pipeline.
        """
        for observer in self._observers:
            try:
                observer.on_event(event)
            except Exception:
                # Log but never propagate
                pass
```

Impact: ~25 LOC addition to `runner.py`.

### Hook Points in Runner

Add `_notify()` calls at these points in existing runner methods:

| Method | Hook Point | Event Type |
|--------|-----------|------------|
| `prepare()` | After state init | `PIPELINE_START` |
| `execute_step()` pre-check | After pre-conditions run | `GATE_PRE_CHECK` |
| `execute_step()` start | When step begins | `STEP_START` |
| `execute_step()` post-check | After post-conditions run | `GATE_POST_CHECK` |
| `mark_step_complete()` | After status update | `STEP_COMPLETE` |
| `mark_step_failed()` | After status update | `STEP_FAIL` |
| `mark_step_skipped()` | After status update | `STEP_SKIP` |
| Pipeline complete check | When `is_complete()` is true | `PIPELINE_COMPLETE` |
| Pipeline fail | On unrecoverable error | `PIPELINE_FAIL` |

Impact: ~20 LOC of `_notify()` calls inserted at existing code points.

---

## 6. ComplianceObserver (First Implementation)

New file: `pipeline/compliance_observer.py`

```python
import yaml
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline.models import (
    PipelineEvent,
    PipelineEventType,
)
from src.pipeline.observer import PipelineObserver


class ComplianceObserver(PipelineObserver):
    """Writes pipeline events to an audit log for post-hoc compliance review.

    The compliance observer records all pipeline events to a YAML log file.
    This log is the primary input for the compliance auditor agent (or PMO
    when filling the auditor slot).

    Output: {log_dir}/{pipeline_id}-events.yaml

    The event log is append-only and never modified after writing.
    """

    def __init__(self, log_dir: str):
        """
        Args:
            log_dir: Directory for event log files.
                     Typically state/active/
        """
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict] = []
        self._pipeline_id: str | None = None

    def on_event(self, event: PipelineEvent) -> None:
        """Append event to in-memory log and flush to disk."""
        self._pipeline_id = event.pipeline_id

        entry = {
            "event_type": str(event.event_type),
            "pipeline_id": event.pipeline_id,
            "timestamp": event.timestamp,
            "step_id": event.step_id,
            "data": event.data,
        }
        self._events.append(entry)
        self._flush()

    def _flush(self) -> None:
        """Write event log to disk."""
        if not self._pipeline_id:
            return
        log_path = self._log_dir / f"{self._pipeline_id}-events.yaml"
        try:
            with open(log_path, "w") as f:
                yaml.safe_dump(
                    {"events": self._events},
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                )
        except OSError:
            pass  # Observer must never raise

    def get_log_path(self) -> str | None:
        """Return path to the event log file."""
        if self._pipeline_id:
            return str(self._log_dir / f"{self._pipeline_id}-events.yaml")
        return None
```

Impact: ~55 LOC new file.

---

## 7. Event Log Format

```yaml
# {pipeline_id}-events.yaml
events:
  - event_type: "pipeline_start"
    pipeline_id: "standard-feature"
    timestamp: "2026-02-17T10:00:00+00:00"
    step_id: null
    data:
      pipeline_name: "Standard Feature Development"
      total_steps: 5

  - event_type: "step_start"
    pipeline_id: "standard-feature"
    timestamp: "2026-02-17T10:00:05+00:00"
    step_id: "architect-design"
    data:
      step_name: "Architecture Design"
      role: "ARCH-001"

  - event_type: "gate_pre_check"
    pipeline_id: "standard-feature"
    timestamp: "2026-02-17T10:00:06+00:00"
    step_id: "architect-design"
    data:
      gate_type: "pre"
      results:
        - condition: "Integration contract exists"
          passed: true
          evidence: "File exists: specs/integration-contract.md"

  - event_type: "step_complete"
    pipeline_id: "standard-feature"
    timestamp: "2026-02-17T12:15:00+00:00"
    step_id: "architect-design"
    data:
      step_name: "Architecture Design"
      duration_minutes: 135
```

---

## 8. Integration with Existing Schema

### 8.1 schema.yaml Addition

Add to `state_schema.status.enum`:

```yaml
status:
  enum: ["loaded", "validated", "running", "paused", "completed", "failed", "aborted", "auditing"]
```

The `auditing` state is entered after `completed` when an auditor slot exists in the pipeline.

### 8.2 PipelineStatus Enum Addition

Add to `models.py` `PipelineStatus`:

```python
class PipelineStatus(StrEnum):
    LOADED = "loaded"
    VALIDATED = "validated"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    AUDITING = "auditing"      # NEW: post-completion audit in progress
    FAILED = "failed"
    ABORTED = "aborted"
```

### 8.3 StepType Addition

Add to `models.py` `StepType`:

```python
class StepType(StrEnum):
    # ... existing ...
    COMPLIANCE_AUDIT = "compliance_audit"  # NEW: post-pipeline audit step
```

---

## 9. Total Implementation Impact

| File | Change Type | Estimated LOC |
|------|------------|---------------|
| `pipeline/models.py` | Add `PipelineEvent`, `PipelineEventType`, update enums | ~25 |
| `pipeline/observer.py` | New file: abstract observer base class | ~65 |
| `pipeline/compliance_observer.py` | New file: event log writer | ~55 |
| `pipeline/runner.py` | Add observer registry + `_notify()` calls | ~45 |
| **Total** | | **~190** |

### Test Files

| File | Tests |
|------|-------|
| `tests/test_pipeline/test_observer.py` | ~8 tests (event dispatch, error isolation, multiple observers) |
| `tests/test_pipeline/test_compliance_observer.py` | ~6 tests (event log write, flush, format, error handling) |

---

## 10. Usage Example

```python
from src.pipeline import PipelineRunner
from src.pipeline.compliance_observer import ComplianceObserver

runner = PipelineRunner(
    project_root="/path/to/project",
    templates_dir="/path/to/templates",
    state_dir="/path/to/active",
)

# Attach compliance observer
compliance = ComplianceObserver(log_dir="/path/to/state/active")
runner.add_observer(compliance)

# Execute pipeline (observer records all events automatically)
pipeline, state = runner.prepare("templates/standard-feature.yaml", params)

# ... pipeline execution ...

# After pipeline completes, the event log is at:
print(compliance.get_log_path())
# -> /path/to/state/active/standard-feature-events.yaml
# This file is the input for the compliance audit step
```
