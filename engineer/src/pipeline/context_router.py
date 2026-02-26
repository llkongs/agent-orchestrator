"""Context routing engine for slot-aware context loading.

Scans a project for .abstract.md and .overview.md files, builds a tiered
context list for each slot based on its type, and manages token budget
allocation.  Only depends on models.py + stdlib (pathlib, yaml, os, re).

When *use_openviking* is ``True``, delegates to :class:`OVContextRouter`
first and falls back to the file-scan implementation on failure.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import yaml

from pipeline.models import ContextItem, ContextTier, Pipeline, Slot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Slot type -> relevant directories mapping
# ---------------------------------------------------------------------------

_SLOT_DIRECTORY_MAP: dict[str, list[str]] = {
    "designer": ["specs/", "architect/"],
    "researcher": ["specs/", "agents/", "docs/"],
    "implementer": ["engineer/src/pipeline/", "specs/pipelines/"],
    "reviewer": ["engineer/src/pipeline/", "specs/"],
    "approver": ["architect/", "specs/"],
    "auditor": ["compliance-auditor/", "specs/"],
    "deployer": ["engineer/", "state/"],
}


def _estimate_tokens(content: str) -> int:
    """Rough token estimate: character count / 4."""
    return len(content) // 4


class ContextRouter:
    """Builds tiered context lists for pipeline slots.

    Scans a project directory for .abstract.md (L0) and .overview.md (L1)
    files, and constructs a token-budgeted context list for each slot
    based on its type.
    """

    def __init__(
        self,
        project_root: str,
        constitution_path: str,
        *,
        use_openviking: bool = False,
        ov_binary: str = "ov",
        ov_namespace: str = "viking://agent-orchestrator",
    ) -> None:
        self._project_root = Path(project_root)
        self._constitution_path = Path(constitution_path)
        self._abstract_files: list[str] = []  # Relative paths
        self._overview_files: list[str] = []  # Relative paths
        self._use_openviking = use_openviking
        self._ov_router: "OVContextRouter | None" = None
        if use_openviking:
            from pipeline.ov_context_router import OVContextRouter

            self._ov_router = OVContextRouter(
                project_root,
                ov_binary=ov_binary,
                ov_namespace=ov_namespace,
            )
        self._scan_files()

    def _scan_files(self) -> None:
        """Walk project root and collect .abstract.md / .overview.md files."""
        root = self._project_root
        if not root.is_dir():
            return
        for dirpath, _dirnames, filenames in os.walk(root):
            for fname in filenames:
                full = Path(dirpath) / fname
                rel = str(full.relative_to(root))
                if fname.endswith(".abstract.md"):
                    self._abstract_files.append(rel)
                elif fname.endswith(".overview.md"):
                    self._overview_files.append(rel)

    def build_context(
        self,
        slot: Slot,
        pipeline: Pipeline,
        *,
        max_tokens: int = 8000,
    ) -> list[ContextItem]:
        """Build a tiered context list for the given slot.

        When OpenViking is enabled and available, delegates to
        :class:`OVContextRouter` first.  On failure (OV unavailable or
        returns ``None``), falls back to the file-scan implementation.

        Returns:
            Ordered list of ContextItem within budget.
        """
        if self._ov_router is not None:
            try:
                ov_items = self._ov_router.build_context(
                    slot.slot_type,
                    getattr(slot.task, "description", ""),
                    max_tokens=max_tokens,
                )
                if ov_items is not None:
                    logger.debug(
                        "OV context router returned %d items for slot %s",
                        len(ov_items), slot.id,
                    )
                    return ov_items
            except Exception:
                logger.debug(
                    "OV context router failed, falling back to file scan",
                    exc_info=True,
                )

        return self._build_context_from_files(slot, pipeline, max_tokens=max_tokens)

    def _build_context_from_files(
        self,
        slot: Slot,
        pipeline: Pipeline,
        *,
        max_tokens: int = 8000,
    ) -> list[ContextItem]:
        """Build context by scanning .abstract.md / .overview.md files.

        This is the original file-scan implementation, now used as
        fallback when OpenViking is unavailable.

        Returns:
            Ordered list of ContextItem within budget.
        """
        items: list[ContextItem] = []
        used_tokens = 0

        # 1. Constitution is always L2
        constitution_content = self.get_constitution()
        if constitution_content:
            tokens = _estimate_tokens(constitution_content)
            items.append(ContextItem(
                path=str(self._constitution_path.relative_to(self._project_root))
                if self._constitution_path.is_relative_to(self._project_root)
                else str(self._constitution_path),
                tier=ContextTier.L2,
                relevance=1.0,
                tokens_estimate=tokens,
            ))
            used_tokens += tokens

        # 2. Load all L0 files
        for rel_path in sorted(self._abstract_files):
            content = self._read_file(rel_path)
            if content is None:
                continue
            tokens = _estimate_tokens(content)
            if used_tokens + tokens > max_tokens:
                continue
            items.append(ContextItem(
                path=rel_path,
                tier=ContextTier.L0,
                relevance=0.3,
                tokens_estimate=tokens,
            ))
            used_tokens += tokens

        # 3. Load L1 for slot-relevant directories
        mandatory_dirs = self.get_mandatory_reads(slot.slot_type)
        for rel_path in sorted(self._overview_files):
            if not self._matches_directories(rel_path, mandatory_dirs):
                continue
            content = self._read_file(rel_path)
            if content is None:
                continue
            tokens = _estimate_tokens(content)
            if used_tokens + tokens > max_tokens:
                continue
            items.append(ContextItem(
                path=rel_path,
                tier=ContextTier.L1,
                relevance=0.7,
                tokens_estimate=tokens,
            ))
            used_tokens += tokens

        # 4. Upgrade L0 items in relevant directories to L1 within budget
        upgraded: list[ContextItem] = []
        for item in items:
            if (
                item.tier == ContextTier.L0
                and self._matches_directories(item.path, mandatory_dirs)
            ):
                try:
                    new_item = self.upgrade_tier(item, ContextTier.L1)
                    delta = new_item.tokens_estimate - item.tokens_estimate
                    if used_tokens + delta <= max_tokens:
                        upgraded.append(new_item)
                        used_tokens += delta
                    else:
                        upgraded.append(item)
                except (FileNotFoundError, ValueError):
                    upgraded.append(item)
            else:
                upgraded.append(item)

        return upgraded

    def get_constitution(self) -> str:
        """Read and return constitution.md content.

        Returns:
            File content as string, or empty string if not found.
        """
        try:
            return self._constitution_path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return ""

    def get_mandatory_reads(self, slot_type: str) -> list[str]:
        """Return relevant directory prefixes for the given slot type.

        Args:
            slot_type: The slot type identifier (e.g., "designer").

        Returns:
            List of directory prefix strings.  Empty for unknown types.
        """
        return _SLOT_DIRECTORY_MAP.get(slot_type, [])

    def upgrade_tier(
        self, item: ContextItem, target: ContextTier
    ) -> ContextItem:
        """Upgrade a ContextItem to a higher tier.

        L0 -> L1: swap .abstract.md -> .overview.md path.
        L1 -> L2: swap .overview.md -> source file path (strip suffix).

        Args:
            item: The item to upgrade.
            target: The target tier.

        Returns:
            New ContextItem with upgraded tier and updated token estimate.

        Raises:
            ValueError: Invalid upgrade (e.g., L0 -> L2 directly, or
                        already at target).
            FileNotFoundError: Upgraded file does not exist.
        """
        if item.tier == target:
            raise ValueError(
                f"Item is already at tier {target.value}"
            )

        if item.tier == ContextTier.L0 and target == ContextTier.L1:
            new_path = item.path.replace(".abstract.md", ".overview.md")
        elif item.tier == ContextTier.L1 and target == ContextTier.L2:
            new_path = re.sub(r"\.overview\.md$", "", item.path)
            if new_path == item.path:
                raise ValueError(
                    f"Cannot derive source path from '{item.path}'"
                )
        elif item.tier == ContextTier.L0 and target == ContextTier.L2:
            raise ValueError(
                "Cannot upgrade directly from L0 to L2; upgrade to L1 first"
            )
        else:
            raise ValueError(
                f"Invalid upgrade: {item.tier.value} -> {target.value}"
            )

        full_path = self._project_root / new_path
        if not full_path.is_file():
            raise FileNotFoundError(
                f"Upgraded file not found: {new_path}"
            )

        content = full_path.read_text(encoding="utf-8")
        return ContextItem(
            path=new_path,
            tier=target,
            relevance=item.relevance,
            tokens_estimate=_estimate_tokens(content),
        )

    def generate_slot_context_yaml(self, items: list[ContextItem]) -> str:
        """Generate a YAML string describing the context items.

        Args:
            items: List of ContextItem objects.

        Returns:
            YAML-formatted string.
        """
        if not items:
            return yaml.dump({"context_items": []}, default_flow_style=False)

        data = {
            "context_items": [
                {
                    "path": item.path,
                    "tier": item.tier.value,
                    "relevance": item.relevance,
                    "tokens_estimate": item.tokens_estimate,
                }
                for item in items
            ]
        }
        return yaml.dump(data, default_flow_style=False)

    # --- Private helpers ---

    def _read_file(self, rel_path: str) -> str | None:
        """Read a file relative to project root.  Returns None on error."""
        try:
            return (self._project_root / rel_path).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None

    @staticmethod
    def _matches_directories(path: str, directories: list[str]) -> bool:
        """Check if a path falls under any of the given directory prefixes."""
        for d in directories:
            if path.startswith(d):
                return True
        return False
