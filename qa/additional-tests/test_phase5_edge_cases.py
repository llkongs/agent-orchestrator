"""Supplementary edge-case tests for Phase 5: Observer + AUDITING.

These tests cover:
- PipelineObserver ABC enforcement
- ComplianceObserver error resilience
- Observer failure isolation in runner
- AUDITING state transition edge cases
- PipelineStatus enum completeness
- nl_matcher compliance-audit keyword matching
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.models import (
    GateCheckResult,
    Pipeline,
    PipelineObserver,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotState,
    SlotStatus,
    SlotTask,
)
from pipeline.observer import ComplianceObserver
from pipeline.runner import PipelineExecutionError, PipelineRunner


class TestPipelineObserverABC:
    """Verify PipelineObserver cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError, match="abstract method"):
            PipelineObserver()  # type: ignore

    def test_partial_implementation_raises(self):
        class PartialObserver(PipelineObserver):
            def on_pipeline_started(self, pipeline_id, state):
                pass

        with pytest.raises(TypeError, match="abstract method"):
            PartialObserver()  # type: ignore

    def test_complete_implementation_works(self):
        class FullObserver(PipelineObserver):
            def on_pipeline_started(self, pipeline_id, state): pass
            def on_pipeline_completed(self, pipeline_id, state): pass
            def on_pipeline_failed(self, pipeline_id, state, error): pass
            def on_slot_started(self, pipeline_id, slot_id, agent_id): pass
            def on_slot_completed(self, pipeline_id, slot_id): pass
            def on_slot_failed(self, pipeline_id, slot_id, error): pass
            def on_gate_check_completed(self, pipeline_id, slot_id, gate_type, results): pass
            def on_status_changed(self, pipeline_id, old_status, new_status): pass

        obs = FullObserver()
        assert isinstance(obs, PipelineObserver)


class TestComplianceObserverEdgeCases:
    """Edge cases for ComplianceObserver."""

    def test_write_to_nonexistent_nested_dir(self, tmp_path):
        nested = str(tmp_path / "a" / "b" / "c")
        obs = ComplianceObserver(nested)
        state = MagicMock()
        state.status = PipelineStatus.RUNNING
        state.slots = {}
        obs.on_pipeline_started("test-pipe", state)
        log_file = Path(nested) / "test-pipe.events.yaml"
        assert log_file.exists()

    def test_write_to_readonly_dir_does_not_raise(self, tmp_path):
        readonly = tmp_path / "readonly"
        readonly.mkdir()
        os.chmod(str(readonly), 0o444)
        obs = ComplianceObserver(str(readonly))
        state = MagicMock()
        state.status = PipelineStatus.RUNNING
        state.slots = {}
        # Should not raise -- observer failures are caught
        obs.on_pipeline_started("test-pipe", state)
        os.chmod(str(readonly), 0o755)  # cleanup

    def test_multiple_events_append(self, tmp_path):
        obs = ComplianceObserver(str(tmp_path))
        state = MagicMock()
        state.status = PipelineStatus.RUNNING
        state.slots = {}
        obs.on_pipeline_started("pipe-1", state)
        obs.on_slot_started("pipe-1", "slot-a", "ENG-001")
        obs.on_slot_completed("pipe-1", "slot-a")
        log_file = tmp_path / "pipe-1.events.yaml"
        content = log_file.read_text()
        assert content.count("---") == 3  # 3 events = 3 separators

    def test_gate_check_with_empty_results(self, tmp_path):
        obs = ComplianceObserver(str(tmp_path))
        obs.on_gate_check_completed("pipe-1", "slot-a", "pre", [])
        log_file = tmp_path / "pipe-1.events.yaml"
        content = log_file.read_text()
        assert "passed: true" in content  # all([]) == True


