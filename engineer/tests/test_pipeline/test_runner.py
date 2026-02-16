"""Tests for pipeline.runner -- Pipeline orchestration engine."""

import pytest
import yaml

from pipeline.models import (
    PipelineObserver,
    PipelineStatus,
    SlotStatus,
)
from pipeline.observer import ComplianceObserver
from pipeline.runner import PipelineExecutionError, PipelineRunner


@pytest.fixture
def project_dirs(tmp_path):
    """Create directory structure for runner tests."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "state" / "active").mkdir(parents=True)
    (tmp_path / "state" / "archive").mkdir(parents=True)
    (tmp_path / "slot-types").mkdir()
    (tmp_path / "agents").mkdir()

    # Create a minimal slot type
    (tmp_path / "slot-types" / "implementer.yaml").write_text(
        yaml.dump(
            {
                "slot_type": {
                    "id": "implementer",
                    "name": "Code Implementer",
                    "category": "engineering",
                    "description": "Writes code",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "required_capabilities": ["python"],
                }
            }
        )
    )
    (tmp_path / "slot-types" / "designer.yaml").write_text(
        yaml.dump(
            {
                "slot_type": {
                    "id": "designer",
                    "name": "Designer",
                    "category": "architecture",
                    "description": "Designs",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "required_capabilities": ["design"],
                }
            }
        )
    )

    # Create agent .md with front-matter
    (tmp_path / "agents" / "eng.md").write_text(
        "---\n"
        "agent_id: ENG-001\n"
        "version: '1.0'\n"
        "capabilities:\n"
        "  - python\n"
        "compatible_slot_types:\n"
        "  - implementer\n"
        "---\n"
        "# Engineer\n"
    )
    (tmp_path / "agents" / "arch.md").write_text(
        "---\n"
        "agent_id: ARCH-001\n"
        "version: '1.0'\n"
        "capabilities:\n"
        "  - design\n"
        "compatible_slot_types:\n"
        "  - designer\n"
        "---\n"
        "# Architect\n"
    )

    return tmp_path


@pytest.fixture
def pipeline_yaml(project_dirs):
    """Create a pipeline YAML file and return its path."""
    pipeline_data = {
        "pipeline": {
            "id": "test-pipeline",
            "name": "Test Pipeline",
            "version": "1.0.0",
            "description": "A test pipeline",
            "created_by": "test",
            "created_at": "2026-01-01T00:00:00Z",
            "slots": [
                {
                    "id": "slot-design",
                    "slot_type": "designer",
                    "name": "Design",
                    "outputs": [
                        {
                            "name": "design_doc",
                            "type": "design_doc",
                        }
                    ],
                },
                {
                    "id": "slot-implement",
                    "slot_type": "implementer",
                    "name": "Implement",
                    "depends_on": ["slot-design"],
                },
            ],
            "data_flow": [
                {
                    "from_slot": "slot-design",
                    "to_slot": "slot-implement",
                    "artifact": "design_doc",
                }
            ],
        }
    }
    path = project_dirs / "templates" / "test-pipeline.yaml"
    path.write_text(yaml.dump(pipeline_data))
    return str(path)


@pytest.fixture
def runner(project_dirs):
    """Create a PipelineRunner with test directories."""
    return PipelineRunner(
        project_root=str(project_dirs),
        templates_dir=str(project_dirs / "templates"),
        state_dir=str(project_dirs / "state" / "active"),
        slot_types_dir=str(project_dirs / "slot-types"),
        agents_dir=str(project_dirs / "agents"),
    )


# ===================================================================
# prepare
# ===================================================================


class TestPrepare:
    def test_successful_prepare(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        assert pipeline.id == "test-pipeline"
        assert state.pipeline_id == "test-pipeline"
        assert state.status == PipelineStatus.LOADED
        assert len(state.slots) == 2
        assert all(
            s.status == SlotStatus.PENDING for s in state.slots.values()
        )

    def test_prepare_invalid_yaml(self, runner, project_dirs):
        bad_path = project_dirs / "templates" / "bad.yaml"
        bad_path.write_text("not: valid: pipeline")
        with pytest.raises(Exception):
            runner.prepare(str(bad_path), {})

    def test_prepare_cycle(self, runner, project_dirs):
        cycle_data = {
            "pipeline": {
                "id": "cycle",
                "name": "Cycle",
                "version": "1.0.0",
                "description": "Cyclic",
                "created_by": "test",
                "created_at": "2026-01-01",
                "slots": [
                    {
                        "id": "a",
                        "slot_type": "designer",
                        "name": "A",
                        "depends_on": ["b"],
                    },
                    {
                        "id": "b",
                        "slot_type": "designer",
                        "name": "B",
                        "depends_on": ["a"],
                    },
                ],
            }
        }
        path = project_dirs / "templates" / "cycle.yaml"
        path.write_text(yaml.dump(cycle_data))
        with pytest.raises(PipelineExecutionError, match="validation failed"):
            runner.prepare(str(path), {})


# ===================================================================
# get_next_slots
# ===================================================================


class TestGetNextSlots:
    def test_initial_ready(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        next_slots = runner.get_next_slots(pipeline, state)
        assert len(next_slots) == 1
        assert next_slots[0].id == "slot-design"

    def test_after_first_complete(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        # Manually set slot-design to completed
        state.slots["slot-design"].status = SlotStatus.COMPLETED
        next_slots = runner.get_next_slots(pipeline, state)
        assert len(next_slots) == 1
        assert next_slots[0].id == "slot-implement"

    def test_all_complete(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state.slots["slot-design"].status = SlotStatus.COMPLETED
        state.slots["slot-implement"].status = SlotStatus.COMPLETED
        next_slots = runner.get_next_slots(pipeline, state)
        assert len(next_slots) == 0


# ===================================================================
# begin_slot
# ===================================================================


class TestBeginSlot:
    def test_begin_with_no_preconditions(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        slot = pipeline.slots[0]  # slot-design (no pre_conditions)
        state = runner.begin_slot(
            slot, pipeline, state, agent_id="ARCH-001"
        )
        assert state.slots["slot-design"].status == SlotStatus.IN_PROGRESS
        assert state.slots["slot-design"].agent_id == "ARCH-001"
        assert state.status == PipelineStatus.RUNNING

    def test_begin_with_failing_precondition(self, runner, project_dirs):
        # Create pipeline with a file_exists pre-condition that will fail
        pipeline_data = {
            "pipeline": {
                "id": "precond-test",
                "name": "Precond Test",
                "version": "1.0.0",
                "description": "T",
                "created_by": "t",
                "created_at": "t",
                "slots": [
                    {
                        "id": "s1",
                        "slot_type": "designer",
                        "name": "S1",
                        "pre_conditions": [
                            {
                                "check": "Nonexistent file",
                                "type": "file_exists",
                                "target": "nonexistent.txt",
                            }
                        ],
                    }
                ],
            }
        }
        path = project_dirs / "templates" / "precond.yaml"
        path.write_text(yaml.dump(pipeline_data))
        pipeline, state = runner.prepare(str(path), {})
        slot = pipeline.slots[0]
        state = runner.begin_slot(slot, pipeline, state)
        assert state.slots["s1"].status == SlotStatus.FAILED
        assert "Pre-conditions failed" in state.slots["s1"].error


# ===================================================================
# complete_slot
# ===================================================================


class TestCompleteSlot:
    def test_complete_no_postconditions(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        # Begin and complete slot-design
        slot = pipeline.slots[0]
        state = runner.begin_slot(slot, pipeline, state)
        state = runner.complete_slot("slot-design", pipeline, state)
        assert state.slots["slot-design"].status == SlotStatus.COMPLETED

    def test_complete_all_sets_pipeline_completed(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        # Complete both slots
        state = runner.begin_slot(pipeline.slots[0], pipeline, state)
        state = runner.complete_slot("slot-design", pipeline, state)
        state = runner.begin_slot(pipeline.slots[1], pipeline, state)
        state = runner.complete_slot("slot-implement", pipeline, state)
        assert state.status == PipelineStatus.COMPLETED

    def test_complete_with_failing_postcondition(self, runner, project_dirs):
        pipeline_data = {
            "pipeline": {
                "id": "postcond",
                "name": "T",
                "version": "1.0.0",
                "description": "T",
                "created_by": "t",
                "created_at": "t",
                "slots": [
                    {
                        "id": "s1",
                        "slot_type": "designer",
                        "name": "S1",
                        "post_conditions": [
                            {
                                "check": "Delivery exists",
                                "type": "file_exists",
                                "target": "DELIVERY.yaml",
                            }
                        ],
                    }
                ],
            }
        }
        path = project_dirs / "templates" / "postcond.yaml"
        path.write_text(yaml.dump(pipeline_data))
        pipeline, state = runner.prepare(str(path), {})
        state = runner.begin_slot(pipeline.slots[0], pipeline, state)
        state = runner.complete_slot("s1", pipeline, state)
        assert state.slots["s1"].status == SlotStatus.FAILED
        assert "Post-conditions failed" in state.slots["s1"].error


# ===================================================================
# fail_slot / skip_slot
# ===================================================================


class TestFailSlot:
    def test_fail_slot(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state = runner.fail_slot("slot-design", "Agent crashed", state)
        assert state.slots["slot-design"].status == SlotStatus.FAILED
        assert state.slots["slot-design"].error == "Agent crashed"

    def test_fail_all_slots_sets_pipeline_failed(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state = runner.fail_slot("slot-design", "err1", state)
        state = runner.fail_slot("slot-implement", "err2", state)
        assert state.status == PipelineStatus.FAILED


class TestSkipSlot:
    def test_skip_slot(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state = runner.skip_slot("slot-design", state)
        assert state.slots["slot-design"].status == SlotStatus.SKIPPED

    def test_skip_all_slots_completes_pipeline(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state = runner.skip_slot("slot-design", state)
        state = runner.skip_slot("slot-implement", state)
        assert state.status == PipelineStatus.COMPLETED


# ===================================================================
# get_summary
# ===================================================================


class TestGetSummary:
    def test_summary_format(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        summary = runner.get_summary(state)
        assert "Pipeline: test-pipeline" in summary
        assert "v1.0.0" in summary
        assert "Progress: 0/2 slots" in summary
        assert "[PENDING]" in summary

    def test_summary_with_agent(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state = runner.begin_slot(
            pipeline.slots[0], pipeline, state, agent_id="ENG-001"
        )
        summary = runner.get_summary(state)
        assert "agent: ENG-001" in summary
        assert "[IN_PROGRESS]" in summary


# ===================================================================
# resume_with_pipeline
# ===================================================================


class TestResumeWithPipeline:
    def test_resume_successful(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state_path = runner._state_tracker.save(state)
        resumed_pipeline, resumed_state = runner.resume_with_pipeline(
            state_path, pipeline_yaml, {}
        )
        assert resumed_state.pipeline_id == "test-pipeline"
        assert resumed_pipeline.id == "test-pipeline"

    def test_resume_hash_mismatch(self, runner, pipeline_yaml, project_dirs):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state_path = runner._state_tracker.save(state)

        # Modify the pipeline YAML to cause hash mismatch
        modified_data = {
            "pipeline": {
                "id": "test-pipeline",
                "name": "Modified Pipeline",
                "version": "2.0.0",
                "description": "Modified",
                "created_by": "test",
                "created_at": "2026-01-01T00:00:00Z",
                "slots": [
                    {
                        "id": "slot-different",
                        "slot_type": "designer",
                        "name": "Different",
                    }
                ],
            }
        }
        modified_path = project_dirs / "templates" / "modified.yaml"
        modified_path.write_text(yaml.dump(modified_data))
        with pytest.raises(
            PipelineExecutionError, match="hash mismatch"
        ):
            runner.resume_with_pipeline(state_path, str(modified_path), {})


# ===================================================================
# resume (base method)
# ===================================================================


class TestResume:
    def test_resume_raises_not_implemented(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state_path = runner._state_tracker.save(state)
        with pytest.raises(PipelineExecutionError, match="resume"):
            runner.resume(state_path)


# ===================================================================
# _find_slot
# ===================================================================


class TestFindSlot:
    def test_found(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        slot = PipelineRunner._find_slot(pipeline, "slot-design")
        assert slot.id == "slot-design"

    def test_not_found(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        with pytest.raises(KeyError, match="nonexistent"):
            PipelineRunner._find_slot(pipeline, "nonexistent")


# ===================================================================
# Observer integration
# ===================================================================


class _RecordingObserver(PipelineObserver):
    """Captures lifecycle events for test assertions."""

    def __init__(self):
        self.events = []

    def on_pipeline_started(self, pipeline_id, state):
        self.events.append(("pipeline_started", pipeline_id))

    def on_pipeline_completed(self, pipeline_id, state):
        self.events.append(("pipeline_completed", pipeline_id))

    def on_pipeline_failed(self, pipeline_id, state, error):
        self.events.append(("pipeline_failed", pipeline_id, error))

    def on_slot_started(self, pipeline_id, slot_id, agent_id):
        self.events.append(("slot_started", pipeline_id, slot_id, agent_id))

    def on_slot_completed(self, pipeline_id, slot_id):
        self.events.append(("slot_completed", pipeline_id, slot_id))

    def on_slot_failed(self, pipeline_id, slot_id, error):
        self.events.append(("slot_failed", pipeline_id, slot_id, error))

    def on_gate_check_completed(self, pipeline_id, slot_id, gate_type, results):
        self.events.append(("gate_check", pipeline_id, slot_id, gate_type))

    def on_status_changed(self, pipeline_id, old_status, new_status):
        self.events.append(("status_changed", pipeline_id, old_status, new_status))


class _FailingObserver(PipelineObserver):
    """Observer that raises on every method -- tests error isolation."""

    def on_pipeline_started(self, pipeline_id, state):
        raise RuntimeError("boom")

    def on_pipeline_completed(self, pipeline_id, state):
        raise RuntimeError("boom")

    def on_pipeline_failed(self, pipeline_id, state, error):
        raise RuntimeError("boom")

    def on_slot_started(self, pipeline_id, slot_id, agent_id):
        raise RuntimeError("boom")

    def on_slot_completed(self, pipeline_id, slot_id):
        raise RuntimeError("boom")

    def on_slot_failed(self, pipeline_id, slot_id, error):
        raise RuntimeError("boom")

    def on_gate_check_completed(self, pipeline_id, slot_id, gate_type, results):
        raise RuntimeError("boom")

    def on_status_changed(self, pipeline_id, old_status, new_status):
        raise RuntimeError("boom")


@pytest.fixture
def recording_observer():
    return _RecordingObserver()


@pytest.fixture
def runner_with_observer(project_dirs, recording_observer):
    """PipelineRunner with a recording observer attached."""
    r = PipelineRunner(
        project_root=str(project_dirs),
        templates_dir=str(project_dirs / "templates"),
        state_dir=str(project_dirs / "state" / "active"),
        slot_types_dir=str(project_dirs / "slot-types"),
        agents_dir=str(project_dirs / "agents"),
        observers=[recording_observer],
    )
    return r


class TestObserverIntegration:
    def test_begin_slot_fires_events(
        self, runner_with_observer, pipeline_yaml, recording_observer
    ):
        pipeline, state = runner_with_observer.prepare(pipeline_yaml, {})
        slot = pipeline.slots[0]
        runner_with_observer.begin_slot(slot, pipeline, state, agent_id="ARCH-001")

        event_types = [e[0] for e in recording_observer.events]
        assert "gate_check" in event_types
        assert "status_changed" in event_types
        assert "pipeline_started" in event_types
        assert "slot_started" in event_types

    def test_complete_slot_fires_events(
        self, runner_with_observer, pipeline_yaml, recording_observer
    ):
        pipeline, state = runner_with_observer.prepare(pipeline_yaml, {})
        state = runner_with_observer.begin_slot(
            pipeline.slots[0], pipeline, state
        )
        recording_observer.events.clear()
        runner_with_observer.complete_slot("slot-design", pipeline, state)

        event_types = [e[0] for e in recording_observer.events]
        assert "gate_check" in event_types
        assert "slot_completed" in event_types

    def test_complete_all_fires_pipeline_completed(
        self, runner_with_observer, pipeline_yaml, recording_observer
    ):
        pipeline, state = runner_with_observer.prepare(pipeline_yaml, {})
        state = runner_with_observer.begin_slot(
            pipeline.slots[0], pipeline, state
        )
        state = runner_with_observer.complete_slot("slot-design", pipeline, state)
        state = runner_with_observer.begin_slot(
            pipeline.slots[1], pipeline, state
        )
        recording_observer.events.clear()
        runner_with_observer.complete_slot("slot-implement", pipeline, state)

        event_types = [e[0] for e in recording_observer.events]
        assert "pipeline_completed" in event_types
        assert "status_changed" in event_types

    def test_fail_slot_fires_events(
        self, runner_with_observer, pipeline_yaml, recording_observer
    ):
        pipeline, state = runner_with_observer.prepare(pipeline_yaml, {})
        runner_with_observer.fail_slot("slot-design", "agent crashed", state)

        event_types = [e[0] for e in recording_observer.events]
        assert "slot_failed" in event_types

    def test_fail_all_fires_pipeline_failed(
        self, runner_with_observer, pipeline_yaml, recording_observer
    ):
        pipeline, state = runner_with_observer.prepare(pipeline_yaml, {})
        state = runner_with_observer.fail_slot("slot-design", "err", state)
        recording_observer.events.clear()
        runner_with_observer.fail_slot("slot-implement", "err", state)

        event_types = [e[0] for e in recording_observer.events]
        assert "pipeline_failed" in event_types

    def test_add_observer_after_init(self, runner, pipeline_yaml):
        obs = _RecordingObserver()
        runner.add_observer(obs)
        pipeline, state = runner.prepare(pipeline_yaml, {})
        runner.begin_slot(pipeline.slots[0], pipeline, state)
        assert len(obs.events) > 0

    def test_multiple_observers_all_notified(self, project_dirs, pipeline_yaml):
        obs1 = _RecordingObserver()
        obs2 = _RecordingObserver()
        r = PipelineRunner(
            project_root=str(project_dirs),
            templates_dir=str(project_dirs / "templates"),
            state_dir=str(project_dirs / "state" / "active"),
            slot_types_dir=str(project_dirs / "slot-types"),
            agents_dir=str(project_dirs / "agents"),
            observers=[obs1, obs2],
        )
        pipeline, state = r.prepare(pipeline_yaml, {})
        r.begin_slot(pipeline.slots[0], pipeline, state)
        assert len(obs1.events) > 0
        assert len(obs2.events) > 0
        assert len(obs1.events) == len(obs2.events)


class TestObserverErrorIsolation:
    def test_failing_observer_does_not_block_execution(
        self, project_dirs, pipeline_yaml
    ):
        """A broken observer must not prevent pipeline operations."""
        failing = _FailingObserver()
        recording = _RecordingObserver()
        r = PipelineRunner(
            project_root=str(project_dirs),
            templates_dir=str(project_dirs / "templates"),
            state_dir=str(project_dirs / "state" / "active"),
            slot_types_dir=str(project_dirs / "slot-types"),
            agents_dir=str(project_dirs / "agents"),
            observers=[failing, recording],
        )
        pipeline, state = r.prepare(pipeline_yaml, {})
        state = r.begin_slot(pipeline.slots[0], pipeline, state)
        # The pipeline should continue despite the failing observer
        assert state.slots["slot-design"].status == SlotStatus.IN_PROGRESS
        # The recording observer after the failing one still got notified
        assert len(recording.events) > 0

    def test_failing_observer_does_not_block_complete(
        self, project_dirs, pipeline_yaml
    ):
        failing = _FailingObserver()
        r = PipelineRunner(
            project_root=str(project_dirs),
            templates_dir=str(project_dirs / "templates"),
            state_dir=str(project_dirs / "state" / "active"),
            slot_types_dir=str(project_dirs / "slot-types"),
            agents_dir=str(project_dirs / "agents"),
            observers=[failing],
        )
        pipeline, state = r.prepare(pipeline_yaml, {})
        state = r.begin_slot(pipeline.slots[0], pipeline, state)
        state = r.complete_slot("slot-design", pipeline, state)
        assert state.slots["slot-design"].status == SlotStatus.COMPLETED


class TestComplianceObserverWithRunner:
    def test_compliance_observer_logs_full_lifecycle(
        self, project_dirs, pipeline_yaml, tmp_path
    ):
        """End-to-end: ComplianceObserver writes events for a full pipeline run."""
        log_dir = tmp_path / "compliance-logs"
        obs = ComplianceObserver(str(log_dir))
        r = PipelineRunner(
            project_root=str(project_dirs),
            templates_dir=str(project_dirs / "templates"),
            state_dir=str(project_dirs / "state" / "active"),
            slot_types_dir=str(project_dirs / "slot-types"),
            agents_dir=str(project_dirs / "agents"),
            observers=[obs],
        )
        pipeline, state = r.prepare(pipeline_yaml, {})
        state = r.begin_slot(pipeline.slots[0], pipeline, state, agent_id="ARCH-001")
        state = r.complete_slot("slot-design", pipeline, state)
        state = r.begin_slot(pipeline.slots[1], pipeline, state, agent_id="ENG-001")
        state = r.complete_slot("slot-implement", pipeline, state)

        log_path = log_dir / "test-pipeline.events.yaml"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        events = list(yaml.safe_load_all(content))
        event_types = [e["event"] for e in events]
        assert "pipeline_started" in event_types
        assert "slot_started" in event_types
        assert "slot_completed" in event_types
        assert "pipeline_completed" in event_types


# ===================================================================
# start_auditing
# ===================================================================


class TestStartAuditing:
    def test_completed_to_auditing(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        # Complete all slots
        state = runner.begin_slot(pipeline.slots[0], pipeline, state)
        state = runner.complete_slot("slot-design", pipeline, state)
        state = runner.begin_slot(pipeline.slots[1], pipeline, state)
        state = runner.complete_slot("slot-implement", pipeline, state)
        assert state.status == PipelineStatus.COMPLETED

        state = runner.start_auditing(state)
        assert state.status == PipelineStatus.AUDITING

    def test_auditing_not_from_running(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state = runner.begin_slot(pipeline.slots[0], pipeline, state)
        assert state.status == PipelineStatus.RUNNING
        with pytest.raises(PipelineExecutionError, match="expected 'completed'"):
            runner.start_auditing(state)

    def test_auditing_not_from_loaded(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        assert state.status == PipelineStatus.LOADED
        with pytest.raises(PipelineExecutionError, match="expected 'completed'"):
            runner.start_auditing(state)

    def test_auditing_not_from_failed(self, runner, pipeline_yaml):
        pipeline, state = runner.prepare(pipeline_yaml, {})
        state = runner.fail_slot("slot-design", "err", state)
        state = runner.fail_slot("slot-implement", "err", state)
        assert state.status == PipelineStatus.FAILED
        with pytest.raises(PipelineExecutionError, match="expected 'completed'"):
            runner.start_auditing(state)

    def test_auditing_fires_status_changed(
        self, runner_with_observer, pipeline_yaml, recording_observer
    ):
        pipeline, state = runner_with_observer.prepare(pipeline_yaml, {})
        state = runner_with_observer.begin_slot(pipeline.slots[0], pipeline, state)
        state = runner_with_observer.complete_slot("slot-design", pipeline, state)
        state = runner_with_observer.begin_slot(pipeline.slots[1], pipeline, state)
        state = runner_with_observer.complete_slot("slot-implement", pipeline, state)
        recording_observer.events.clear()

        runner_with_observer.start_auditing(state)

        event_types = [e[0] for e in recording_observer.events]
        assert "status_changed" in event_types
        status_event = [
            e for e in recording_observer.events if e[0] == "status_changed"
        ][0]
        assert status_event[2] == PipelineStatus.COMPLETED
        assert status_event[3] == PipelineStatus.AUDITING
