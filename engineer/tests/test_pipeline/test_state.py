"""Tests for pipeline.state -- state tracking and persistence."""

import pytest
from pathlib import Path

from src.pipeline.state import PipelineStateTracker
from src.pipeline.models import (
    DataFlowEdge,
    GateCheckResult,
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotState,
    SlotStatus,
    SlotTask,
    ArtifactOutput,
)


class TestInitState:
    def test_all_slots_pending(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {"feature": "test"})
        assert len(state.slots) == 2
        for ss in state.slots.values():
            assert ss.status == SlotStatus.PENDING

    def test_definition_hash_set(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        assert state.definition_hash.startswith("sha256:")
        assert len(state.definition_hash) > 10

    def test_parameters_stored(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {"feature": "kline"})
        assert state.parameters["feature"] == "kline"

    def test_state_file_created(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        tracker.init_state(sample_pipeline, {})
        files = list(state_dir.glob("*.state.yaml"))
        assert len(files) == 1

    def test_pipeline_id_in_state(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        assert state.pipeline_id == "test-pipeline"
        assert state.pipeline_version == "1.0.0"


class TestUpdateSlot:
    def test_update_status(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        assert state.slots["slot-design"].status == SlotStatus.IN_PROGRESS

    def test_started_at_set_on_in_progress(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        assert state.slots["slot-design"].started_at is not None

    def test_completed_at_set_on_completed(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        assert state.slots["slot-design"].completed_at is not None

    def test_completed_at_set_on_failed(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(
            state, "slot-design", SlotStatus.FAILED, error="Something broke"
        )
        assert state.slots["slot-design"].completed_at is not None
        assert state.slots["slot-design"].error == "Something broke"

    def test_agent_assignment(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(
            state, "slot-design", SlotStatus.IN_PROGRESS,
            agent_id="ARCH-001", agent_prompt="agents/01-architect-agent.md",
        )
        assert state.slots["slot-design"].agent_id == "ARCH-001"
        assert state.slots["slot-design"].agent_prompt == "agents/01-architect-agent.md"

    def test_pre_check_results(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        result = GateCheckResult(
            condition="File exists", passed=True,
            evidence="Found", checked_at="2026-01-01T00:00:00Z",
        )
        state = tracker.update_slot(
            state, "slot-design", SlotStatus.PRE_CHECK,
            pre_check_results=[result],
        )
        assert len(state.slots["slot-design"].pre_check_results) == 1

    def test_unknown_slot_raises(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        with pytest.raises(KeyError, match="nonexistent"):
            tracker.update_slot(state, "nonexistent", SlotStatus.IN_PROGRESS)


class TestGetReadySlots:
    def test_initial_ready(self, sample_pipeline, state_dir):
        """Slots with no dependencies are ready initially."""
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        ready = tracker.get_ready_slots(sample_pipeline, state)
        assert "slot-design" in ready
        assert "slot-implement" not in ready

    def test_after_completion(self, sample_pipeline, state_dir):
        """Dependent slots become ready when deps complete."""
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        ready = tracker.get_ready_slots(sample_pipeline, state)
        assert "slot-implement" in ready

    def test_blocked_when_deps_incomplete(self, sample_pipeline, state_dir):
        """Dependent slots stay blocked when deps are in progress."""
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        ready = tracker.get_ready_slots(sample_pipeline, state)
        assert "slot-implement" not in ready

    def test_data_flow_dependency(self, state_dir):
        """Slots also check data_flow source slots."""
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[
                Slot(
                    id="src", slot_type="x", name="Source",
                    outputs=[ArtifactOutput(name="artifact", type="code")],
                ),
                Slot(id="dst", slot_type="x", name="Dest"),
            ],
            data_flow=[
                DataFlowEdge(from_slot="src", to_slot="dst", artifact="artifact"),
            ],
        )
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(pipeline, {})
        ready = tracker.get_ready_slots(pipeline, state)
        assert "src" in ready
        assert "dst" not in ready

        state = tracker.update_slot(state, "src", SlotStatus.COMPLETED)
        ready = tracker.get_ready_slots(pipeline, state)
        assert "dst" in ready


class TestIsComplete:
    def test_not_complete_initially(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        assert tracker.is_complete(state) is False

    def test_complete_all_completed(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        state = tracker.update_slot(state, "slot-implement", SlotStatus.COMPLETED)
        assert tracker.is_complete(state) is True

    def test_complete_with_skipped(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        state = tracker.update_slot(state, "slot-implement", SlotStatus.SKIPPED)
        assert tracker.is_complete(state) is True

    def test_complete_with_failed(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.FAILED)
        state = tracker.update_slot(state, "slot-implement", SlotStatus.SKIPPED)
        assert tracker.is_complete(state) is True


class TestGetStatusSummary:
    def test_summary_structure(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        summary = tracker.get_status_summary(state)
        assert summary["pipeline_id"] == "test-pipeline"
        assert "progress" in summary
        assert summary["progress"] == "0/2 slots completed"

    def test_summary_after_completion(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        summary = tracker.get_status_summary(state)
        assert "slot-design" in summary["completed"]
        assert summary["progress"] == "1/2 slots completed"


class TestSaveLoad:
    def test_save_returns_path(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        path = tracker.save(state)
        assert Path(path).exists()

    def test_load_roundtrip(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        path = tracker.save(state)

        tracker2 = PipelineStateTracker(str(state_dir))
        loaded = tracker2.load(path)
        assert loaded.pipeline_id == state.pipeline_id
        assert loaded.definition_hash == state.definition_hash
        assert loaded.slots["slot-design"].status == SlotStatus.COMPLETED

    def test_load_missing_file(self, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        with pytest.raises(FileNotFoundError):
            tracker.load("/nonexistent/state.yaml")


class TestArchive:
    def test_archive_moves_file(self, sample_pipeline, state_dir, tmp_path):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})

        archive_path = tracker.archive(state)
        assert "archive" in archive_path
        assert Path(archive_path).exists()
        # Original should not exist
        active_files = list(state_dir.glob("*.state.yaml"))
        assert len(active_files) == 0
