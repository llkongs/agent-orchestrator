"""Tests for pipeline.ov_context_router -- OpenViking-backed context router."""

import json
import subprocess

import pytest

from src.pipeline.ov_context_router import OVContextRouter
from src.pipeline.models import ContextItem, ContextTier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def router(tmp_path):
    return OVContextRouter(
        str(tmp_path),
        ov_binary="ov",
        ov_namespace="viking://test-project",
    )


# ---------------------------------------------------------------------------
# _run_ov
# ---------------------------------------------------------------------------


class TestRunOv:
    def test_run_ov_success(self, router, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, stdout="ok\n", stderr=""),
        )
        result = router._run_ov(["health"])
        assert result == "ok\n"

    def test_run_ov_nonzero_returncode(self, router, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, stdout="", stderr="error"),
        )
        result = router._run_ov(["health"])
        assert result is None

    def test_run_ov_binary_not_found(self, router, monkeypatch):
        def raise_fnf(*a, **kw):
            raise FileNotFoundError("ov not found")

        monkeypatch.setattr(subprocess, "run", raise_fnf)
        result = router._run_ov(["health"])
        assert result is None
        assert router._available is False

    def test_run_ov_timeout(self, router, monkeypatch):
        def raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="ov", timeout=30)

        monkeypatch.setattr(subprocess, "run", raise_timeout)
        result = router._run_ov(["health"])
        assert result is None

    def test_run_ov_generic_exception(self, router, monkeypatch):
        def raise_err(*a, **kw):
            raise OSError("something went wrong")

        monkeypatch.setattr(subprocess, "run", raise_err)
        result = router._run_ov(["health"])
        assert result is None


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    def test_available_when_health_succeeds(self, router, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, stdout="ok", stderr=""),
        )
        assert router.is_available is True

    def test_unavailable_when_health_fails(self, router, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, stdout="", stderr="err"),
        )
        assert router.is_available is False

    def test_is_available_caches_result(self, router, monkeypatch):
        call_count = 0

        def counting_run(*a, **kw):
            nonlocal call_count
            call_count += 1
            return subprocess.CompletedProcess(a[0], 0, stdout="ok", stderr="")

        monkeypatch.setattr(subprocess, "run", counting_run)
        _ = router.is_available
        _ = router.is_available
        assert call_count == 1


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------


class TestBuildContext:
    def test_returns_none_when_unavailable(self, router, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, stdout="", stderr="err"),
        )
        result = router.build_context("implementer")
        assert result is None

    def test_build_context_returns_items(self, router, monkeypatch):
        """Simulate ov abstract + ov ls + ov overview + ov find."""
        call_seq = []

        def mock_run(args, **kw):
            call_seq.append(args[1] if len(args) > 1 else "?")
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "health":
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")
            if cmd == "abstract":
                return subprocess.CompletedProcess(args, 0, stdout="Project abstract text.", stderr="")
            if cmd == "ls":
                return subprocess.CompletedProcess(args, 0, stdout="pipeline\nspecs\n", stderr="")
            if cmd == "overview":
                return subprocess.CompletedProcess(args, 0, stdout="Overview content here.", stderr="")
            if cmd == "find":
                data = [
                    {"uri": "viking://test/pipeline/runner.py", "score": 0.85, "content": "runner code"},
                ]
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(data), stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="unknown")

        monkeypatch.setattr(subprocess, "run", mock_run)
        items = router.build_context("implementer", "Build the runner module")
        assert items is not None
        assert len(items) > 0
        # Check duck-typing (src.pipeline vs pipeline import paths differ)
        for item in items:
            assert hasattr(item, "path")
            assert hasattr(item, "tier")
            assert hasattr(item, "relevance")
            assert hasattr(item, "tokens_estimate")

    def test_build_context_respects_max_tokens(self, router, monkeypatch):
        def mock_run(args, **kw):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "health":
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")
            if cmd == "abstract":
                return subprocess.CompletedProcess(args, 0, stdout="A" * 200, stderr="")
            if cmd == "ls":
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        items = router.build_context("implementer", max_tokens=10)
        # With max_tokens=10, the 200-char abstract (50 tokens) should be excluded
        assert items is not None
        abstract_items = [i for i in items if i.tier == ContextTier.L0]
        assert len(abstract_items) == 0


# ---------------------------------------------------------------------------
# semantic_search
# ---------------------------------------------------------------------------


class TestSemanticSearch:
    def test_returns_empty_when_unavailable(self, router, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, stdout="", stderr="err"),
        )
        result = router.semantic_search("test query")
        assert result == []

    def test_parses_list_response(self, router, monkeypatch):
        data = [
            {"uri": "viking://test/foo.py", "score": 0.9, "content": "foo content"},
            {"uri": "viking://test/bar.py", "score": 0.7, "content": "bar content"},
        ]

        def mock_run(args, **kw):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "health":
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")
            if cmd == "find":
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(data), stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        results = router.semantic_search("test query")
        assert len(results) == 2
        assert results[0].path == "viking://test/foo.py"
        assert results[0].relevance == 0.9
        assert results[1].relevance == 0.7

    def test_parses_object_response(self, router, monkeypatch):
        data = {
            "results": [
                {"uri": "viking://test/baz.py", "score": 0.6, "content": "baz"},
            ]
        }

        def mock_run(args, **kw):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "health":
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")
            if cmd == "find":
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(data), stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        results = router.semantic_search("test query")
        assert len(results) == 1
        assert results[0].path == "viking://test/baz.py"

    def test_caps_relevance_at_1(self, router, monkeypatch):
        data = [{"uri": "viking://test/x.py", "score": 1.5, "content": "x"}]

        def mock_run(args, **kw):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "health":
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")
            if cmd == "find":
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(data), stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        results = router.semantic_search("query")
        assert results[0].relevance == 1.0

    def test_handles_invalid_json(self, router, monkeypatch):
        def mock_run(args, **kw):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "health":
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")
            if cmd == "find":
                return subprocess.CompletedProcess(args, 0, stdout="not json{", stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        results = router.semantic_search("query")
        assert results == []


# ---------------------------------------------------------------------------
# get_relations
# ---------------------------------------------------------------------------


class TestGetRelations:
    def test_returns_relations_list(self, router, monkeypatch):
        data = [
            {"uri": "viking://test/a"},
            {"uri": "viking://test/b"},
        ]

        def mock_run(args, **kw):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "relations":
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(data), stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        rels = router.get_relations("viking://test/x")
        assert rels == ["viking://test/a", "viking://test/b"]

    def test_returns_empty_on_failure(self, router, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, stdout="", stderr="err"),
        )
        rels = router.get_relations("viking://test/x")
        assert rels == []

    def test_handles_object_response(self, router, monkeypatch):
        data = {"relations": [{"uri": "viking://test/rel1"}]}

        def mock_run(args, **kw):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "relations":
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(data), stderr="")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        rels = router.get_relations("viking://test/x")
        assert rels == ["viking://test/rel1"]
