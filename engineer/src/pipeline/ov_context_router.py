"""OpenViking-backed context router for slot-aware context loading.

Delegates to the ``ov`` CLI for L0/L1/L2 context retrieval and semantic
search.  Falls back gracefully when OpenViking is unavailable — every
public method returns ``None`` on failure so the caller can use the
standard file-scan ContextRouter.

Only depends on stdlib (subprocess, json, logging) + pipeline.models.
No external Python packages (Constitution §2.2).
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

from pipeline.models import ContextItem, ContextTier

logger = logging.getLogger(__name__)

_OV_TIMEOUT = 30  # seconds per CLI call


class OVContextRouter:
    """Context router backed by the OpenViking CLI.

    All ``ov`` calls are wrapped in try/except and return ``None`` on
    failure.  The caller should fall back to :class:`ContextRouter` when
    this router is unavailable or returns ``None``.
    """

    def __init__(
        self,
        project_root: str,
        *,
        ov_binary: str = "ov",
        ov_namespace: str = "viking://agent-orchestrator",
    ) -> None:
        self._project_root = project_root
        self._ov = ov_binary
        self._namespace = ov_namespace
        self._available: bool | None = None  # lazy check

    @property
    def is_available(self) -> bool:
        """Check if ov CLI is reachable and server is running."""
        if self._available is None:
            self._available = self._run_ov(["health"]) is not None
        return self._available

    def build_context(
        self,
        slot_type: str,
        slot_objective: str = "",
        *,
        max_tokens: int = 8000,
    ) -> list[ContextItem] | None:
        """Build a tiered context list using OpenViking.

        Steps:
            1. ``ov abstract`` for the namespace root → L0 items
            2. ``ov overview`` for slot-relevant subdirectories → L1 items
            3. ``ov find`` with the slot objective for semantic hits → L1/L2
            4. Trim to *max_tokens* budget

        Returns:
            List of :class:`ContextItem`, or ``None`` if OV is
            unavailable (caller should fall back).
        """
        if not self.is_available:
            return None

        items: list[ContextItem] = []
        used_tokens = 0

        # 1. L0 — namespace abstract
        abstract_text = self._run_ov(["abstract", self._namespace])
        if abstract_text:
            tokens = len(abstract_text) // 4
            if used_tokens + tokens <= max_tokens:
                items.append(ContextItem(
                    path=f"{self._namespace}/",
                    tier=ContextTier.L0,
                    relevance=0.3,
                    tokens_estimate=tokens,
                ))
                used_tokens += tokens

        # 2. L1 — overview of relevant sub-resources
        ls_output = self._run_ov(["ls", self._namespace, "-s"])
        if ls_output:
            for line in ls_output.strip().splitlines():
                resource = line.strip()
                if not resource:
                    continue
                uri = (
                    f"{self._namespace}/{resource}"
                    if not resource.startswith("viking://")
                    else resource
                )
                overview_text = self._run_ov(["overview", uri])
                if overview_text:
                    tokens = len(overview_text) // 4
                    if used_tokens + tokens <= max_tokens:
                        items.append(ContextItem(
                            path=uri,
                            tier=ContextTier.L1,
                            relevance=0.6,
                            tokens_estimate=tokens,
                        ))
                        used_tokens += tokens

        # 3. Semantic search — boost relevant items
        if slot_objective:
            search_items = self.semantic_search(
                slot_objective, limit=5
            )
            for si in search_items:
                if used_tokens + si.tokens_estimate <= max_tokens:
                    items.append(si)
                    used_tokens += si.tokens_estimate

        return items

    def semantic_search(
        self, query: str, *, limit: int = 10
    ) -> list[ContextItem]:
        """Use ``ov find`` for semantic retrieval.

        Returns:
            List of :class:`ContextItem` from semantic search, or empty
            list on failure.
        """
        if not self.is_available:
            return []

        output = self._run_ov([
            "find", query,
            "--uri", self._namespace,
            "--limit", str(limit),
            "-o", "json",
        ])
        if not output:
            return []

        items: list[ContextItem] = []
        try:
            data = json.loads(output)
            results = data if isinstance(data, list) else data.get("results", [])
            for entry in results:
                path = entry.get("uri", entry.get("path", "unknown"))
                score = float(entry.get("score", entry.get("relevance", 0.5)))
                content = entry.get("content", "")
                tokens = len(content) // 4 if content else 200
                items.append(ContextItem(
                    path=str(path),
                    tier=ContextTier.L1,
                    relevance=min(score, 1.0),
                    tokens_estimate=tokens,
                ))
        except (json.JSONDecodeError, TypeError, KeyError, ValueError):
            logger.debug("Failed to parse ov find output", exc_info=True)

        return items

    def get_relations(self, uri: str) -> list[str]:
        """List relations of a resource via ``ov relations``.

        Returns:
            List of related URIs, or empty list on failure.
        """
        output = self._run_ov(["relations", uri, "-o", "json"])
        if not output:
            return []
        try:
            data = json.loads(output)
            if isinstance(data, list):
                return [str(r.get("uri", r)) for r in data]
            return [str(r.get("uri", r)) for r in data.get("relations", [])]
        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    # --- Private helpers ---

    def _run_ov(self, args: list[str]) -> str | None:
        """Execute an ``ov`` CLI command.

        Uses explicit argument list (no ``shell=True``) per Constitution
        §6.2.  Returns stdout on success, ``None`` on any failure.
        """
        try:
            result = subprocess.run(
                [self._ov, *args],
                capture_output=True,
                text=True,
                timeout=_OV_TIMEOUT,
            )
            if result.returncode == 0:
                return result.stdout
            logger.debug(
                "ov %s failed (rc=%d): %s",
                args[0] if args else "?",
                result.returncode,
                result.stderr[:200],
            )
            return None
        except FileNotFoundError:
            logger.debug("ov binary not found at %s", self._ov)
            self._available = False
            return None
        except subprocess.TimeoutExpired:
            logger.debug("ov %s timed out after %ds", args[0] if args else "?", _OV_TIMEOUT)
            return None
        except Exception:
            logger.debug("ov call failed", exc_info=True)
            return None
