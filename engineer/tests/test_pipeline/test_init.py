"""Tests for pipeline.__init__ -- Public API re-exports."""

import pipeline


class TestPublicAPI:
    """Verify all expected symbols are importable from the top-level package."""

    def test_models_exports(self):
        assert hasattr(pipeline, "SlotStatus")
        assert hasattr(pipeline, "PipelineStatus")
        assert hasattr(pipeline, "ArtifactType")
        assert hasattr(pipeline, "ConditionType")
        assert hasattr(pipeline, "ValidationLevel")
        assert hasattr(pipeline, "Parameter")
        assert hasattr(pipeline, "ArtifactRef")
        assert hasattr(pipeline, "ArtifactOutput")
        assert hasattr(pipeline, "Gate")
        assert hasattr(pipeline, "DataFlowEdge")
        assert hasattr(pipeline, "GateCheckResult")
        assert hasattr(pipeline, "SlotTask")
        assert hasattr(pipeline, "ExecutionConfig")
        assert hasattr(pipeline, "Slot")
        assert hasattr(pipeline, "Pipeline")
        assert hasattr(pipeline, "SlotState")
        assert hasattr(pipeline, "PipelineState")
        assert hasattr(pipeline, "SlotTypeDefinition")
        assert hasattr(pipeline, "AgentCapabilities")
        assert hasattr(pipeline, "CapabilityMatch")
        assert hasattr(pipeline, "SlotAssignment")

    def test_loader_exports(self):
        assert hasattr(pipeline, "PipelineLoader")
        assert hasattr(pipeline, "PipelineLoadError")
        assert hasattr(pipeline, "PipelineParameterError")

    def test_validator_exports(self):
        assert hasattr(pipeline, "PipelineValidator")
        assert hasattr(pipeline, "PipelineCycleError")
        assert hasattr(pipeline, "ValidationResult")

    def test_state_exports(self):
        assert hasattr(pipeline, "PipelineStateTracker")

    def test_slot_registry_exports(self):
        assert hasattr(pipeline, "SlotRegistry")
        assert hasattr(pipeline, "SlotTypeNotFoundError")

    def test_gate_checker_exports(self):
        assert hasattr(pipeline, "GateChecker")

    def test_runner_exports(self):
        assert hasattr(pipeline, "PipelineRunner")
        assert hasattr(pipeline, "PipelineExecutionError")

    def test_nl_matcher_exports(self):
        assert hasattr(pipeline, "NLMatcher")
        assert hasattr(pipeline, "TemplateMatch")

    def test_all_list_complete(self):
        """Verify __all__ contains all expected names."""
        assert len(pipeline.__all__) >= 30
        for name in pipeline.__all__:
            assert hasattr(pipeline, name), f"Missing: {name}"

    def test_runner_instantiation(self, tmp_path):
        """Smoke test: PipelineRunner can be instantiated."""
        (tmp_path / "templates").mkdir()
        (tmp_path / "state").mkdir()
        (tmp_path / "slot-types").mkdir()
        (tmp_path / "agents").mkdir()
        runner = pipeline.PipelineRunner(
            project_root=str(tmp_path),
            templates_dir=str(tmp_path / "templates"),
            state_dir=str(tmp_path / "state"),
            slot_types_dir=str(tmp_path / "slot-types"),
            agents_dir=str(tmp_path / "agents"),
        )
        assert runner is not None
