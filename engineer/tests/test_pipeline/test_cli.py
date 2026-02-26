"""Tests for pipeline.cli — CLI interface for the pipeline engine."""

from __future__ import annotations

import json

import pytest
import yaml

from pipeline.cli import main, _global_session_path


@pytest.fixture
def project(tmp_path):
    """Create a minimal project for CLI tests."""
    (tmp_path / "specs" / "pipelines" / "templates").mkdir(parents=True)
    (tmp_path / "specs" / "pipelines" / "slot-types").mkdir(parents=True)
    (tmp_path / "state" / "active").mkdir(parents=True)
    (tmp_path / "agents").mkdir()

    # Slot types
    for st_id, cat, cap in [
        ("designer", "architecture", "design"),
        ("implementer", "engineering", "python"),
    ]:
        (tmp_path / "specs" / "pipelines" / "slot-types" / f"{st_id}.yaml").write_text(
            yaml.dump({
                "slot_type": {
                    "id": st_id, "name": st_id.title(), "category": cat,
                    "description": f"{st_id} slot", "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "required_capabilities": [cap],
                }
            })
        )

    # Agent
    (tmp_path / "agents" / "eng.md").write_text(
        "---\nagent_id: ENG-001\nversion: '1.0'\ncapabilities:\n"
        "  - python\n  - design\ncompatible_slot_types:\n"
        "  - implementer\n  - designer\n---\n# Engineer\n"
    )

    # Two-slot pipeline: design -> implement
    template = {
        "pipeline": {
            "id": "standard-feature", "name": "Standard Feature",
            "version": "1.0.0", "description": "Test pipeline",
            "created_by": "test", "created_at": "2026-01-01T00:00:00Z",
            "slots": [
                {"id": "slot-design", "slot_type": "designer", "name": "Design",
                 "task": {"objective": "Design the feature"}},
                {"id": "slot-impl", "slot_type": "implementer", "name": "Implement",
                 "depends_on": ["slot-design"],
                 "task": {"objective": "Implement the feature"}},
            ],
        }
    }
    (tmp_path / "specs" / "pipelines" / "templates" / "standard-feature.yaml").write_text(
        yaml.dump(template, default_flow_style=False)
    )

    return tmp_path


@pytest.fixture(autouse=True)
def clean_global_session():
    """Clean up global session file before/after each test."""
    path = _global_session_path()
    if path.exists():
        path.unlink()
    yield
    if path.exists():
        path.unlink()


class TestHelp:
    def test_no_args_shows_help(self, capsys):
        ret = main([])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Pipeline Engine CLI" in out

    def test_help_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


