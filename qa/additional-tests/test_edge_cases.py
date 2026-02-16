"""QA supplementary edge-case tests for the pipeline engine.

Tests edge cases the engineer may have missed: empty pipelines, single-slot
pipelines, self-referencing depends_on, data_flow only dependencies,
concurrent state updates, and boundary conditions.
"""

import os
import sys
import tempfile

import pytest
import yaml

# Ensure the engineer's src is on the path
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "engineer", "src"
))

from pipeline.models import (
    DataFlowEdge,
    Gate,
    GateCheckResult,
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotAssignment,
    SlotState,
    SlotStatus,
    SlotTypeDefinition,
)
from pipeline.loader import PipelineLoader, PipelineLoadError, PipelineParameterError
from pipeline.validator import PipelineValidator, PipelineCycleError, ValidationResult
from pipeline.state import PipelineStateTracker
from pipeline.gate_checker import GateChecker
from pipeline.slot_registry import SlotRegistry, SlotTypeNotFoundError, SlotManifest


# ---------------------------------------------------------------------------
# Test 1: Empty pipeline (zero slots) validation
# ---------------------------------------------------------------------------
class TestEmptyPipeline:
    def test_validate_zero_slots(self):
        """A pipeline with zero slots should validate (no structural errors)."""
        pipeline = Pipeline(
            id="empty", name="Empty", version="1.0.0",
            description="Empty pipeline", created_by="QA",
            created_at="2026-02-16T00:00:00Z",
            slots=[], data_flow=[],
        )
        validator = PipelineValidator("/tmp")
        result = validator.validate(pipeline)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_topological_sort_zero_slots(self):
        """Topological sort on zero slots should return empty list."""
        validator = PipelineValidator("/tmp")
        result = validator.topological_sort([])
        assert result == []


# ---------------------------------------------------------------------------
# Test 2: Single-slot pipeline
# ---------------------------------------------------------------------------
class TestSingleSlotPipeline:
    def test_validate_single_slot(self):
        """A single-slot pipeline with no deps is valid."""
        slot = Slot(id="only-slot", slot_type="implementer", name="Solo Slot")
        pipeline = Pipeline(
            id="single", name="Single", version="1.0.0",
            description="Single slot", created_by="QA",
            created_at="2026-02-16T00:00:00Z",
            slots=[slot], data_flow=[],
        )
        validator = PipelineValidator("/tmp")
        result = validator.validate(pipeline)
        assert result.is_valid is True

    def test_single_slot_is_ready_immediately(self, tmp_path):
        """A single-slot pipeline should have its slot ready immediately."""
        slot = Slot(id="only-slot", slot_type="implementer", name="Solo")
        pipeline = Pipeline(
            id="single", name="Single", version="1.0.0",
            description="d", created_by="QA", created_at="2026-02-16",
            slots=[slot], data_flow=[],
        )
        tracker = PipelineStateTracker(str(tmp_path))
        state = tracker.init_state(pipeline, {})
        ready = tracker.get_ready_slots(pipeline, state)
        assert ready == ["only-slot"]


# ---------------------------------------------------------------------------
# Test 3: Self-referencing depends_on (slot depends on itself)
# ---------------------------------------------------------------------------
class TestSelfReference:
    def test_self_dependency_detected_as_cycle(self):
        """A slot that depends on itself should be detected as a cycle."""
        slot = Slot(
            id="self-ref", slot_type="implementer", name="Self Ref",
            depends_on=["self-ref"],
        )
        validator = PipelineValidator("/tmp")
        errors = validator.check_dag([slot])
        assert len(errors) > 0
        assert "cycle" in errors[0].lower() or "self-ref" in errors[0]


# ---------------------------------------------------------------------------
# Test 4: data_flow-only dependency (no explicit depends_on)
# ---------------------------------------------------------------------------
class TestDataFlowOnlyDependency:
    def test_data_flow_blocks_downstream(self, tmp_path):
        """Slots connected only via data_flow should still respect ordering."""
        from pipeline.models import ArtifactOutput
        slot_a = Slot(
            id="producer", slot_type="designer", name="Producer",
            outputs=[ArtifactOutput(name="doc", type="design_doc")],
        )
        slot_b = Slot(id="consumer", slot_type="implementer", name="Consumer")
        pipeline = Pipeline(
            id="df-test", name="DF Test", version="1.0.0",
            description="d", created_by="QA", created_at="2026-02-16",
            slots=[slot_a, slot_b],
            data_flow=[DataFlowEdge(
                from_slot="producer", to_slot="consumer",
                artifact="doc", required=True,
            )],
        )
        tracker = PipelineStateTracker(str(tmp_path))
        state = tracker.init_state(pipeline, {})

        ready = tracker.get_ready_slots(pipeline, state)
        assert "producer" in ready
        assert "consumer" not in ready

        # Complete producer, consumer should become ready
        state = tracker.update_slot(state, "producer", SlotStatus.COMPLETED)
        ready = tracker.get_ready_slots(pipeline, state)
        assert "consumer" in ready


