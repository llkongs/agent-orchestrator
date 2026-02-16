"""Tests for pipeline.observer -- ComplianceObserver event logging."""

import yaml
import pytest

from pipeline.models import (
    GateCheckResult,
    PipelineObserver,
    PipelineState,
    PipelineStatus,
    SlotState,
    SlotStatus,
)
from pipeline.observer import ComplianceObserver


@pytest.fixture
def log_dir(tmp_path):
    """Temp directory for compliance event logs."""
    d = tmp_path / "compliance-logs"
    d.mkdir()
    return d


@pytest.fixture
def observer(log_dir):
    return ComplianceObserver(str(log_dir))


@pytest.fixture
def sample_state():
    return PipelineState(
        pipeline_id="test-pipe",
        pipeline_version="1.0.0",
        definition_hash="sha256:abc",
        status=PipelineStatus.RUNNING,
        slots={
            "slot-a": SlotState(slot_id="slot-a", status=SlotStatus.COMPLETED),
            "slot-b": SlotState(slot_id="slot-b", status=SlotStatus.IN_PROGRESS),
        },
    )


def _read_events(log_dir, pipeline_id="test-pipe"):
    """Read all YAML events from the log file."""
    log_path = log_dir / f"{pipeline_id}.events.yaml"
    if not log_path.exists():
        return []
    content = log_path.read_text(encoding="utf-8")
    return list(yaml.safe_load_all(content))


# ===================================================================
# ComplianceObserver is a PipelineObserver
# ===================================================================


class TestComplianceObserverIsObserver:
    def test_isinstance(self, observer):
        assert isinstance(observer, PipelineObserver)

    def test_all_abstract_methods_implemented(self, observer):
        for method_name in PipelineObserver.__abstractmethods__:
            assert hasattr(observer, method_name)
            assert callable(getattr(observer, method_name))


# ===================================================================
# Event writing -- individual lifecycle events
# ===================================================================


class TestOnPipelineStarted:
    def test_writes_event(self, observer, log_dir, sample_state):
        observer.on_pipeline_started("test-pipe", sample_state)
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "pipeline_started"
        assert events[0]["pipeline_id"] == "test-pipe"
        assert events[0]["status"] == "running"
        assert events[0]["slot_count"] == 2
        assert "timestamp" in events[0]


class TestOnPipelineCompleted:
    def test_writes_event(self, observer, log_dir, sample_state):
        sample_state.status = PipelineStatus.COMPLETED
        observer.on_pipeline_completed("test-pipe", sample_state)
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "pipeline_completed"
        assert events[0]["status"] == "completed"


class TestOnPipelineFailed:
    def test_writes_event(self, observer, log_dir, sample_state):
        sample_state.status = PipelineStatus.FAILED
        observer.on_pipeline_failed("test-pipe", sample_state, "slot-b crashed")
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "pipeline_failed"
        assert events[0]["error"] == "slot-b crashed"


class TestOnSlotStarted:
    def test_writes_event(self, observer, log_dir):
        observer.on_slot_started("test-pipe", "slot-a", "ENG-001")
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "slot_started"
        assert events[0]["slot_id"] == "slot-a"
        assert events[0]["agent_id"] == "ENG-001"

    def test_null_agent(self, observer, log_dir):
        observer.on_slot_started("test-pipe", "slot-a", None)
        events = _read_events(log_dir)
        assert events[0]["agent_id"] == ""


class TestOnSlotCompleted:
    def test_writes_event(self, observer, log_dir):
        observer.on_slot_completed("test-pipe", "slot-a")
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "slot_completed"
        assert events[0]["slot_id"] == "slot-a"


class TestOnSlotFailed:
    def test_writes_event(self, observer, log_dir):
        observer.on_slot_failed("test-pipe", "slot-a", "timeout")
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "slot_failed"
        assert events[0]["error"] == "timeout"