class TestTemplates:
    def test_list_templates(self, project, capsys):
        ret = main(["-P", str(project), "templates"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "standard-feature" in out
        assert "Slots: 2" in out

    def test_no_templates_dir(self, tmp_path, capsys):
        ret = main(["-P", str(tmp_path), "templates"])
        assert ret == 1
        out = capsys.readouterr().out
        assert "No templates directory" in out


class TestMatch:
    def test_match_found(self, project, capsys):
        ret = main(["-P", str(project), "match", "implement", "a", "new", "feature"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "standard-feature" in out
        assert "Confidence" in out

    def test_match_not_found(self, project, capsys):
        ret = main(["-P", str(project), "match", "xyzzy", "gibberish"])
        assert ret == 1
        out = capsys.readouterr().out
        assert "No template matched" in out


class TestPrepare:
    def test_prepare_creates_pipeline(self, project, capsys):
        ret = main(["-P", str(project), "prepare", "standard-feature.yaml"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Pipeline created: standard-feature" in out
        assert "slot-design" in out
        assert "slot-impl" in out

    def test_prepare_with_params(self, project, capsys):
        ret = main(["-P", str(project), "prepare", "standard-feature.yaml",
                     "-p", "feature_name=login"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Pipeline created" in out

    def test_prepare_template_not_found(self, project, capsys):
        ret = main(["-P", str(project), "prepare", "nonexistent.yaml"])
        assert ret == 1
        out = capsys.readouterr().out
        assert "not found" in out

    def test_prepare_invalid_param_format(self, project, capsys):
        ret = main(["-P", str(project), "prepare", "standard-feature.yaml",
                     "-p", "badparam"])
        assert ret == 1
        out = capsys.readouterr().out
        assert "Invalid param format" in out

    def test_prepare_saves_session(self, project):
        main(["-P", str(project), "prepare", "standard-feature.yaml"])
        session = json.loads(_global_session_path().read_text())
        assert "state_file" in session
        assert "project_root" in session
        assert session["project_root"] == str(project.resolve())


class TestWorkflow:
    """End-to-end workflow: prepare -> next -> begin -> complete -> summary."""

    def _prepare(self, project):
        main(["-P", str(project), "prepare", "standard-feature.yaml"])

    def test_status_after_prepare(self, project, capsys):
        self._prepare(project)
        ret = main(["status"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "standard-feature" in out
        assert "pending: 2" in out

    def test_next_shows_ready_slot(self, project, capsys):
        self._prepare(project)
        ret = main(["next"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "slot-design" in out
        assert "Design the feature" in out

    def test_begin_slot(self, project, capsys):
        self._prepare(project)
        ret = main(["begin", "slot-design"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Slot started: slot-design" in out
        assert "in_progress" in out

    def test_begin_nonexistent_slot(self, project, capsys):
        self._prepare(project)
        ret = main(["begin", "no-such-slot"])
        assert ret == 1
        out = capsys.readouterr().out
        assert "Slot not found" in out

    def test_complete_slot(self, project, capsys):
        self._prepare(project)
        main(["begin", "slot-design"])
        ret = main(["complete", "slot-design"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Slot completed: slot-design" in out
        assert "slot-impl" in out  # next ready

    def test_complete_nonexistent_slot(self, project, capsys):
        self._prepare(project)
        ret = main(["complete", "no-such-slot"])
        assert ret == 1
        out = capsys.readouterr().out
        assert "Slot not found" in out

    def test_blocked_slot_not_in_next(self, project, capsys):
        self._prepare(project)
        capsys.readouterr()  # flush prepare output
        main(["next"])
        out = capsys.readouterr().out
        assert "slot-impl" not in out  # blocked by slot-design

    def test_full_workflow(self, project, capsys):
        """Complete pipeline: design -> implement -> completed."""
        self._prepare(project)

        main(["begin", "slot-design"])
        main(["complete", "slot-design"])
        main(["begin", "slot-impl"])
        ret = main(["complete", "slot-impl"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "COMPLETED" in out

    def test_summary_after_completion(self, project, capsys):
        self._prepare(project)
        main(["begin", "slot-design"])
        main(["complete", "slot-design"])
        main(["begin", "slot-impl"])
        main(["complete", "slot-impl"])

        ret = main(["summary"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "completed" in out
        assert "COMPLETED" in out


class TestFail:
    def test_fail_slot(self, project, capsys):
        main(["-P", str(project), "prepare", "standard-feature.yaml"])
        main(["begin", "slot-design"])
        ret = main(["fail", "slot-design", "Agent", "crashed"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Slot failed: slot-design" in out
        assert "Agent crashed" in out

    def test_fail_nonexistent_slot(self, project, capsys):
        main(["-P", str(project), "prepare", "standard-feature.yaml"])
        ret = main(["fail", "no-such-slot", "error"])
        assert ret == 1


class TestSkip:
    def test_skip_slot(self, project, capsys):
        main(["-P", str(project), "prepare", "standard-feature.yaml"])
        ret = main(["skip", "slot-design"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Slot skipped: slot-design" in out

    def test_skip_unblocks_dependent(self, project, capsys):
        main(["-P", str(project), "prepare", "standard-feature.yaml"])
        main(["skip", "slot-design"])
        ret = main(["next"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "slot-impl" in out  # unblocked by skip

    def test_skip_nonexistent_slot(self, project, capsys):
        main(["-P", str(project), "prepare", "standard-feature.yaml"])
        ret = main(["skip", "no-such-slot"])
        assert ret == 1


class TestNoSession:
    def test_status_without_prepare(self, capsys):
        with pytest.raises(SystemExit):
            main(["status"])

    def test_next_without_prepare(self, capsys):
        with pytest.raises(SystemExit):
            main(["next"])
