"""Tests for pipeline.nl_matcher -- Natural language template matching."""

import pytest
import yaml

from src.pipeline.nl_matcher import NLMatcher, TemplateMatch


@pytest.fixture
def templates_dir(tmp_path):
    """Create a temp directory with sample pipeline templates."""
    d = tmp_path / "templates"
    d.mkdir()

    # Standard feature template
    (d / "standard-feature.yaml").write_text(
        yaml.dump(
            {
                "pipeline": {
                    "id": "standard-feature",
                    "name": "Standard Feature Development",
                    "description": "Develop a new feature end-to-end",
                    "version": "1.0.0",
                    "created_by": "test",
                    "created_at": "2026-01-01",
                    "parameters": [
                        {"name": "feature_name", "type": "string", "required": True},
                        {"name": "phase_id", "type": "string", "required": True},
                    ],
                }
            }
        )
    )

    # Hotfix template
    (d / "hotfix.yaml").write_text(
        yaml.dump(
            {
                "pipeline": {
                    "id": "hotfix",
                    "name": "Hotfix",
                    "description": "Emergency bug fix pipeline",
                    "version": "1.0.0",
                    "created_by": "test",
                    "created_at": "2026-01-01",
                    "parameters": [
                        {"name": "bug_id", "type": "string", "required": True},
                    ],
                }
            }
        )
    )

    # Research template
    (d / "research-task.yaml").write_text(
        yaml.dump(
            {
                "pipeline": {
                    "id": "research-task",
                    "name": "Research Task",
                    "description": "Research and investigation pipeline",
                    "version": "1.0.0",
                    "created_by": "test",
                    "created_at": "2026-01-01",
                }
            }
        )
    )

    # Quant strategy template
    (d / "quant-strategy.yaml").write_text(
        yaml.dump(
            {
                "pipeline": {
                    "id": "quant-strategy",
                    "name": "Quant Strategy",
                    "description": "Quantitative trading strategy development",
                    "version": "1.0.0",
                    "created_by": "test",
                    "created_at": "2026-01-01",
                }
            }
        )
    )

    # Security hardening template
    (d / "security-hardening.yaml").write_text(
        yaml.dump(
            {
                "pipeline": {
                    "id": "security-hardening",
                    "name": "Security Hardening",
                    "description": "Security audit and hardening pipeline",
                    "version": "1.0.0",
                    "created_by": "test",
                    "created_at": "2026-01-01",
                }
            }
        )
    )

    return d


@pytest.fixture
def matcher(templates_dir):
    return NLMatcher(str(templates_dir))


# ===================================================================
# Template loading
# ===================================================================


class TestTemplateLoading:
    def test_loads_all_templates(self, matcher):
        assert len(matcher._templates) == 5

    def test_template_ids(self, matcher):
        assert "standard-feature" in matcher._templates
        assert "hotfix" in matcher._templates
        assert "research-task" in matcher._templates

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        m = NLMatcher(str(d))
        assert len(m._templates) == 0

    def test_nonexistent_dir(self, tmp_path):
        m = NLMatcher(str(tmp_path / "nonexistent"))
        assert len(m._templates) == 0

    def test_invalid_yaml_skipped(self, tmp_path):
        d = tmp_path / "templates"
        d.mkdir()
        (d / "bad.yaml").write_text(":\n  bad:\n - ][")
        m = NLMatcher(str(d))
        assert len(m._templates) == 0


# ===================================================================
# match -- English
# ===================================================================


class TestMatchEnglish:
    def test_feature_request(self, matcher):
        results = matcher.match("I want to implement a new feature for kline aggregation")
        assert len(results) > 0
        assert results[0].template_id == "standard-feature"
        assert results[0].confidence > 0.1

    def test_hotfix_request(self, matcher):
        results = matcher.match("There is an urgent bug crash in the system")
        top_ids = [r.template_id for r in results]
        assert "hotfix" in top_ids

    def test_research_request(self, matcher):
        results = matcher.match("We need to research and investigate websocket performance")
        top_ids = [r.template_id for r in results]
        assert "research-task" in top_ids

    def test_strategy_request(self, matcher):
        results = matcher.match("Develop a new trading strategy with backtest for BTC/USDT")
        top_ids = [r.template_id for r in results]
        assert "quant-strategy" in top_ids

    def test_security_request(self, matcher):
        results = matcher.match("Run a security audit to find vulnerabilities")
        top_ids = [r.template_id for r in results]
        assert "security-hardening" in top_ids

    def test_no_match(self, matcher):
        results = matcher.match("completely unrelated gibberish xyzzy")
        assert len(results) == 0

    def test_sorted_by_confidence(self, matcher):
        results = matcher.match("implement a new feature")
        if len(results) > 1:
            confidences = [r.confidence for r in results]
            assert confidences == sorted(confidences, reverse=True)