class TestAuditingStateTransition:
    """Edge cases for AUDITING state."""

    def test_auditing_in_pipeline_status_enum(self):
        assert hasattr(PipelineStatus, "AUDITING")
        assert PipelineStatus.AUDITING.value == "auditing"

    def test_pipeline_status_has_8_values(self):
        assert len(PipelineStatus) == 8

    def test_start_auditing_from_non_completed_raises(self):
        runner = PipelineRunner.__new__(PipelineRunner)
        runner._state_tracker = MagicMock()
        runner._observers = []
        state = MagicMock()
        state.status = PipelineStatus.RUNNING
        with pytest.raises(PipelineExecutionError, match="Cannot start auditing"):
            runner.start_auditing(state)

    def test_start_auditing_from_failed_raises(self):
        runner = PipelineRunner.__new__(PipelineRunner)
        runner._state_tracker = MagicMock()
        runner._observers = []
        state = MagicMock()
        state.status = PipelineStatus.FAILED
        with pytest.raises(PipelineExecutionError, match="Cannot start auditing"):
            runner.start_auditing(state)


class TestObserverFailureIsolation:
    """Verify observer exceptions never propagate to pipeline."""

    def test_failing_observer_does_not_crash_notify(self):
        runner = PipelineRunner.__new__(PipelineRunner)

        class BrokenObserver(PipelineObserver):
            def on_pipeline_started(self, *a): raise RuntimeError("boom")
            def on_pipeline_completed(self, *a): raise RuntimeError("boom")
            def on_pipeline_failed(self, *a, **kw): raise RuntimeError("boom")
            def on_slot_started(self, *a): raise RuntimeError("boom")
            def on_slot_completed(self, *a): raise RuntimeError("boom")
            def on_slot_failed(self, *a): raise RuntimeError("boom")
            def on_gate_check_completed(self, *a): raise RuntimeError("boom")
            def on_status_changed(self, *a): raise RuntimeError("boom")

        runner._observers = [BrokenObserver()]
        # _notify should catch the exception, not propagate it
        runner._notify("on_pipeline_started", "pipe-1", MagicMock())
        runner._notify("on_status_changed", "pipe-1", PipelineStatus.RUNNING, PipelineStatus.COMPLETED)

    def test_multiple_observers_one_fails(self):
        runner = PipelineRunner.__new__(PipelineRunner)
        good = MagicMock()

        class BadObserver(PipelineObserver):
            def on_pipeline_started(self, *a): raise ValueError("fail")
            def on_pipeline_completed(self, *a): pass
            def on_pipeline_failed(self, *a, **kw): pass
            def on_slot_started(self, *a): pass
            def on_slot_completed(self, *a): pass
            def on_slot_failed(self, *a): pass
            def on_gate_check_completed(self, *a): pass
            def on_status_changed(self, *a): pass

        runner._observers = [BadObserver(), good]
        runner._notify("on_pipeline_started", "pipe-1", MagicMock())
        # Good observer should still be called even though bad one raised
        good.on_pipeline_started.assert_called_once()


class TestNLMatcherComplianceAudit:
    """Verify compliance-audit template matching."""

    @pytest.fixture
    def matcher_with_compliance(self, tmp_path):
        import yaml
        from pipeline.nl_matcher import NLMatcher
        (tmp_path / "compliance-audit.yaml").write_text(
            yaml.dump({
                "pipeline": {
                    "id": "compliance-audit",
                    "name": "Compliance Audit",
                    "description": "PPQA compliance audit pipeline",
                    "version": "1.0.0",
                    "created_by": "test",
                    "created_at": "2026-01-01",
                }
            })
        )
        return NLMatcher(str(tmp_path))

    def test_compliance_audit_english(self, matcher_with_compliance):
        matches = matcher_with_compliance.match("Run compliance audit on this pipeline")
        template_ids = [m.template_id for m in matches]
        assert "compliance-audit" in template_ids

    def test_compliance_audit_chinese(self, matcher_with_compliance):
        matches = matcher_with_compliance.match("对这个流程进行合规审计")
        template_ids = [m.template_id for m in matches]
        assert "compliance-audit" in template_ids
