"""Tests for pipeline.validator -- DAG validation and I/O compatibility."""

import pytest
from pathlib import Path

from src.pipeline.validator import (
    PipelineCycleError,
    PipelineValidator,
    ValidationResult,
)
from src.pipeline.models import (
    ArtifactOutput,
    DataFlowEdge,
    Pipeline,
    Slot,
    SlotTask,
)
from src.pipeline.loader import PipelineLoader


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def validator(tmp_path):
    return PipelineValidator(project_root=str(tmp_path))


@pytest.fixture
def loader():
    return PipelineLoader()


class TestValidate:
    def test_valid_pipeline(self, validator, sample_pipeline):
        result = validator.validate(sample_pipeline)
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_loaded_pipeline(self, validator, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        result = validator.validate(pipeline)
        assert result.is_valid is True

    def test_returns_validation_result(self, validator, sample_pipeline):
        result = validator.validate(sample_pipeline)
        assert isinstance(result, ValidationResult)


class TestUniqueSlotIds:
    def test_duplicate_ids(self, validator):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[
                Slot(id="slot-a", slot_type="designer", name="A"),
                Slot(id="slot-a", slot_type="implementer", name="B"),
            ],
        )
        result = validator.validate(pipeline)
        assert result.is_valid is False
        assert any("Duplicate slot ID" in e for e in result.errors)


class TestValidDependencies:
    def test_missing_dependency_target(self, validator):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[
                Slot(id="slot-a", slot_type="designer", name="A"),
                Slot(
                    id="slot-b", slot_type="implementer", name="B",
                    depends_on=["slot-nonexistent"],
                ),
            ],
        )
        result = validator.validate(pipeline)
        assert result.is_valid is False
        assert any("does not exist" in e for e in result.errors)


class TestCheckDag:
    def test_no_cycle(self, validator, sample_pipeline):
        errors = validator.check_dag(sample_pipeline.slots)
        assert errors == []

    def test_simple_cycle(self, validator):
        slots = [
            Slot(id="a", slot_type="x", name="A", depends_on=["b"]),
            Slot(id="b", slot_type="x", name="B", depends_on=["a"]),
        ]
        errors = validator.check_dag(slots)
        assert len(errors) == 1
        assert "cycle" in errors[0].lower()

    def test_three_node_cycle(self, validator):
        slots = [
            Slot(id="a", slot_type="x", name="A", depends_on=["c"]),
            Slot(id="b", slot_type="x", name="B", depends_on=["a"]),
            Slot(id="c", slot_type="x", name="C", depends_on=["b"]),
        ]
        errors = validator.check_dag(slots)
        assert len(errors) == 1

    def test_cycle_from_yaml(self, validator, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "invalid-cycle.yaml"))
        result = validator.validate(pipeline)
        assert result.is_valid is False
        assert any("cycle" in e.lower() for e in result.errors)


class TestTopologicalSort:
    def test_linear_sort(self, validator):
        slots = [
            Slot(id="a", slot_type="x", name="A"),
            Slot(id="b", slot_type="x", name="B", depends_on=["a"]),
            Slot(id="c", slot_type="x", name="C", depends_on=["b"]),
        ]
        order = validator.topological_sort(slots)
        assert order == ["a", "b", "c"]

    def test_parallel_sort(self, validator):
        slots = [
            Slot(id="a", slot_type="x", name="A"),
            Slot(id="b", slot_type="x", name="B", depends_on=["a"]),
            Slot(id="c", slot_type="x", name="C", depends_on=["a"]),
            Slot(id="d", slot_type="x", name="D", depends_on=["b", "c"]),
        ]
        order = validator.topological_sort(slots)
        assert order[0] == "a"
        assert order[-1] == "d"
        # b and c should both come before d
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_raises_on_cycle(self, validator):
        slots = [
            Slot(id="a", slot_type="x", name="A", depends_on=["b"]),
            Slot(id="b", slot_type="x", name="B", depends_on=["a"]),
        ]
        with pytest.raises(PipelineCycleError, match="cycle"):
            validator.topological_sort(slots)

    def test_single_slot(self, validator):
        slots = [Slot(id="only", slot_type="x", name="Only")]
        order = validator.topological_sort(slots)
        assert order == ["only"]


class TestIoCompatibility:
    def test_valid_io(self, validator, sample_pipeline):
        errors = validator.check_io_compatibility(sample_pipeline)
        assert errors == []

    def test_missing_output_artifact(self, validator, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "invalid-io.yaml"))
        errors = validator.check_io_compatibility(pipeline)
        assert len(errors) == 1
        assert "design_doc" in errors[0]

    def test_missing_from_slot(self, validator):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[Slot(id="slot-b", slot_type="x", name="B")],
            data_flow=[
                DataFlowEdge(from_slot="nonexistent", to_slot="slot-b", artifact="x"),
            ],
        )
        errors = validator.check_io_compatibility(pipeline)
        assert any("from_slot" in e and "nonexistent" in e for e in errors)

    def test_missing_to_slot(self, validator):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[
                Slot(
                    id="slot-a", slot_type="x", name="A",
                    outputs=[ArtifactOutput(name="doc", type="design_doc")],
                ),
            ],
            data_flow=[
                DataFlowEdge(from_slot="slot-a", to_slot="nonexistent", artifact="doc"),
            ],
        )
        errors = validator.check_io_compatibility(pipeline)
        assert any("to_slot" in e and "nonexistent" in e for e in errors)


class TestTerminalSlot:
    def test_has_terminal(self, validator, sample_pipeline):
        result = validator.validate(sample_pipeline)
        # slot-implement is terminal (nothing depends on it)
        assert not any("terminal" in w.lower() for w in result.warnings)

    def test_no_terminal_warning(self, validator):
        """When all slots are dependencies of another, warn."""
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[
                Slot(id="a", slot_type="x", name="A", depends_on=["b"]),
                Slot(id="b", slot_type="x", name="B", depends_on=["a"]),
            ],
        )
        result = validator.validate(pipeline)
        # This also has a cycle, but the terminal check is separate
        assert any("terminal" in w.lower() for w in result.warnings)


class TestCheckSlotTypes:
    def test_slot_types_missing(self, validator):
        """Slot type check with a mock registry that raises."""

        class FakeRegistry:
            def get_slot_type(self, slot_type_id):
                raise KeyError(f"Not found: {slot_type_id}")

        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[Slot(id="s", slot_type="nonexistent", name="S")],
        )
        errors = validator.check_slot_types(pipeline, FakeRegistry())
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_slot_types_valid(self, validator):
        """Slot type check with a registry that resolves."""

        class FakeRegistry:
            def get_slot_type(self, slot_type_id):
                return True  # Just needs to not raise

        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[Slot(id="s", slot_type="designer", name="S")],
        )
        errors = validator.check_slot_types(pipeline, FakeRegistry())
        assert errors == []
