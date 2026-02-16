"""Natural language template matching for pipeline selection.

Matches free-text requests (English or Chinese) to pipeline templates
using keyword matching and regex pattern extraction.  No LLM calls --
purely deterministic keyword + regex scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeline.loader import PipelineLoader


@dataclass(frozen=True)
class TemplateMatch:
    """Result of matching a natural language input to a template."""

    template_id: str
    template_path: str
    confidence: float  # 0.0 - 1.0
    matched_keywords: list[str]
    description: str
    suggested_params: dict[str, Any]


# Keyword definitions per template id.
# Keys = template id, values = (weight, keywords list).
# Keywords include both English and Chinese terms.
_KEYWORD_MAP: dict[str, tuple[float, list[str]]] = {
    "standard-feature": (
        1.0,
        [
            "feature",
            "implement",
            "develop",
            "build",
            "create",
            "add",
            "new",
            "功能",
            "开发",
            "实现",
            "新增",
            "构建",
        ],
    ),
    "research-task": (
        1.0,
        [
            "research",
            "investigate",
            "explore",
            "study",
            "analyze",
            "survey",
            "调研",
            "研究",
            "探索",
            "分析",
            "调查",
        ],
    ),
    "quant-strategy": (
        1.2,
        [
            "strategy",
            "quant",
            "trading",
            "backtest",
            "signal",
            "alpha",
            "策略",
            "量化",
            "交易",
            "回测",
            "信号",
        ],
    ),
    "security-hardening": (
        1.1,
        [
            "security",
            "audit",
            "vulnerability",
            "hardening",
            "fix",
            "cve",
            "安全",
            "审计",
            "漏洞",
            "加固",
            "修复",
        ],
    ),
    "hotfix": (
        1.3,
        [
            "hotfix",
            "emergency",
            "urgent",
            "bug",
            "crash",
            "broken",
            "紧急",
            "热修",
            "崩溃",
            "故障",
            "修复",
        ],
    ),
}


class NLMatcher:
    """Matches natural language input to pipeline templates.

    Scans a templates directory at init time and builds a keyword index.
    The match() method scores each template against the input and returns
    candidates sorted by confidence.
    """

    def __init__(self, templates_dir: str) -> None:
        self._templates_dir = Path(templates_dir)
        self._templates: dict[str, dict[str, Any]] = {}
        self._loader = PipelineLoader()
        self._load_templates()

    def match(self, nl_input: str) -> list[TemplateMatch]:
        """Find matching templates for a natural language input.

        Algorithm:
        1. Tokenize input (Unicode-aware)
        2. For each template, count keyword matches
        3. Score = matched / total * weight
        4. Apply regex pattern bonuses
        5. Sort by score descending
        6. Return candidates with confidence > 0.1

        Returns:
            List of TemplateMatch sorted by confidence (descending).
        """
        tokens = self._tokenize(nl_input)
        lower_input = nl_input.lower()
        results: list[TemplateMatch] = []

        for template_id, meta in self._templates.items():
            weight, keywords = _KEYWORD_MAP.get(template_id, (1.0, []))
            if not keywords:
                continue

            matched = []
            for kw in keywords:
                if kw.lower() in lower_input or kw.lower() in tokens:
                    matched.append(kw)

            if not matched:
                continue

            score = (len(matched) / len(keywords)) * weight

            # Bonus for exact template name match
            if template_id in lower_input:
                score += 0.15

            # Cap at 1.0
            confidence = min(score, 1.0)
            if confidence < 0.1:
                continue

            suggested_params = self.extract_params(nl_input, template_id)

            results.append(
                TemplateMatch(
                    template_id=template_id,
                    template_path=meta.get("path", ""),
                    confidence=round(confidence, 3),
                    matched_keywords=matched,
                    description=meta.get("description", ""),
                    suggested_params=suggested_params,
                )
            )

        results.sort(key=lambda m: m.confidence, reverse=True)
        return results

    def extract_params(
        self, nl_input: str, template_id: str
    ) -> dict[str, Any]:
        """Extract parameter values from natural language.

        Pattern-based extraction:
        - Trading symbol: r'[A-Z]{2,10}/[A-Z]{2,10}'
        - Feature name: alphanumeric-kebab words after "feature" or "功能"
        - Phase id: r'phase[-_]?(\\d+)' or r'阶段\\s*(\\d+)'
        - Bug id: r'[A-Z]{1,4}-\\d{1,4}'

        Returns:
            Dict of extracted params. Missing params keep template defaults.
        """
        params: dict[str, Any] = {}

        # Trading symbol: BTC/USDT, ETH/BTC
        symbol_match = re.search(r"[A-Z]{2,10}/[A-Z]{2,10}", nl_input)
        if symbol_match:
            params["target_symbol"] = symbol_match.group()

        # Phase id: phase5, phase-2, 阶段3
        phase_match = re.search(
            r"phase[-_]?(\d+)", nl_input, re.IGNORECASE
        )
        if not phase_match:
            phase_match = re.search(r"阶段\s*(\d+)", nl_input)
        if phase_match:
            params["phase_id"] = f"phase{phase_match.group(1)}"

        # Bug id: P0-001, P1-042, KI-003
        bug_match = re.search(r"[A-Z]{1,4}\d?-\d{1,4}", nl_input)
        if bug_match:
            params["bug_id"] = bug_match.group()

        # Feature name: word after "feature" or "功能"
        feature_match = re.search(
            r"(?:feature|功能)\s+[\"']?(\S+)[\"']?", nl_input, re.IGNORECASE
        )
        if feature_match:
            name = feature_match.group(1).strip("\"'")
            params["feature_name"] = name

        # Strategy name
        strategy_match = re.search(
            r"(?:strategy|策略)\s+[\"']?(\S+)[\"']?",
            nl_input,
            re.IGNORECASE,
        )
        if strategy_match:
            params["strategy_name"] = strategy_match.group(1).strip("\"'")

        # Module name: after "module" or "模块"
        module_match = re.search(
            r"(?:module|模块)\s+[\"']?(\S+)[\"']?", nl_input, re.IGNORECASE
        )
        if module_match:
            params["target_module"] = module_match.group(1).strip("\"'")
            params["affected_module"] = module_match.group(1).strip("\"'")

        return params

    def generate_summary(
        self, match: TemplateMatch, params: dict[str, Any]
    ) -> str:
        """Generate human-readable pipeline summary for CEO review.

        Format:
            Template: {name} ({id})
            Parameters:
              - key: value
            Confidence: 0.85
        """
        lines = [
            f"Template: {match.description.strip()[:60]} ({match.template_id})",
            "Parameters:",
        ]
        if params:
            for k, v in params.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append("  (none)")
        lines.append(f"Confidence: {match.confidence}")
        return "\n".join(lines)

    # --- Private helpers ---

    def _load_templates(self) -> None:
        """Scan templates_dir for YAML files and extract metadata."""
        if not self._templates_dir.exists():
            return

        for path in sorted(self._templates_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if data is None:
                    continue
                pipeline_data = data.get("pipeline", data)
                template_id = pipeline_data.get("id", path.stem)
                self._templates[template_id] = {
                    "path": str(path),
                    "name": pipeline_data.get("name", ""),
                    "description": pipeline_data.get("description", ""),
                    "parameters": pipeline_data.get("parameters", []),
                }
            except Exception:
                continue

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Tokenize text into lowercase word tokens (Unicode-aware)."""
        # Split on whitespace and punctuation, keep Unicode chars
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
        return set(tokens)
