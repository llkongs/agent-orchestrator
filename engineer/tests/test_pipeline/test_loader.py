"""Tests for pipeline.loader -- YAML loading and parameter resolution."""

import pytest
from pathlib import Path

from src.pipeline.loader import PipelineLoader, PipelineLoadError, PipelineParameterError
from src.pipeline.models import Pipeline, Parameter


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def loader():
    return PipelineLoader()


class TestLoad:
    def test_load_valid_pipeline(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        assert pipeline.id == "standard-feature"
        assert pipeline.version == "1.0.0"
        assert len(pipeline.slots) == 3
        assert len(pipeline.parameters) == 2
        assert len(pipeline.data_flow) == 2

    def test_load_bare_pipeline(self, loader):
        """Load pipeline without `pipeline:` wrapper key."""
        pipeline = loader.load(str(FIXTURES_DIR / "bare-pipeline.yaml"))
        assert pipeline.id == "bare-test"
        assert len(pipeline.slots) == 1

    def test_load_slot_details(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        impl_slot = next(s for s in pipeline.slots if s.id == "slot-implement")
        assert impl_slot.slot_type == "implementer"
        assert impl_slot.depends_on == ["slot-design"]
        assert len(impl_slot.inputs) == 1
        assert impl_slot.inputs[0].from_slot == "slot-design"
        assert impl_slot.task is not None
        assert impl_slot.task.objective == "Implement {feature_name} per design"
        assert impl_slot.execution.timeout_hours == 8.0
        assert impl_slot.execution.max_retries == 1

    def test_load_pre_post_conditions(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        impl_slot = next(s for s in pipeline.slots if s.id == "slot-implement")
        assert len(impl_slot.pre_conditions) == 1
        assert impl_slot.pre_conditions[0].type == "slot_completed"
        assert len(impl_slot.post_conditions) == 1
        assert impl_slot.post_conditions[0].type == "tests_pass"

    def test_load_data_flow(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        assert pipeline.data_flow[0].from_slot == "slot-design"
        assert pipeline.data_flow[0].to_slot == "slot-implement"
        assert pipeline.data_flow[0].artifact == "design_doc"
        assert pipeline.data_flow[0].required is True

    def test_load_missing_file(self, loader):
        with pytest.raises(PipelineLoadError, match="not found"):
            loader.load("/nonexistent/path/pipeline.yaml")

    def test_load_malformed_yaml(self, loader, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{ invalid yaml: [")
        with pytest.raises(PipelineLoadError, match="Malformed YAML"):
            loader.load(str(bad_yaml))

    def test_load_empty_file(self, loader, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        with pytest.raises(PipelineLoadError, match="Empty YAML"):
            loader.load(str(empty))

    def test_load_missing_required_field(self, loader, tmp_path):
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text("id: test\nname: test\n")
        with pytest.raises(PipelineLoadError, match="Missing required fields"):
            loader.load(str(incomplete))

    def test_load_non_dict_yaml(self, loader, tmp_path):
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n")
        with pytest.raises(PipelineLoadError, match="Expected YAML mapping"):
            loader.load(str(list_yaml))


class TestResolve:
    def test_resolve_parameters(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        resolved = loader.resolve(pipeline, {"feature_name": "kline-agg"})
        assert resolved.name == "kline-agg Feature Pipeline"
        assert resolved.description == "Standard feature pipeline for kline-agg"

    def test_resolve_slot_task(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        resolved = loader.resolve(pipeline, {"feature_name": "kline-agg"})
        design_slot = next(s for s in resolved.slots if s.id == "slot-design")
        assert design_slot.task.objective == "Create design for kline-agg"
        assert "kline-agg-design.md" in design_slot.task.deliverables[0]

    def test_resolve_slot_name(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        resolved = loader.resolve(pipeline, {"feature_name": "dashboard"})
        design_slot = next(s for s in resolved.slots if s.id == "slot-design")
        assert design_slot.name == "Design dashboard"

    def test_resolve_output_path(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        resolved = loader.resolve(pipeline, {"feature_name": "kline-agg"})
        design_slot = next(s for s in resolved.slots if s.id == "slot-design")
        assert design_slot.outputs[0].path == "architect/designs/kline-agg-design.md"

    def test_resolve_default_param(self, loader):
        """Default value used when param not provided."""
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        resolved = loader.resolve(pipeline, {"feature_name": "test"})
        # phase_id has default "phase1", should not raise
        assert resolved is not None

    def test_resolve_missing_required_param(self, loader):
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        with pytest.raises(PipelineParameterError, match="feature_name"):
            loader.resolve(pipeline, {})

    def test_resolve_preserves_immutable_pipeline(self, loader):
        """Resolve returns a new Pipeline, does not mutate the original."""
        pipeline = loader.load(str(FIXTURES_DIR / "valid-pipeline.yaml"))
        original_name = pipeline.name
        loader.resolve(pipeline, {"feature_name": "new"})
        assert pipeline.name == original_name


class TestResolveParamTypes:
    def test_int_param(self, loader):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            parameters=[
                Parameter(name="count", type="int", description="c", required=True),
            ],
        )
        resolved = loader.resolve(pipeline, {"count": "42"})
        # param itself is resolved; since it's int it should be coerced
        assert resolved is not None

    def test_bool_param(self, loader):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            parameters=[
                Parameter(name="flag", type="bool", description="f", required=True),
            ],
        )
        resolved = loader.resolve(pipeline, {"flag": "true"})
        assert resolved is not None

    def test_bool_param_invalid(self, loader):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            parameters=[
                Parameter(name="flag", type="bool", description="f", required=True),
            ],
        )
        with pytest.raises(PipelineParameterError, match="expects bool"):
            loader.resolve(pipeline, {"flag": "maybe"})

    def test_list_param_from_string(self, loader):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            parameters=[
                Parameter(name="items", type="list", description="i", required=True),
            ],
        )
        resolved = loader.resolve(pipeline, {"items": "a, b, c"})
        assert resolved is not None

    def test_int_param_invalid(self, loader):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            parameters=[
                Parameter(name="count", type="int", description="c", required=True),
            ],
        )
        with pytest.raises(PipelineParameterError, match="expects int"):
            loader.resolve(pipeline, {"count": "not_a_number"})


class TestLoadAndResolve:
    def test_end_to_end(self, loader):
        pipeline = loader.load_and_resolve(
            str(FIXTURES_DIR / "valid-pipeline.yaml"),
            {"feature_name": "kline-aggregator"},
        )
        assert pipeline.name == "kline-aggregator Feature Pipeline"
        assert pipeline.slots[0].name == "Design kline-aggregator"
        assert pipeline.slots[0].task.objective == "Create design for kline-aggregator"