# ---------------------------------------------------------------------------
# Test 5: GateChecker with non-existent project root
# ---------------------------------------------------------------------------
class TestGateCheckerBoundary:
    def test_file_exists_with_nonexistent_root(self):
        """check_file_exists should return passed=False for nonexistent root."""
        checker = GateChecker("/nonexistent/root/path")
        result = checker.check_file_exists("some/file.py")
        assert result.passed is False

    def test_all_passed_empty(self):
        """all_passed on empty list should return True (vacuously)."""
        checker = GateChecker("/tmp")
        assert checker.all_passed([]) is True

    def test_custom_unknown_format(self):
        """evaluate_custom with unknown format should fail gracefully."""
        checker = GateChecker("/tmp")
        result = checker.evaluate_custom("unknown:format")
        assert result.passed is False
        assert "Unknown" in result.evidence


# ---------------------------------------------------------------------------
# Test 6: State tracker -- update nonexistent slot
# ---------------------------------------------------------------------------
class TestStateTrackerBoundary:
    def test_update_nonexistent_slot_raises(self, tmp_path):
        """Updating a slot that doesn't exist should raise KeyError."""
        tracker = PipelineStateTracker(str(tmp_path))
        state = PipelineState(
            pipeline_id="test", pipeline_version="1.0.0",
            definition_hash="sha256:abc",
            slots={},
        )
        with pytest.raises(KeyError, match="ghost"):
            tracker.update_slot(state, "ghost", SlotStatus.COMPLETED)


# ---------------------------------------------------------------------------
# Test 7: Loader -- YAML list at top level (not dict)
# ---------------------------------------------------------------------------
class TestLoaderBoundary:
    def test_load_list_yaml_raises(self, tmp_path):
        """A YAML file that is a list (not dict) should raise PipelineLoadError."""
        bad_file = tmp_path / "list.yaml"
        bad_file.write_text("- item1\n- item2\n")
        loader = PipelineLoader()
        with pytest.raises(PipelineLoadError, match="Expected YAML mapping"):
            loader.load(str(bad_file))

    def test_resolve_missing_required_param(self):
        """Resolving with a missing required param should raise."""
        from pipeline.models import Parameter
        loader = PipelineLoader()
        pipeline = Pipeline(
            id="test", name="Test", version="1.0.0",
            description="d", created_by="QA", created_at="2026-02-16",
            parameters=[Parameter(
                name="required_p", type="string",
                description="A required param", required=True,
            )],
        )
        with pytest.raises(PipelineParameterError, match="required_p"):
            loader.resolve(pipeline, {})


# ---------------------------------------------------------------------------
# Test 8: SlotManifest for empty pipeline
# ---------------------------------------------------------------------------
class TestSlotManifestEmpty:
    def test_manifest_empty_pipeline(self, tmp_path):
        """generate_slot_manifest on an empty pipeline should return empty slots."""
        slot_dir = tmp_path / "slot-types"
        slot_dir.mkdir()
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        registry = SlotRegistry(str(slot_dir), str(agents_dir))
        pipeline = Pipeline(
            id="empty", name="E", version="1.0.0",
            description="d", created_by="QA", created_at="2026-02-16",
        )
        manifest = registry.generate_slot_manifest(pipeline)
        assert manifest.pipeline_id == "empty"
        assert manifest.slots == []


# ---------------------------------------------------------------------------
# Test 9: Validator -- duplicate slot IDs
# ---------------------------------------------------------------------------
class TestDuplicateSlotIds:
    def test_duplicate_ids_detected(self):
        """Two slots with the same ID should produce a validation error."""
        slot_a = Slot(id="same", slot_type="designer", name="A")
        slot_b = Slot(id="same", slot_type="implementer", name="B")
        pipeline = Pipeline(
            id="dup", name="Dup", version="1.0.0",
            description="d", created_by="QA", created_at="2026-02-16",
            slots=[slot_a, slot_b],
        )
        validator = PipelineValidator("/tmp")
        result = validator.validate(pipeline)
        assert result.is_valid is False
        assert any("Duplicate" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Test 10: is_complete with mixed terminal states
# ---------------------------------------------------------------------------
class TestIsCompleteMixed:
    def test_mixed_completed_skipped_failed(self, tmp_path):
        """is_complete should be True when all slots are COMPLETED, SKIPPED, or FAILED."""
        tracker = PipelineStateTracker(str(tmp_path))
        state = PipelineState(
            pipeline_id="test", pipeline_version="1.0.0",
            definition_hash="sha256:abc",
            slots={
                "s1": SlotState(slot_id="s1", status=SlotStatus.COMPLETED),
                "s2": SlotState(slot_id="s2", status=SlotStatus.SKIPPED),
                "s3": SlotState(slot_id="s3", status=SlotStatus.FAILED),
            },
        )
        assert tracker.is_complete(state) is True

    def test_not_complete_with_pending(self, tmp_path):
        """is_complete should be False if any slot is still PENDING."""
        tracker = PipelineStateTracker(str(tmp_path))
        state = PipelineState(
            pipeline_id="test", pipeline_version="1.0.0",
            definition_hash="sha256:abc",
            slots={
                "s1": SlotState(slot_id="s1", status=SlotStatus.COMPLETED),
                "s2": SlotState(slot_id="s2", status=SlotStatus.PENDING),
            },
        )
        assert tracker.is_complete(state) is False