# ===================================================================
# match -- Chinese
# ===================================================================


class TestMatchChinese:
    def test_feature_chinese(self, matcher):
        results = matcher.match("开发一个新功能实现K线聚合")
        top_ids = [r.template_id for r in results]
        assert "standard-feature" in top_ids

    def test_research_chinese(self, matcher):
        results = matcher.match("调研分析WebSocket性能优化方案")
        top_ids = [r.template_id for r in results]
        assert "research-task" in top_ids

    def test_security_chinese(self, matcher):
        results = matcher.match("安全审计漏洞扫描")
        top_ids = [r.template_id for r in results]
        assert "security-hardening" in top_ids

    def test_hotfix_chinese(self, matcher):
        results = matcher.match("紧急修复系统崩溃故障")
        top_ids = [r.template_id for r in results]
        assert "hotfix" in top_ids


# ===================================================================
# extract_params
# ===================================================================


class TestExtractParams:
    def test_extract_symbol(self, matcher):
        params = matcher.extract_params(
            "backtest strategy for BTC/USDT", "quant-strategy"
        )
        assert params["target_symbol"] == "BTC/USDT"

    def test_extract_phase(self, matcher):
        params = matcher.extract_params(
            "implement feature in phase5", "standard-feature"
        )
        assert params["phase_id"] == "phase5"

    def test_extract_phase_chinese(self, matcher):
        params = matcher.extract_params(
            "开发阶段3的功能", "standard-feature"
        )
        assert params["phase_id"] == "phase3"

    def test_extract_bug_id(self, matcher):
        params = matcher.extract_params(
            "hotfix for bug P1-042", "hotfix"
        )
        assert params["bug_id"] == "P1-042"

    def test_extract_feature_name(self, matcher):
        params = matcher.extract_params(
            "implement feature kline-aggregator in phase5", "standard-feature"
        )
        assert params["feature_name"] == "kline-aggregator"

    def test_extract_strategy_name(self, matcher):
        params = matcher.extract_params(
            "develop strategy mean-reversion for BTC/USDT", "quant-strategy"
        )
        assert params["strategy_name"] == "mean-reversion"

    def test_extract_module(self, matcher):
        params = matcher.extract_params(
            "fix module risk in phase2", "standard-feature"
        )
        assert params["target_module"] == "risk"

    def test_no_params_extracted(self, matcher):
        params = matcher.extract_params("just some random text", "hotfix")
        assert isinstance(params, dict)

    def test_multiple_params(self, matcher):
        params = matcher.extract_params(
            "implement feature dashboard in phase5 for module strategy",
            "standard-feature",
        )
        assert params.get("feature_name") == "dashboard"
        assert params.get("phase_id") == "phase5"
        assert params.get("target_module") == "strategy"


# ===================================================================
# generate_summary
# ===================================================================


class TestGenerateSummary:
    def test_summary_with_params(self, matcher):
        match = TemplateMatch(
            template_id="standard-feature",
            template_path="/path/to/template.yaml",
            confidence=0.85,
            matched_keywords=["feature", "implement"],
            description="Develop a new feature end-to-end",
            suggested_params={"feature_name": "dashboard"},
        )
        summary = matcher.generate_summary(
            match, {"feature_name": "dashboard", "phase_id": "phase5"}
        )
        assert "standard-feature" in summary
        assert "feature_name: dashboard" in summary
        assert "phase_id: phase5" in summary
        assert "0.85" in summary

    def test_summary_no_params(self, matcher):
        match = TemplateMatch(
            template_id="research-task",
            template_path="/path/to/template.yaml",
            confidence=0.5,
            matched_keywords=["research"],
            description="Research task",
            suggested_params={},
        )
        summary = matcher.generate_summary(match, {})
        assert "(none)" in summary


# ===================================================================
# _tokenize
# ===================================================================


class TestTokenize:
    def test_basic_tokenize(self):
        tokens = NLMatcher._tokenize("Hello World")
        assert "hello" in tokens
        assert "world" in tokens

    def test_chinese_tokenize(self):
        tokens = NLMatcher._tokenize("开发新功能")
        # Chinese characters should be captured
        assert len(tokens) > 0

    def test_mixed_tokenize(self):
        tokens = NLMatcher._tokenize("implement 功能 in phase5")
        assert "implement" in tokens
        assert "phase5" in tokens

    def test_punctuation_stripped(self):
        tokens = NLMatcher._tokenize("hello, world! foo-bar")
        assert "hello" in tokens
        assert "world" in tokens
