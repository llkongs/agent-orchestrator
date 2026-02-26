"""Automated pipeline execution engine.

Sits on top of PipelineRunner and automates the full execution loop:
find agent -> generate contract -> spawn agent -> validate output -> complete slot.
Abstract AgentExecutor interface allows pluggable agent spawning mechanisms.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from pipeline.models import (
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotAssignment,
    SlotStatus,
)
from pipeline.runner import PipelineRunner
from pipeline.slot_contract import SlotContractManager, SlotInput
from pipeline.slot_registry import SlotRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentResult:
    """Result from a single agent execution."""

    slot_id: str
    agent_id: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass(frozen=True)
class AutoExecutorConfig:
    """Configuration for the auto-execution loop."""

    max_parallel: int = 4
    timeout_default_hours: float = 4.0
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Abstract executor interface
# ---------------------------------------------------------------------------


class AgentExecutor(ABC):
    """Abstract interface for executing an agent to fill a slot."""

    @abstractmethod
    def execute(
        self,
        slot_input: SlotInput,
        agent_prompt: str,
        agent_id: str,
        *,
        timeout_seconds: float | None = None,
        project_root: str = "",
    ) -> AgentResult:
        """Execute an agent and return the result.

        Args:
            slot_input: The generated slot input contract.
            agent_prompt: Path to the agent prompt file.
            agent_id: ID of the agent being executed.
            timeout_seconds: Maximum execution time.
            project_root: Working directory for the agent.

        Returns:
            AgentResult with execution outcome.
        """


# ---------------------------------------------------------------------------
# Concrete executors
# ---------------------------------------------------------------------------


class CallbackExecutor(AgentExecutor):
    """Agent executor that delegates to a callback function.

    Useful for testing -- the callback receives (slot_input, agent_id)
    and returns True for success, False for failure.
    """

    def __init__(
        self,
        callback: Callable[[SlotInput, str], bool],
        *,
        stdout_fn: Callable[[SlotInput, str], str] | None = None,
        stderr_fn: Callable[[SlotInput, str], str] | None = None,
    ) -> None:
        self._callback = callback
        self._stdout_fn = stdout_fn
        self._stderr_fn = stderr_fn

    def execute(
        self,
        slot_input: SlotInput,
        agent_prompt: str,
        agent_id: str,
        *,
        timeout_seconds: float | None = None,
        project_root: str = "",
    ) -> AgentResult:
        start = time.monotonic()
        try:
            success = self._callback(slot_input, agent_id)
            duration = time.monotonic() - start
            stdout = self._stdout_fn(slot_input, agent_id) if self._stdout_fn else ""
            stderr = self._stderr_fn(slot_input, agent_id) if self._stderr_fn else ""
            return AgentResult(
                slot_id=slot_input.slot_id,
                agent_id=agent_id,
                success=success,
                exit_code=0 if success else 1,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            return AgentResult(
                slot_id=slot_input.slot_id,
                agent_id=agent_id,
                success=False,
                exit_code=1,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
            )


class SubprocessExecutor(AgentExecutor):
    """Agent executor that spawns a subprocess.

    The command_template is formatted with:
        {agent_prompt}  -- path to agent prompt file
        {slot_input}    -- path to slot-input.yaml
        {project_root}  -- project root directory

    Constitution §6.1: never uses shell=True.
    """

    def __init__(self, command_template: str, contracts_dir: str) -> None:
        self._command_template = command_template
        self._contracts_dir = contracts_dir

    def execute(
        self,
        slot_input: SlotInput,
        agent_prompt: str,
        agent_id: str,
        *,
        timeout_seconds: float | None = None,
        project_root: str = "",
    ) -> AgentResult:
        start = time.monotonic()

        # Write slot-input contract to disk
        contract_mgr = SlotContractManager(project_root or ".", self._contracts_dir)
        input_path = contract_mgr.write_slot_input(slot_input)

        # Format command
        cmd_str = self._command_template.format(
            agent_prompt=agent_prompt,
            slot_input=input_path,
            project_root=project_root,
        )
        cmd_parts = cmd_str.split()

        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=project_root or None,
            )
            duration = time.monotonic() - start
            return AgentResult(
                slot_id=slot_input.slot_id,
                agent_id=agent_id,
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            return AgentResult(
                slot_id=slot_input.slot_id,
                agent_id=agent_id,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout_seconds}s",
                duration_seconds=duration,
            )
        except OSError as exc:
            duration = time.monotonic() - start
            return AgentResult(
                slot_id=slot_input.slot_id,
                agent_id=agent_id,
                success=False,
                exit_code=-2,
                stdout="",
                stderr=f"Command error: {exc}",
                duration_seconds=duration,
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass
class _SlotTask:
    """Internal bundle for a slot ready to execute."""

    slot: Slot
    agent_id: str
    agent_prompt: str
    slot_input: SlotInput


# ---------------------------------------------------------------------------
# AutoExecutor
# ---------------------------------------------------------------------------


class AutoExecutor:
    """Automated pipeline execution engine.

    Sits on top of PipelineRunner and automates the full loop:
    find agent -> generate contract -> spawn agent -> validate output -> complete/fail.

    Usage:
        executor = AutoExecutor(runner, agent_executor, contract_mgr, registry)
        final_state = executor.run(pipeline, state)
    """

    def __init__(
        self,
        runner: PipelineRunner,
        executor: AgentExecutor,
        contract_manager: SlotContractManager,
        registry: SlotRegistry,
        *,
        config: AutoExecutorConfig | None = None,
        assignments: list[SlotAssignment] | None = None,
        project_root: str = "",
    ) -> None:
        self._runner = runner
        self._executor = executor
        self._contract_manager = contract_manager
        self._registry = registry
        self._config = config or AutoExecutorConfig()
        self._project_root = project_root
        self._state_lock = threading.RLock()

        # Index assignments by slot_id for O(1) lookup
        self._assignments: dict[str, SlotAssignment] = {}
        if assignments:
            for a in assignments:
                self._assignments[a.slot_id] = a

    # --- Public API ---

    def run(
        self, pipeline: Pipeline, state: PipelineState
    ) -> PipelineState:
        """Execute the full pipeline until no more slots are ready.

        Processes slots in dependency order. Slots in the same
        parallel_group are executed concurrently.

        Args:
            pipeline: The pipeline definition.
            state: Current pipeline state.

        Returns:
            Final PipelineState after all executable slots complete.
        """
        while True:
            ready_slots = self._runner.get_next_slots(pipeline, state)
            if not ready_slots:
                break

            groups = self._group_by_parallel(ready_slots, pipeline)
            for group_slots in groups.values():
                if self._config.dry_run:
                    state = self._dry_run_group(group_slots, pipeline, state)
                else:
                    state = self._execute_group(group_slots, pipeline, state)

        return state

    def run_single_slot(
        self,
        slot: Slot,
        pipeline: Pipeline,
        state: PipelineState,
    ) -> tuple[PipelineState, AgentResult | None]:
        """Execute a single slot and return both state and result.

        Useful for fine-grained control over individual slot execution.

        Args:
            slot: The slot to execute.
            pipeline: The pipeline definition.
            state: Current pipeline state.

        Returns:
            Tuple of (updated state, AgentResult or None if begin failed).
        """
        agent_id, agent_prompt = self._resolve_agent(slot)

        with self._state_lock:
            state = self._runner.begin_slot(
                slot, pipeline, state,
                agent_id=agent_id,
                agent_prompt=agent_prompt,
            )

        # Check if begin_slot failed (pre-conditions)
        slot_state = state.slots.get(slot.id)
        if slot_state and slot_state.status == SlotStatus.FAILED:
            return state, None

        # Generate contract and execute
        slot_input = self._contract_manager.generate_slot_input(
            slot, pipeline, state
        )

        timeout = (
            slot.execution.timeout_hours * 3600
            if slot.execution.timeout_hours
            else self._config.timeout_default_hours * 3600
        )

        result = self._executor.execute(
            slot_input,
            agent_prompt or "",
            agent_id or "",
            timeout_seconds=timeout,
            project_root=self._project_root,
        )

        with self._state_lock:
            state = self._finalize_slot(slot, pipeline, state, result)

        return state, result

    # --- Private: execution ---

    def _execute_group(
        self,
        slots: list[Slot],
        pipeline: Pipeline,
        state: PipelineState,
    ) -> PipelineState:
        """Execute a group of slots with three-phase approach.

        Phase 1 (sequential): begin slots, generate contracts
        Phase 2 (concurrent): execute agents
        Phase 3 (sequential): finalize slots
        """
        # Phase 1: Sequential -- state mutations
        tasks: list[_SlotTask] = []
        for slot in slots:
            agent_id, agent_prompt = self._resolve_agent(slot)

            with self._state_lock:
                state = self._runner.begin_slot(
                    slot, pipeline, state,
                    agent_id=agent_id,
                    agent_prompt=agent_prompt,
                )

            # Check if begin_slot failed
            slot_state = state.slots.get(slot.id)
            if slot_state and slot_state.status == SlotStatus.FAILED:
                logger.warning(
                    "Slot %s failed pre-conditions, skipping execution",
                    slot.id,
                )
                continue

            slot_input = self._contract_manager.generate_slot_input(
                slot, pipeline, state
            )
            tasks.append(_SlotTask(
                slot=slot,
                agent_id=agent_id or "",
                agent_prompt=agent_prompt or "",
                slot_input=slot_input,
            ))

        if not tasks:
            return state

        # Phase 2: Concurrent -- pure I/O
        results = self._execute_tasks(tasks)

        # Phase 3: Sequential -- state mutations
        for task, result in zip(tasks, results):
            with self._state_lock:
                state = self._finalize_slot(
                    task.slot, pipeline, state, result
                )

                # Retry if failed and retries allowed
                slot_state = state.slots.get(task.slot.id)
                if (
                    slot_state
                    and slot_state.status == SlotStatus.FAILED
                    and task.slot.execution.retry_on_fail
                    and slot_state.retry_count < task.slot.execution.max_retries
                ):
                    state = self._retry_slot(
                        task.slot, pipeline, state,
                        task.agent_id, task.agent_prompt,
                    )

        return state

    def _execute_tasks(self, tasks: list[_SlotTask]) -> list[AgentResult]:
        """Execute tasks, using thread pool for multiple tasks."""
        if len(tasks) == 1:
            # Single task -- execute directly, no thread pool overhead
            return [self._execute_single_task(tasks[0])]

        max_workers = min(len(tasks), self._config.max_parallel)
        results: list[AgentResult] = []

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(self._execute_single_task, task)
                for task in tasks
            ]
            results = [f.result() for f in futures]

        return results

    def _execute_single_task(self, task: _SlotTask) -> AgentResult:
        """Execute a single task (called from thread pool or directly)."""
        timeout = (
            task.slot.execution.timeout_hours * 3600
            if task.slot.execution.timeout_hours
            else self._config.timeout_default_hours * 3600
        )

        return self._executor.execute(
            task.slot_input,
            task.agent_prompt,
            task.agent_id,
            timeout_seconds=timeout,
            project_root=self._project_root,
        )

    # --- Private: finalization ---

    def _finalize_slot(
        self,
        slot: Slot,
        pipeline: Pipeline,
        state: PipelineState,
        result: AgentResult,
    ) -> PipelineState:
        """Validate output and complete or fail a slot.

        Args:
            slot: The slot that was executed.
            pipeline: Pipeline definition.
            state: Current pipeline state.
            result: The agent execution result.

        Returns:
            Updated PipelineState.
        """
        if not result.success:
            error = f"Agent {result.agent_id} failed (exit={result.exit_code})"
            if result.stderr:
                error += f": {result.stderr[:500]}"
            return self._runner.fail_slot(slot.id, error, state)

        # Validate outputs
        validation = self._contract_manager.validate_slot_output(slot)
        if not validation.valid:
            parts = []
            if validation.missing_outputs:
                parts.append(f"missing: {validation.missing_outputs}")
            if validation.invalid_outputs:
                parts.append(f"invalid: {validation.invalid_outputs}")
            error = f"Output validation failed: {'; '.join(parts)}"
            return self._runner.fail_slot(slot.id, error, state)

        return self._runner.complete_slot(slot.id, pipeline, state)

    # --- Private: retry ---

    def _retry_slot(
        self,
        slot: Slot,
        pipeline: Pipeline,
        state: PipelineState,
        agent_id: str,
        agent_prompt: str,
    ) -> PipelineState:
        """Retry a failed slot.

        Uses runner.retry_slot() for FAILED -> RETRYING -> IN_PROGRESS,
        then re-generates contract and re-executes the agent.

        Note: fail_slot() may have transitioned the pipeline to FAILED
        when all slots became terminal. We transition back to RUNNING
        so that complete_slot() can later mark it COMPLETED.
        """
        # Pipeline may have been marked FAILED when all slots became terminal.
        # FAILED -> RUNNING is a valid transition (allow retry).
        if state.status == PipelineStatus.FAILED:
            state.status = PipelineStatus.RUNNING
            state.completed_at = None

        try:
            state = self._runner.retry_slot(
                slot.id, pipeline, state,
                agent_id=agent_id or None,
                agent_prompt=agent_prompt or None,
            )
        except Exception:
            logger.warning(
                "Retry failed for slot %s", slot.id, exc_info=True
            )
            return state

        # Re-generate contract and re-execute
        slot_input = self._contract_manager.generate_slot_input(
            slot, pipeline, state
        )

        timeout = (
            slot.execution.timeout_hours * 3600
            if slot.execution.timeout_hours
            else self._config.timeout_default_hours * 3600
        )

        result = self._executor.execute(
            slot_input,
            agent_prompt,
            agent_id,
            timeout_seconds=timeout,
            project_root=self._project_root,
        )

        state = self._finalize_slot(slot, pipeline, state, result)

        # If the retry itself failed, check if another retry is possible
        slot_state = state.slots.get(slot.id)
        if (
            slot_state
            and slot_state.status == SlotStatus.FAILED
            and slot.execution.retry_on_fail
            and slot_state.retry_count < slot.execution.max_retries
        ):
            return self._retry_slot(
                slot, pipeline, state, agent_id, agent_prompt
            )

        return state

    # --- Private: agent resolution ---

    def _resolve_agent(self, slot: Slot) -> tuple[str | None, str | None]:
        """Resolve the agent for a slot.

        Priority:
        1. Explicit assignment from self._assignments
        2. Auto-match from registry
        3. Graceful fallback (None, None)

        Returns:
            Tuple of (agent_id, agent_prompt) or (None, None).
        """
        # 1. Explicit assignment
        assignment = self._assignments.get(slot.id)
        if assignment:
            return assignment.agent_id, assignment.agent_prompt

        # 2. Auto-match from registry
        try:
            matches = self._registry.find_compatible_agents(slot.slot_type)
            for match in matches:
                if match.is_compatible:
                    return match.agent_id, match.prompt_path
        except Exception:
            logger.warning(
                "Agent auto-match failed for slot %s (type=%s)",
                slot.id, slot.slot_type,
                exc_info=True,
            )

        # 3. Graceful fallback
        return None, None

    # --- Private: grouping ---

    @staticmethod
    def _group_by_parallel(
        slots: list[Slot], pipeline: Pipeline
    ) -> dict[str, list[Slot]]:
        """Group slots by parallel_group for concurrent execution.

        Slots with the same parallel_group are grouped together.
        Slots with no parallel_group get their own singleton group.

        Returns:
            Dict mapping group key to list of slots.
        """
        groups: dict[str, list[Slot]] = {}
        singleton_counter = 0

        for slot in slots:
            group_key = slot.execution.parallel_group
            if group_key is None:
                # Singleton group
                groups[f"_singleton_{singleton_counter}"] = [slot]
                singleton_counter += 1
            else:
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(slot)

        return groups

    # --- Private: dry run ---

    def _dry_run_group(
        self,
        slots: list[Slot],
        pipeline: Pipeline,
        state: PipelineState,
    ) -> PipelineState:
        """Dry run: generate contracts, write to disk, skip slots.

        No agents are executed. Contracts are written for inspection.
        """
        # Ensure pipeline is in RUNNING state before skipping slots.
        # skip_slot may trigger is_complete -> COMPLETED transition,
        # which requires the pipeline to be in RUNNING state.
        if state.status in (
            PipelineStatus.LOADED,
            PipelineStatus.VALIDATED,
        ):
            state.status = PipelineStatus.RUNNING

        for slot in slots:
            agent_id, agent_prompt = self._resolve_agent(slot)

            # Generate and write contract
            slot_input = self._contract_manager.generate_slot_input(
                slot, pipeline, state
            )
            contract_path = self._contract_manager.write_slot_input(slot_input)
            logger.info(
                "Dry run: slot=%s agent=%s contract=%s",
                slot.id, agent_id, contract_path,
            )

            # Skip the slot
            with self._state_lock:
                state = self._runner.skip_slot(slot.id, state)

        return state
