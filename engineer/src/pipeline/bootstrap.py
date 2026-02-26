"""One-call bootstrap for the pipeline engine.

Usage (in target project's CLAUDE.md):

    ```python
    import sys
    sys.path.insert(0, "engine/src")  # adjust path to pipeline source

    from pipeline.bootstrap import boot

    auto, runner = boot("/path/to/project")

    # Option A: Natural language -> auto execute
    final_state = auto.run_nl("开发一个新功能实现K线聚合")

    # Option B: Explicit template + params
    pipeline, state = runner.prepare("templates/standard-feature.yaml", {
        "feature_name": "kline-aggregator",
    })
    final_state = auto.run(pipeline, state)

    print(runner.get_summary(final_state))
    ```

Provides sensible defaults for all components.  Override anything via kwargs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.auto_executor import (
    AgentExecutor,
    AutoExecutor,
    AutoExecutorConfig,
    CallbackExecutor,
)
from pipeline.nl_matcher import NLMatcher
from pipeline.models import Pipeline, PipelineState
from pipeline.runner import PipelineRunner
from pipeline.slot_contract import SlotContractManager
from pipeline.slot_registry import SlotRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_DIRS = {
    "templates_dir": "specs/pipelines/templates",
    "state_dir": "state/active",
    "slot_types_dir": "specs/pipelines/slot-types",
    "agents_dir": "agents",
    "contracts_dir": "state/contracts",
}


# ---------------------------------------------------------------------------
# BootstrappedExecutor — wraps AutoExecutor + NLMatcher
# ---------------------------------------------------------------------------


class BootstrappedExecutor:
    """Convenience wrapper that bundles AutoExecutor + NLMatcher.

    Returned by boot().  Provides run() for explicit pipelines
    and run_nl() for natural-language-triggered execution.
    """

    def __init__(
        self,
        auto: AutoExecutor,
        runner: PipelineRunner,
        matcher: NLMatcher,
    ) -> None:
        self._auto = auto
        self._runner = runner
        self._matcher = matcher

    # --- Delegated to AutoExecutor ---

    def run(
        self, pipeline: Pipeline, state: PipelineState
    ) -> PipelineState:
        """Execute a prepared pipeline to completion."""
        return self._auto.run(pipeline, state)

    def run_single_slot(self, slot, pipeline, state):
        """Execute a single slot."""
        return self._auto.run_single_slot(slot, pipeline, state)

    # --- Natural language entry point ---

    def run_nl(
        self,
        user_request: str,
        params: dict[str, Any] | None = None,
    ) -> PipelineState:
        """Match a natural-language request to a template and execute.

        Args:
            user_request: Free-text request (English or Chinese).
            params: Optional parameter overrides.  Extracted params
                from NLMatcher are used as defaults.

        Returns:
            Final PipelineState.

        Raises:
            ValueError: No matching template found.
        """
        matches = self._matcher.match(user_request)
        if not matches:
            raise ValueError(
                f"No pipeline template matched: {user_request!r}"
            )

        best = matches[0]
        logger.info(
            "Matched template: %s (confidence=%.2f)",
            best.template_id, best.confidence,
        )

        # Merge suggested params with explicit overrides
        merged_params: dict[str, Any] = {}
        if best.suggested_params:
            merged_params.update(best.suggested_params)
        if params:
            merged_params.update(params)

        pipeline, state = self._runner.prepare(
            best.template_path, merged_params
        )

        logger.info(
            "Pipeline %s v%s prepared (%d slots)",
            pipeline.id, pipeline.version, len(pipeline.slots),
        )

        return self._auto.run(pipeline, state)

    def match(self, user_request: str):
        """Preview which template would match (without executing)."""
        return self._matcher.match(user_request)

    def summary(self, state: PipelineState) -> str:
        """Get human-readable pipeline status."""
        return self._runner.get_summary(state)


# ---------------------------------------------------------------------------
# boot() — the one-call entry point
# ---------------------------------------------------------------------------


def boot(
    project_root: str,
    *,
    executor: AgentExecutor | None = None,
    config: AutoExecutorConfig | None = None,
    assignments: list | None = None,
    templates_dir: str | None = None,
    state_dir: str | None = None,
    slot_types_dir: str | None = None,
    agents_dir: str | None = None,
    contracts_dir: str | None = None,
) -> tuple[BootstrappedExecutor, PipelineRunner]:
    """Bootstrap the full pipeline engine in one call.

    Args:
        project_root: Absolute path to the project root.
        executor: AgentExecutor implementation.
            Defaults to CallbackExecutor (pass-through, for testing).
        config: AutoExecutorConfig.  Defaults to max_parallel=4.
        assignments: Explicit SlotAssignment list (optional).
        templates_dir: Override templates directory.
        state_dir: Override state directory.
        slot_types_dir: Override slot-types directory.
        agents_dir: Override agents directory.
        contracts_dir: Override contracts directory.

    Returns:
        (bootstrapped_executor, runner) tuple.

    Usage:
        auto, runner = boot("/path/to/project")
        final = auto.run_nl("implement a login feature")
        print(auto.summary(final))
    """
    root = Path(project_root).resolve()

    # Resolve directories
    t_dir = str(root / (templates_dir or _DEFAULT_DIRS["templates_dir"]))
    s_dir = str(root / (state_dir or _DEFAULT_DIRS["state_dir"]))
    st_dir = str(root / (slot_types_dir or _DEFAULT_DIRS["slot_types_dir"]))
    a_dir = str(root / (agents_dir or _DEFAULT_DIRS["agents_dir"]))
    c_dir = str(root / (contracts_dir or _DEFAULT_DIRS["contracts_dir"]))

    # Create components
    runner = PipelineRunner(
        project_root=str(root),
        templates_dir=t_dir,
        state_dir=s_dir,
        slot_types_dir=st_dir,
        agents_dir=a_dir,
    )

    contract_mgr = SlotContractManager(str(root), c_dir)
    registry = SlotRegistry(st_dir, a_dir)
    matcher = NLMatcher(t_dir)

    if executor is None:
        executor = CallbackExecutor(lambda si, aid: True)

    if config is None:
        config = AutoExecutorConfig(max_parallel=4)

    auto_executor = AutoExecutor(
        runner,
        executor,
        contract_mgr,
        registry,
        config=config,
        assignments=assignments,
        project_root=str(root),
    )

    bootstrapped = BootstrappedExecutor(auto_executor, runner, matcher)

    logger.info("Pipeline engine bootstrapped at %s", root)

    return bootstrapped, runner
