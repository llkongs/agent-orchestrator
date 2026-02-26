"""Tests for pipeline.bootstrap -- one-call pipeline engine initialization."""

from __future__ import annotations

import pytest
import yaml

from pipeline.bootstrap import BootstrappedExecutor, boot
from pipeline.auto_executor import AutoExecutorConfig, CallbackExecutor
from pipeline.models import PipelineStatus, SlotStatus
from pipeline.runner import PipelineRunner


@pytest.fixture
def project_root(tmp_path):
    """Create a full project directory structure for bootstrap tests."""
    # Directories
    (tmp_path / "specs" / "pipelines" / "templates").mkdir(parents=True)
    (tmp_path / "specs" / "pipelines" / "slot-types").mkdir(parents=True)
    (tmp_path / "state" / "active").mkdir(parents=True)
    (tmp_path / "state" / "contracts").mkdir(parents=True)
    (tmp_path / "agents").mkdir()

    # Slot types
    (tmp_path / "specs" / "pipelines" / "slot-types" / "implementer.yaml").write_text(
        yaml.dump({
            "slot_type": {
                "id": "implementer",
                "name": "Implementer",
                "category": "engineering",
                "description": "Writes code",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "required_capabilities": ["python"],
            }
        })
    )
    (tmp_path / "specs" / "pipelines" / "slot-types" / "designer.yaml").write_text(
        yaml.dump({
            "slot_type": {
                "id": "designer",
                "name": "Designer",
                "category": "architecture",
                "description": "Designs",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "required_capabilities": ["design"],
            }
        })
    )

    # Agent
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

    # Pipeline template — use "standard-feature" ID so NLMatcher's
    # hardcoded _KEYWORD_MAP can match it
    pipeline_data = {
        "pipeline": {
            "id": "standard-feature",
            "name": "Standard Feature Pipeline",
            "version": "1.0.0",
            "description": "A standard feature pipeline",
            "created_by": "test",
            "created_at": "2026-01-01T00:00:00Z",
            "slots": [
                {
                    "id": "slot-impl",
                    "slot_type": "implementer",
                    "name": "Implement",
                    "task": {"objective": "Implement the feature"},
                },
            ],
        }
    }
    (tmp_path / "specs" / "pipelines" / "templates" / "standard-feature.yaml").write_text(
        yaml.dump(pipeline_data, default_flow_style=False)
    )

    return tmp_path


class TestBoot:
    """Tests for boot() function."""

    def test_returns_tuple(self, project_root):
        auto, runner = boot(str(project_root))
        assert isinstance(auto, BootstrappedExecutor)
        assert isinstance(runner, PipelineRunner)

    def test_default_executor(self, project_root):
        """Default executor is CallbackExecutor (pass-through)."""
        auto, runner = boot(str(project_root))
        # Should work without providing an executor
        pipeline, state = runner.prepare(
            str(project_root / "specs/pipelines/templates/standard-feature.yaml"),
            {},
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-impl"].status == SlotStatus.COMPLETED

    def test_custom_executor(self, project_root):
        """Custom executor is used."""
        called = [False]

        def my_callback(si, aid):
            called[0] = True
            return True

        auto, runner = boot(
            str(project_root),
            executor=CallbackExecutor(my_callback),
        )
        pipeline, state = runner.prepare(
            str(project_root / "specs/pipelines/templates/standard-feature.yaml"),
            {},
        )
        auto.run(pipeline, state)
        assert called[0] is True

    def test_custom_config(self, project_root):
        """Custom config is applied."""
        auto, runner = boot(
            str(project_root),
            config=AutoExecutorConfig(max_parallel=1, dry_run=True),
        )
        pipeline, state = runner.prepare(
            str(project_root / "specs/pipelines/templates/standard-feature.yaml"),
            {},
        )
        final = auto.run(pipeline, state)
        # Dry run → SKIPPED
        assert final.slots["slot-impl"].status == SlotStatus.SKIPPED

    def test_custom_dirs(self, project_root):
        """Custom directory overrides work."""
        # Move templates to a custom dir
        (project_root / "custom-templates").mkdir()
        (project_root / "specs/pipelines/templates/standard-feature.yaml").rename(
            project_root / "custom-templates" / "standard-feature.yaml"
        )

        auto, runner = boot(
            str(project_root),
            templates_dir="custom-templates",
        )
        pipeline, state = runner.prepare(
            str(project_root / "custom-templates/standard-feature.yaml"),
            {},
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-impl"].status == SlotStatus.COMPLETED


class TestBootstrappedExecutor:
    """Tests for BootstrappedExecutor wrapper."""

    def test_run(self, project_root):
        auto, runner = boot(str(project_root))
        pipeline, state = runner.prepare(
            str(project_root / "specs/pipelines/templates/standard-feature.yaml"),
            {},
        )
        final = auto.run(pipeline, state)
        assert final.status == PipelineStatus.COMPLETED

    def test_summary(self, project_root):
        auto, runner = boot(str(project_root))
        pipeline, state = runner.prepare(
            str(project_root / "specs/pipelines/templates/standard-feature.yaml"),
            {},
        )
        final = auto.run(pipeline, state)
        text = auto.summary(final)
        assert "standard-feature" in text
        assert "COMPLETED" in text

    def test_match_preview(self, project_root):
        """match() returns template matches without executing."""
        auto, runner = boot(str(project_root))
        matches = auto.match("implement a new feature")
        assert len(matches) > 0

    def test_run_nl(self, project_root):
        """run_nl() matches and executes from natural language."""
        auto, runner = boot(str(project_root))
        final = auto.run_nl("implement a new feature")
        assert final.status == PipelineStatus.COMPLETED

    def test_run_nl_no_match(self, project_root):
        """run_nl() raises ValueError when no template matches."""
        auto, runner = boot(str(project_root))
        with pytest.raises(ValueError, match="No pipeline template matched"):
            auto.run_nl("xyzzy gibberish no match 12345")

    def test_run_nl_with_param_override(self, project_root):
        """run_nl() merges explicit params with extracted ones."""
        auto, runner = boot(str(project_root))
        final = auto.run_nl(
            "implement a new feature",
            params={"custom_key": "custom_value"},
        )
        assert final.status == PipelineStatus.COMPLETED
