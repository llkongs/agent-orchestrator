"""Tests for pipeline.state -- state tracking and persistence."""

import os
from unittest.mock import patch

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
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
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
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
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

        state = tracker.update_slot(state, "src", SlotStatus.IN_PROGRESS)
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
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        state = tracker.update_slot(state, "slot-implement", SlotStatus.IN_PROGRESS)
        state = tracker.update_slot(state, "slot-implement", SlotStatus.COMPLETED)
        assert tracker.is_complete(state) is True

    def test_complete_with_skipped(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
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
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
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
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
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


# ===================================================================
# Phase 1 Bug Fix Tests
# ===================================================================


class TestAtomicWriteDoublClose:
    """Bug 1: Atomic write should not double-close fd on rename failure."""

    def test_no_double_close_on_rename_failure(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        with patch("os.rename", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                tracker.save(state)

    def test_tmp_file_cleaned_on_rename_failure(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        with patch("os.rename", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                tracker.save(state)
        tmp_files = list(state_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_fd_closed_before_rename(self, sample_pipeline, state_dir):
        """After successful write+close, rename failure should not try to close again."""
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        close_calls = []
        original_close = os.close

        def tracking_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        with patch("os.close", side_effect=tracking_close):
            with patch("os.rename", side_effect=OSError("fail")):
                with pytest.raises(OSError):
                    tracker.save(state)

        # fd should be closed exactly once (in the try block), not twice
        assert len(close_calls) == 1


class TestGateCheckResultsSaveLoad:
    """Bug 2: Gate check results must survive save/load roundtrip."""

    def test_pre_check_results_roundtrip(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        result = GateCheckResult(
            condition="File exists: design.md",
            passed=True,
            evidence="Found at /tmp/design.md",
            checked_at="2026-01-01T00:00:00Z",
        )
        state = tracker.update_slot(
            state, "slot-design", SlotStatus.PRE_CHECK,
            pre_check_results=[result],
        )
        path = tracker.save(state)

        tracker2 = PipelineStateTracker(str(state_dir))
        loaded = tracker2.load(path)
        assert len(loaded.slots["slot-design"].pre_check_results) == 1
        r = loaded.slots["slot-design"].pre_check_results[0]
        assert r.condition == "File exists: design.md"
        assert r.passed is True
        assert r.evidence == "Found at /tmp/design.md"

    def test_post_check_results_roundtrip(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        results = [
            GateCheckResult(
                condition="Tests pass", passed=True,
                evidence="312 passed", checked_at="2026-01-01T00:00:00Z",
            ),
            GateCheckResult(
                condition="Coverage", passed=False,
                evidence="85% < 90%", checked_at="2026-01-01T00:00:01Z",
            ),
        ]
        state = tracker.update_slot(
            state, "slot-design", SlotStatus.IN_PROGRESS,
        )
        state = tracker.update_slot(
            state, "slot-design", SlotStatus.POST_CHECK,
            post_check_results=results,
        )
        path = tracker.save(state)

        tracker2 = PipelineStateTracker(str(state_dir))
        loaded = tracker2.load(path)
        post = loaded.slots["slot-design"].post_check_results
        assert len(post) == 2
        assert post[0].passed is True
        assert post[1].passed is False

    def test_empty_check_results_roundtrip(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        path = tracker.save(state)

        tracker2 = PipelineStateTracker(str(state_dir))
        loaded = tracker2.load(path)
        assert loaded.slots["slot-design"].pre_check_results == []
        assert loaded.slots["slot-design"].post_check_results == []


class TestUpdatePipelineStatus:
    """Bug 3+4: Pipeline status via state_tracker with timestamps."""

    def test_started_at_set_on_running(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        assert state.started_at is None
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        assert state.status == PipelineStatus.RUNNING
        assert state.started_at is not None

    def test_started_at_not_overwritten(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        first_started = state.started_at
        # Calling again should not overwrite
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        assert state.started_at == first_started

    def test_completed_at_set_on_completed(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        state = tracker.update_pipeline_status(state, PipelineStatus.COMPLETED)
        assert state.completed_at is not None

    def test_completed_at_set_on_failed(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        state = tracker.update_pipeline_status(state, PipelineStatus.FAILED)
        assert state.completed_at is not None

    def test_completed_at_set_on_aborted(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        state = tracker.update_pipeline_status(state, PipelineStatus.ABORTED)
        assert state.completed_at is not None


class TestSkippedDependencyUnblocks:
    """Bug 5: SKIPPED dependencies should unblock downstream slots."""

    def test_skipped_dep_unblocks_dependent(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.SKIPPED)
        ready = tracker.get_ready_slots(sample_pipeline, state)
        assert "slot-implement" in ready

    def test_skipped_data_flow_source_unblocks(self, state_dir):
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
        state = tracker.update_slot(state, "src", SlotStatus.SKIPPED)
        ready = tracker.get_ready_slots(pipeline, state)
        assert "dst" in ready

    def test_mixed_completed_and_skipped(self, state_dir):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[
                Slot(id="a", slot_type="x", name="A"),
                Slot(id="b", slot_type="x", name="B"),
                Slot(id="c", slot_type="x", name="C", depends_on=["a", "b"]),
            ],
        )
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(pipeline, {})
        state = tracker.update_slot(state, "a", SlotStatus.IN_PROGRESS)
        state = tracker.update_slot(state, "a", SlotStatus.COMPLETED)
        state = tracker.update_slot(state, "b", SlotStatus.SKIPPED)
        ready = tracker.get_ready_slots(pipeline, state)
        assert "c" in ready


class TestYamlPathSaveLoad:
    """Bug 7: yaml_path must survive save/load roundtrip."""

    def test_yaml_path_stored(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {}, yaml_path="/tmp/test.yaml")
        assert state.yaml_path == "/tmp/test.yaml"

    def test_yaml_path_roundtrip(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {}, yaml_path="/tmp/test.yaml")
        path = tracker.save(state)

        tracker2 = PipelineStateTracker(str(state_dir))
        loaded = tracker2.load(path)
        assert loaded.yaml_path == "/tmp/test.yaml"

    def test_yaml_path_none_roundtrip(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        path = tracker.save(state)

        tracker2 = PipelineStateTracker(str(state_dir))
        loaded = tracker2.load(path)
        assert loaded.yaml_path is None


# ===================================================================
# Phase 2: State Transition Enforcement Tests
# ===================================================================

from src.pipeline.state import InvalidTransitionError, VALID_SLOT_TRANSITIONS


class TestSlotTransitionEnforcement:
    """Valid and invalid slot state transitions."""

    def test_pending_to_in_progress(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        assert state.slots["slot-design"].status == SlotStatus.IN_PROGRESS

    def test_pending_to_completed_blocked(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        with pytest.raises(InvalidTransitionError, match="pending -> completed"):
            tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)

    def test_completed_is_terminal(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        with pytest.raises(InvalidTransitionError):
            tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)

    def test_skipped_is_terminal(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.SKIPPED)
        with pytest.raises(InvalidTransitionError):
            tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)

    def test_failed_to_retrying(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.FAILED)
        state = tracker.update_slot(state, "slot-design", SlotStatus.RETRYING)
        assert state.slots["slot-design"].status == SlotStatus.RETRYING

    def test_retrying_to_in_progress(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.FAILED)
        state = tracker.update_slot(state, "slot-design", SlotStatus.RETRYING)
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        assert state.slots["slot-design"].status == SlotStatus.IN_PROGRESS

    def test_in_progress_to_post_check(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        state = tracker.update_slot(state, "slot-design", SlotStatus.POST_CHECK)
        assert state.slots["slot-design"].status == SlotStatus.POST_CHECK

    def test_post_check_to_completed(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        state = tracker.update_slot(state, "slot-design", SlotStatus.POST_CHECK)
        state = tracker.update_slot(state, "slot-design", SlotStatus.COMPLETED)
        assert state.slots["slot-design"].status == SlotStatus.COMPLETED

    def test_same_status_is_noop(self, sample_pipeline, state_dir):
        """Setting the same status should not raise."""
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.PENDING)
        assert state.slots["slot-design"].status == SlotStatus.PENDING

    def test_transition_table_covers_all_statuses(self):
        """Every SlotStatus must have an entry in the transition table."""
        for status in SlotStatus:
            assert status in VALID_SLOT_TRANSITIONS, (
                f"{status.value} missing from VALID_SLOT_TRANSITIONS"
            )

    def test_in_progress_to_pending_blocked(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_slot(state, "slot-design", SlotStatus.IN_PROGRESS)
        with pytest.raises(InvalidTransitionError, match="in_progress -> pending"):
            tracker.update_slot(state, "slot-design", SlotStatus.PENDING)


class TestPipelineTransitionEnforcement:
    """Valid and invalid pipeline state transitions."""

    def test_loaded_to_running(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        assert state.status == PipelineStatus.RUNNING

    def test_running_to_loaded_blocked(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        with pytest.raises(InvalidTransitionError, match="running -> loaded"):
            tracker.update_pipeline_status(state, PipelineStatus.LOADED)

    def test_completed_to_auditing(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        state = tracker.update_pipeline_status(state, PipelineStatus.COMPLETED)
        state = tracker.update_pipeline_status(state, PipelineStatus.AUDITING)
        assert state.status == PipelineStatus.AUDITING

    def test_aborted_is_terminal(self, sample_pipeline, state_dir):
        tracker = PipelineStateTracker(str(state_dir))
        state = tracker.init_state(sample_pipeline, {})
        state = tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
        state = tracker.update_pipeline_status(state, PipelineStatus.ABORTED)
        with pytest.raises(InvalidTransitionError):
            tracker.update_pipeline_status(state, PipelineStatus.RUNNING)
