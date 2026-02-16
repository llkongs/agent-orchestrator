"""Pipeline orchestration engine.

Coordinates loader, validator, state tracker, slot registry, and gate
checker to execute a pipeline DAG step by step.  The runner is the only
module that instantiates and wires together all other modules.
"""

from __future__ import annotations

from typing import Any

from pipeline.gate_checker import GateChecker
from pipeline.loader import PipelineLoader
from pipeline.models import (
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotStatus,
)
from pipeline.slot_registry import SlotRegistry
from pipeline.state import PipelineStateTracker
from pipeline.validator import PipelineValidator


class PipelineExecutionError(Exception):
    """Raised on unrecoverable pipeline execution errors."""


class PipelineRunner:
    """Top-level pipeline orchestration engine.

    Usage:
        runner = PipelineRunner(...)
        pipeline, state = runner.prepare("path.yaml", params)
        next_slots = runner.get_next_slots(pipeline, state)
        state = runner.begin_slot(next_slots[0], pipeline, state, agent_id="ENG-001")
        # ... agent executes externally ...
        state = runner.complete_slot(next_slots[0].id, pipeline, state)
    """

    def __init__(
        self,
        project_root: str,
        templates_dir: str,
        state_dir: str,
        slot_types_dir: str,
        agents_dir: str,
    ) -> None:
        self._project_root = project_root
        self._loader = PipelineLoader()
        self._validator = PipelineValidator(project_root)
        self._state_tracker = PipelineStateTracker(state_dir)
        self._registry = SlotRegistry(slot_types_dir, agents_dir)
        self._gate_checker = GateChecker(project_root)

    # --- Core lifecycle ---

    def prepare(
        self, yaml_path: str, params: dict[str, Any]
    ) -> tuple[Pipeline, PipelineState]:
        """Load, resolve, validate pipeline, and init state.

        Steps:
        1. loader.load_and_resolve(yaml_path, params)
        2. validator.validate(pipeline) -- raise on errors
        3. validator.check_slot_types(pipeline, registry) -- warn only
        4. state_tracker.init_state(pipeline, params)

        Returns:
            (pipeline, state) tuple ready for execution.

        Raises:
            PipelineLoadError: Loading failed.
            PipelineParameterError: Parameter resolution failed.
            PipelineExecutionError: Validation failed.
        """
        pipeline = self._loader.load_and_resolve(yaml_path, params)

        result = self._validator.validate(pipeline)
        if not result.is_valid:
            raise PipelineExecutionError(
                f"Pipeline validation failed: {'; '.join(result.errors)}"
            )

        # Slot type check -- non-fatal (warn only)
        self._registry.load_slot_types()
        slot_type_errors = self._validator.check_slot_types(
            pipeline, self._registry
        )
        if slot_type_errors:
            raise PipelineExecutionError(
                f"Slot type validation failed: {'; '.join(slot_type_errors)}"
            )

        state = self._state_tracker.init_state(pipeline, params)
        return pipeline, state

    def get_next_slots(
        self, pipeline: Pipeline, state: PipelineState
    ) -> list[Slot]:
        """Get Slot objects that are ready to execute.

        Calls state_tracker.get_ready_slots() and resolves IDs to
        Slot objects from the Pipeline.

        Returns:
            List of Slot objects (not just IDs).
        """
        ready_ids = self._state_tracker.get_ready_slots(pipeline, state)
        slot_map = {s.id: s for s in pipeline.slots}
        return [slot_map[sid] for sid in ready_ids if sid in slot_map]

    def begin_slot(
        self,
        slot: Slot,
        pipeline: Pipeline,
        state: PipelineState,
        *,
        agent_id: str | None = None,
        agent_prompt: str | None = None,
    ) -> PipelineState:
        """Start execution of a slot.

        Steps:
        1. Check pre-conditions via gate_checker
        2. If all pass: update status to IN_PROGRESS
        3. If any fail: update status to FAILED with error details

        Returns:
            Updated PipelineState.
        """
        pre_results = self._gate_checker.check_pre_conditions(slot, state)

        if self._gate_checker.all_passed(pre_results):
            # Update pipeline status to RUNNING if not already
            if state.status != PipelineStatus.RUNNING:
                state.status = PipelineStatus.RUNNING

            state = self._state_tracker.update_slot(
                state,
                slot.id,
                SlotStatus.IN_PROGRESS,
                agent_id=agent_id,
                agent_prompt=agent_prompt,
                pre_check_results=pre_results,
            )
        else:
            failed_conditions = [
                r.evidence for r in pre_results if not r.passed
            ]
            error_msg = f"Pre-conditions failed: {'; '.join(failed_conditions)}"
            state = self._state_tracker.update_slot(
                state,
                slot.id,
                SlotStatus.FAILED,
                error=error_msg,
                pre_check_results=pre_results,
            )

        return state

    def complete_slot(
        self, slot_id: str, pipeline: Pipeline, state: PipelineState
    ) -> PipelineState:
        """Mark a slot as completed after agent finishes.

        Steps:
        1. Find the Slot object by ID
        2. Check post-conditions via gate_checker
        3. If all pass: update status to COMPLETED
        4. If any fail: update status to FAILED

        Returns:
            Updated PipelineState.
        """
        slot = self._find_slot(pipeline, slot_id)

        post_results = self._gate_checker.check_post_conditions(slot, state)

        if self._gate_checker.all_passed(post_results):
            state = self._state_tracker.update_slot(
                state,
                slot_id,
                SlotStatus.COMPLETED,
                post_check_results=post_results,
            )
        else:
            failed_conditions = [
                r.evidence for r in post_results if not r.passed
            ]
            error_msg = (
                f"Post-conditions failed: {'; '.join(failed_conditions)}"
            )
            state = self._state_tracker.update_slot(
                state,
                slot_id,
                SlotStatus.FAILED,
                error=error_msg,
                post_check_results=post_results,
            )

        # Check if pipeline is complete
        if self._state_tracker.is_complete(state):
            state.status = PipelineStatus.COMPLETED
            self._state_tracker.save(state)

        return state

    def fail_slot(
        self, slot_id: str, error: str, state: PipelineState
    ) -> PipelineState:
        """Manually mark a slot as failed.

        Returns:
            Updated PipelineState.
        """
        state = self._state_tracker.update_slot(
            state, slot_id, SlotStatus.FAILED, error=error
        )

        # Check if all slots are terminal
        if self._state_tracker.is_complete(state):
            state.status = PipelineStatus.FAILED
            self._state_tracker.save(state)

        return state

    def skip_slot(
        self, slot_id: str, state: PipelineState
    ) -> PipelineState:
        """Skip a slot (CEO decision). Dependents are unblocked.

        Returns:
            Updated PipelineState.
        """
        state = self._state_tracker.update_slot(
            state, slot_id, SlotStatus.SKIPPED
        )

        if self._state_tracker.is_complete(state):
            state.status = PipelineStatus.COMPLETED
            self._state_tracker.save(state)

        return state

    def get_summary(self, state: PipelineState) -> str:
        """Human-readable pipeline status string.

        Format:
            Pipeline: {id} v{version}
            Status: {status}
            Progress: {completed}/{total} slots
            ---
            [COMPLETED] slot-design (designer)
            [IN_PROGRESS] slot-implement (implementer) -- agent: ENG-001
            [BLOCKED] slot-review (reviewer)
        """
        summary = self._state_tracker.get_status_summary(state)
        total = len(state.slots)
        completed_count = len(summary.get("completed", []))

        lines = [
            f"Pipeline: {state.pipeline_id} v{state.pipeline_version}",
            f"Status: {state.status.value}",
            f"Progress: {completed_count}/{total} slots",
            "---",
        ]

        for slot_id, slot_state in state.slots.items():
            status_tag = f"[{slot_state.status.value.upper()}]"
            agent_info = ""
            if slot_state.agent_id:
                agent_info = f" -- agent: {slot_state.agent_id}"
            lines.append(f"{status_tag} {slot_id}{agent_info}")

        return "\n".join(lines)

    def resume(
        self, state_path: str
    ) -> tuple[Pipeline, PipelineState]:
        """Resume a pipeline from a saved state file.

        Steps:
        1. Load state from state_path
        2. Re-load pipeline YAML (path derived from state metadata)
        3. Verify definition_hash matches
        4. Return (pipeline, state)

        Raises:
            PipelineExecutionError: Hash mismatch (pipeline was modified).
        """
        # The pipeline YAML path is not stored in state, so we cannot
        # re-load and verify the pipeline definition from state alone.
        # The caller should use resume_with_pipeline() instead.
        raise PipelineExecutionError(
            "resume() requires pipeline YAML path tracking -- "
            "use resume_with_pipeline() instead"
        )

    def resume_with_pipeline(
        self, state_path: str, yaml_path: str, params: dict[str, Any]
    ) -> tuple[Pipeline, PipelineState]:
        """Resume a pipeline from a saved state file with explicit YAML path.

        Steps:
        1. Load state from state_path
        2. Re-load pipeline YAML from yaml_path
        3. Verify definition_hash matches
        4. Return (pipeline, state)

        Raises:
            PipelineExecutionError: Hash mismatch (pipeline was modified).
        """
        state = self._state_tracker.load(state_path)
        pipeline = self._loader.load_and_resolve(yaml_path, params)

        # Verify definition hash using the same method as state tracker
        computed_hash = PipelineStateTracker._compute_hash(pipeline)

        if computed_hash != state.definition_hash:
            raise PipelineExecutionError(
                f"Pipeline definition hash mismatch: "
                f"expected {state.definition_hash}, "
                f"got {computed_hash}. "
                f"Pipeline YAML was modified since this state was saved."
            )

        return pipeline, state

    # --- Private helpers ---

    @staticmethod
    def _find_slot(pipeline: Pipeline, slot_id: str) -> Slot:
        """Find a Slot object by ID in the pipeline.

        Raises:
            KeyError: Slot not found.
        """
        for slot in pipeline.slots:
            if slot.id == slot_id:
                return slot
        raise KeyError(f"Slot '{slot_id}' not found in pipeline")
