"""Pipeline state tracking and persistence.

Manages pipeline runtime state: slot statuses, timestamps, gate results.
Persists state to YAML files with atomic writes.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pipeline.models import (
    GateCheckResult,
    Pipeline,
    PipelineState,
    PipelineStatus,
    SlotState,
    SlotStatus,
)


class PipelineStateTracker:
    """Manages pipeline runtime state with YAML persistence."""

    def __init__(self, state_dir: str) -> None:
        """
        Args:
            state_dir: Directory for state YAML files (e.g., state/active/).
        """
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file: str | None = None

    def init_state(
        self, pipeline: Pipeline, params: dict[str, Any]
    ) -> PipelineState:
        """Create initial state for a pipeline run.

        Sets all slots to PENDING, computes definition_hash, stores
        resolved parameter values, saves state file, and returns state.

        File name: {pipeline.id}-{ISO-timestamp}.state.yaml
        """
        definition_hash = self._compute_hash(pipeline)
        slots: dict[str, SlotState] = {}
        for slot in pipeline.slots:
            slots[slot.id] = SlotState(slot_id=slot.id)

        state = PipelineState(
            pipeline_id=pipeline.id,
            pipeline_version=pipeline.version,
            definition_hash=definition_hash,
            status=PipelineStatus.LOADED,
            parameters=dict(params),
            slots=slots,
        )
        self.save(state)
        return state

    def update_slot(
        self,
        state: PipelineState,
        slot_id: str,
        status: SlotStatus,
        *,
        error: str | None = None,
        agent_id: str | None = None,
        agent_prompt: str | None = None,
        pre_check_results: list[GateCheckResult] | None = None,
        post_check_results: list[GateCheckResult] | None = None,
    ) -> PipelineState:
        """Update a slot's status and persist.

        Timestamp behavior:
        - started_at set when status changes to IN_PROGRESS
        - completed_at set when status changes to COMPLETED/FAILED/SKIPPED

        Args:
            state: Current pipeline state (modified in place AND saved).
            slot_id: Which slot to update.
            status: New status.
            error: Error message (for FAILED status).
            agent_id: Agent assigned to this slot.
            agent_prompt: Path to agent .md file.
            pre_check_results: Results of pre-condition evaluation.
            post_check_results: Results of post-condition evaluation.

        Returns:
            Updated PipelineState.

        Raises:
            KeyError: slot_id not found in state.
        """
        if slot_id not in state.slots:
            raise KeyError(f"Slot '{slot_id}' not found in pipeline state")

        slot_state = state.slots[slot_id]
        now = datetime.now(timezone.utc).isoformat()

        slot_state.status = status

        if status == SlotStatus.IN_PROGRESS and slot_state.started_at is None:
            slot_state.started_at = now

        if status in (SlotStatus.COMPLETED, SlotStatus.FAILED, SlotStatus.SKIPPED):
            slot_state.completed_at = now

        if error is not None:
            slot_state.error = error

        if agent_id is not None:
            slot_state.agent_id = agent_id

        if agent_prompt is not None:
            slot_state.agent_prompt = agent_prompt

        if pre_check_results is not None:
            slot_state.pre_check_results = pre_check_results

        if post_check_results is not None:
            slot_state.post_check_results = post_check_results

        self.save(state)
        return state

    def get_ready_slots(
        self, pipeline: Pipeline, state: PipelineState
    ) -> list[str]:
        """Find slots whose dependencies are all met.

        A slot is ready when:
        1. Its status is PENDING or BLOCKED
        2. All slots in its depends_on are COMPLETED
        3. All data_flow source slots are COMPLETED

        Args:
            pipeline: Pipeline definition (for dependency info).
            state: Current state (for slot statuses).

        Returns:
            List of slot IDs that are ready to execute.
        """
        # Build set of data_flow sources for each slot
        data_flow_sources: dict[str, set[str]] = {}
        for edge in pipeline.data_flow:
            data_flow_sources.setdefault(edge.to_slot, set()).add(edge.from_slot)

        ready: list[str] = []
        for slot in pipeline.slots:
            slot_state = state.slots.get(slot.id)
            if slot_state is None:
                continue
            if slot_state.status not in (SlotStatus.PENDING, SlotStatus.BLOCKED):
                continue

            # Check depends_on
            all_deps_met = True
            for dep_id in slot.depends_on:
                dep_state = state.slots.get(dep_id)
                if dep_state is None or dep_state.status != SlotStatus.COMPLETED:
                    all_deps_met = False
                    break

            if not all_deps_met:
                continue

            # Check data_flow sources
            df_sources = data_flow_sources.get(slot.id, set())
            all_sources_met = True
            for src_id in df_sources:
                src_state = state.slots.get(src_id)
                if src_state is None or src_state.status != SlotStatus.COMPLETED:
                    all_sources_met = False
                    break

            if all_sources_met:
                ready.append(slot.id)

        return ready

    def is_complete(self, state: PipelineState) -> bool:
        """True if all slots are in a terminal state (COMPLETED/SKIPPED/FAILED)."""
        terminal = {SlotStatus.COMPLETED, SlotStatus.SKIPPED, SlotStatus.FAILED}
        return all(
            ss.status in terminal
            for ss in state.slots.values()
        )

    def get_status_summary(self, state: PipelineState) -> dict:
        """Human-readable summary.

        Returns:
            {
                "pipeline_id": str,
                "status": str,
                "progress": "3/7 slots completed",
                "completed": [slot_ids...],
                "in_progress": [slot_ids...],
                "ready": [slot_ids...],
                "blocked": [slot_ids...],
                "pending": [slot_ids...],
                "failed": [slot_ids...],
                "skipped": [slot_ids...],
            }
        """
        groups: dict[str, list[str]] = {
            "completed": [],
            "in_progress": [],
            "ready": [],
            "blocked": [],
            "pending": [],
            "failed": [],
            "skipped": [],
        }
        for slot_id, ss in state.slots.items():
            key = ss.status.value
            if key in groups:
                groups[key].append(slot_id)

        # Statuses not in groups (pre_check, post_check, retrying) go to in_progress
        for slot_id, ss in state.slots.items():
            if ss.status.value not in groups:
                groups["in_progress"].append(slot_id)

        total = len(state.slots)
        completed = len(groups["completed"])

        return {
            "pipeline_id": state.pipeline_id,
            "status": state.status.value,
            "progress": f"{completed}/{total} slots completed",
            **groups,
        }

    def save(self, state: PipelineState) -> str:
        """Persist state to YAML file. Returns file path.

        Writes atomically: write to temp file, then os.rename().
        """
        if self._state_file is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            filename = f"{state.pipeline_id}-{timestamp}.state.yaml"
            self._state_file = str(self._state_dir / filename)

        data = self._state_to_dict(state)
        yaml_content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

        # Atomic write
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._state_dir), suffix=".tmp"
        )
        try:
            os.write(fd, yaml_content.encode("utf-8"))
            os.close(fd)
            os.rename(tmp_path, self._state_file)
        except Exception:
            os.close(fd) if not os.get_inheritable(fd) else None
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        return self._state_file

    def load(self, state_path: str) -> PipelineState:
        """Load state from YAML file.

        Returns:
            PipelineState hydrated from YAML.

        Raises:
            FileNotFoundError: state_path does not exist.
            yaml.YAMLError: YAML is malformed.
        """
        path = Path(state_path)
        if not path.exists():
            raise FileNotFoundError(f"State file not found: {state_path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return self._dict_to_state(raw)

    def archive(self, state: PipelineState) -> str:
        """Move state file from active/ to archive/. Returns new path."""
        if self._state_file is None:
            raise FileNotFoundError("No state file to archive")

        archive_dir = self._state_dir.parent / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        src = Path(self._state_file)
        dst = archive_dir / src.name

        os.rename(str(src), str(dst))
        self._state_file = str(dst)
        return str(dst)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hash(pipeline: Pipeline) -> str:
        """Compute sha256 of a deterministic YAML serialization of the pipeline."""
        # Use a sorted dict representation for determinism
        data = {
            "id": pipeline.id,
            "name": pipeline.name,
            "version": pipeline.version,
            "description": pipeline.description,
            "created_by": pipeline.created_by,
            "created_at": pipeline.created_at,
            "slots": [s.id for s in pipeline.slots],
        }
        content = yaml.safe_dump(data, default_flow_style=False, sort_keys=True)
        return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _state_to_dict(state: PipelineState) -> dict:
        """Serialize PipelineState to a dict suitable for YAML."""
        slots_dict = {}
        for slot_id, ss in state.slots.items():
            slot_data: dict[str, Any] = {
                "slot_id": ss.slot_id,
                "status": ss.status.value,
            }
            if ss.started_at:
                slot_data["started_at"] = ss.started_at
            if ss.completed_at:
                slot_data["completed_at"] = ss.completed_at
            if ss.retry_count > 0:
                slot_data["retry_count"] = ss.retry_count
            if ss.error:
                slot_data["error"] = ss.error
            if ss.agent_id:
                slot_data["agent_id"] = ss.agent_id
            if ss.agent_prompt:
                slot_data["agent_prompt"] = ss.agent_prompt
            slots_dict[slot_id] = slot_data

        return {
            "pipeline_id": state.pipeline_id,
            "pipeline_version": state.pipeline_version,
            "definition_hash": state.definition_hash,
            "status": state.status.value,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
            "parameters": state.parameters,
            "slots": slots_dict,
        }

    @staticmethod
    def _dict_to_state(data: dict) -> PipelineState:
        """Deserialize dict from YAML into PipelineState."""
        slots: dict[str, SlotState] = {}
        for slot_id, ss_data in data.get("slots", {}).items():
            slots[slot_id] = SlotState(
                slot_id=ss_data["slot_id"],
                status=SlotStatus(ss_data.get("status", "pending")),
                started_at=ss_data.get("started_at"),
                completed_at=ss_data.get("completed_at"),
                retry_count=ss_data.get("retry_count", 0),
                error=ss_data.get("error"),
                agent_id=ss_data.get("agent_id"),
                agent_prompt=ss_data.get("agent_prompt"),
            )

        return PipelineState(
            pipeline_id=data["pipeline_id"],
            pipeline_version=data["pipeline_version"],
            definition_hash=data["definition_hash"],
            status=PipelineStatus(data.get("status", "loaded")),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            parameters=data.get("parameters", {}),
            slots=slots,
        )
