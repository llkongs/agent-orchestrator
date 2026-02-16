"""Concrete PipelineObserver implementations.

ComplianceObserver writes append-only YAML event logs for compliance
auditing.  Observer failures are caught and logged, never propagated.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pipeline.models import (
    GateCheckResult,
    PipelineObserver,
    PipelineState,
    PipelineStatus,
)

logger = logging.getLogger(__name__)


class ComplianceObserver(PipelineObserver):
    """Writes pipeline events to an append-only YAML log file.

    Each event is appended as a YAML document (separated by ``---``).
    The log file is created on first write.  All methods are safe --
    exceptions are caught and logged, never propagated.

    Args:
        log_dir: Directory for event log files.
    """

    def __init__(self, log_dir: str) -> None:
        self._log_dir = Path(log_dir)

    def on_pipeline_started(
        self, pipeline_id: str, state: PipelineState
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "pipeline_started",
            "pipeline_id": pipeline_id,
            "status": state.status.value,
            "slot_count": len(state.slots),
        })

    def on_pipeline_completed(
        self, pipeline_id: str, state: PipelineState
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "pipeline_completed",
            "pipeline_id": pipeline_id,
            "status": state.status.value,
        })

    def on_pipeline_failed(
        self, pipeline_id: str, state: PipelineState, error: str
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "pipeline_failed",
            "pipeline_id": pipeline_id,
            "status": state.status.value,
            "error": error,
        })

    def on_slot_started(
        self, pipeline_id: str, slot_id: str, agent_id: str | None
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "slot_started",
            "pipeline_id": pipeline_id,
            "slot_id": slot_id,
            "agent_id": agent_id or "",
        })

    def on_slot_completed(
        self, pipeline_id: str, slot_id: str
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "slot_completed",
            "pipeline_id": pipeline_id,
            "slot_id": slot_id,
        })

    def on_slot_failed(
        self, pipeline_id: str, slot_id: str, error: str
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "slot_failed",
            "pipeline_id": pipeline_id,
            "slot_id": slot_id,
            "error": error,
        })

    def on_gate_check_completed(
        self, pipeline_id: str, slot_id: str,
        gate_type: str, results: list[GateCheckResult],
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "gate_check_completed",
            "pipeline_id": pipeline_id,
            "slot_id": slot_id,
            "gate_type": gate_type,
            "passed": all(r.passed for r in results),
            "result_count": len(results),
        })

    def on_status_changed(
        self, pipeline_id: str,
        old_status: PipelineStatus, new_status: PipelineStatus,
    ) -> None:
        self._write_event(pipeline_id, {
            "event": "status_changed",
            "pipeline_id": pipeline_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
        })

    # --- Private helpers ---

    def _write_event(
        self, pipeline_id: str, event: dict[str, Any]
    ) -> None:
        """Append a single event to the log file.  Never raises."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            log_path = self._log_dir / f"{pipeline_id}.events.yaml"
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("---\n")
                yaml.safe_dump(event, f, default_flow_style=False)
        except Exception:
            logger.warning(
                "ComplianceObserver failed to write event: %s",
                event.get("event", "unknown"),
                exc_info=True,
            )