class TestOnGateCheckCompleted:
    def test_writes_event_all_passed(self, observer, log_dir):
        results = [
            GateCheckResult(
                condition="File exists",
                passed=True,
                evidence="found",
                checked_at="2026-01-01T00:00:00Z",
            ),
        ]
        observer.on_gate_check_completed("test-pipe", "slot-a", "pre", results)
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "gate_check_completed"
        assert events[0]["gate_type"] == "pre"
        assert events[0]["passed"] is True
        assert events[0]["result_count"] == 1

    def test_writes_event_some_failed(self, observer, log_dir):
        results = [
            GateCheckResult(
                condition="Check A", passed=True,
                evidence="ok", checked_at="2026-01-01T00:00:00Z",
            ),
            GateCheckResult(
                condition="Check B", passed=False,
                evidence="missing", checked_at="2026-01-01T00:00:00Z",
            ),
        ]
        observer.on_gate_check_completed("test-pipe", "slot-a", "post", results)
        events = _read_events(log_dir)
        assert events[0]["passed"] is False
        assert events[0]["result_count"] == 2


class TestOnStatusChanged:
    def test_writes_event(self, observer, log_dir):
        observer.on_status_changed(
            "test-pipe", PipelineStatus.LOADED, PipelineStatus.RUNNING
        )
        events = _read_events(log_dir)
        assert len(events) == 1
        assert events[0]["event"] == "status_changed"
        assert events[0]["old_status"] == "loaded"
        assert events[0]["new_status"] == "running"


# ===================================================================
# Append-only behavior
# ===================================================================


class TestAppendOnly:
    def test_multiple_events_appended(self, observer, log_dir, sample_state):
        observer.on_pipeline_started("test-pipe", sample_state)
        observer.on_slot_started("test-pipe", "slot-a", "ENG-001")
        observer.on_slot_completed("test-pipe", "slot-a")
        events = _read_events(log_dir)
        assert len(events) == 3
        assert events[0]["event"] == "pipeline_started"
        assert events[1]["event"] == "slot_started"
        assert events[2]["event"] == "slot_completed"

    def test_all_events_have_timestamps(self, observer, log_dir, sample_state):
        observer.on_pipeline_started("test-pipe", sample_state)
        observer.on_slot_started("test-pipe", "slot-a", "ENG-001")
        events = _read_events(log_dir)
        for event in events:
            assert "timestamp" in event
            assert "T" in event["timestamp"]  # ISO 8601 contains T


# ===================================================================
# File creation and directory handling
# ===================================================================


class TestFileHandling:
    def test_creates_log_dir_if_missing(self, tmp_path):
        log_dir = tmp_path / "new" / "nested" / "dir"
        obs = ComplianceObserver(str(log_dir))
        state = PipelineState(
            pipeline_id="p", pipeline_version="1.0",
            definition_hash="h", status=PipelineStatus.RUNNING,
        )
        obs.on_pipeline_started("p", state)
        assert log_dir.exists()
        events = _read_events(log_dir, "p")
        assert len(events) == 1

    def test_separate_files_per_pipeline(self, observer, log_dir, sample_state):
        state_b = PipelineState(
            pipeline_id="pipe-b", pipeline_version="1.0",
            definition_hash="h", status=PipelineStatus.RUNNING,
        )
        observer.on_pipeline_started("test-pipe", sample_state)
        observer.on_pipeline_started("pipe-b", state_b)

        events_a = _read_events(log_dir, "test-pipe")
        events_b = _read_events(log_dir, "pipe-b")
        assert len(events_a) == 1
        assert len(events_b) == 1
        assert events_a[0]["pipeline_id"] == "test-pipe"
        assert events_b[0]["pipeline_id"] == "pipe-b"


# ===================================================================
# Error resilience -- observer failures must never propagate
# ===================================================================


class TestErrorResilience:
    def test_unwritable_dir_does_not_raise(self, tmp_path):
        """Observer logs a warning but does not raise on write failure."""
        # Use a path that cannot be created (file as parent)
        blocker = tmp_path / "blocker"
        blocker.write_text("I am a file, not a dir")
        obs = ComplianceObserver(str(blocker / "subdir"))

        # This should NOT raise even though the directory creation will fail
        obs.on_slot_completed("pipe", "slot-a")
        # If we get here, the observer correctly swallowed the error
