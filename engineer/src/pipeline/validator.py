"""DAG validation for pipeline definitions.

Validates structural correctness: unique slot IDs, valid dependencies,
DAG acyclicity (Kahn's algorithm), I/O compatibility, and slot type
existence.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pipeline.models import Pipeline, Slot

if TYPE_CHECKING:
    from pipeline.slot_registry import SlotRegistry


@dataclass
class ValidationResult:
    """Result of pipeline validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PipelineCycleError(Exception):
    """Raised when dependency graph has a cycle."""


class PipelineValidator:
    """Validates pipeline structural correctness."""

    def __init__(self, project_root: str) -> None:
        """
        Args:
            project_root: Root directory for file existence checks.
        """
        self._project_root = project_root

    def validate(self, pipeline: Pipeline) -> ValidationResult:
        """Run all validation checks on a pipeline.

        Checks performed (in order):
        1. unique_slot_ids     -- No duplicate slot IDs
        2. valid_dependencies  -- All depends_on reference existing slots
        3. dag_acyclic         -- No dependency cycles
        4. io_compatible       -- Every data_flow input has a matching output
        5. terminal_slot       -- At least one slot has no dependents

        Returns:
            ValidationResult with collected errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Unique slot IDs
        errors.extend(self._check_unique_ids(pipeline.slots))

        # 2. Valid dependencies
        errors.extend(self._check_valid_dependencies(pipeline.slots))

        # 3. DAG acyclicity
        errors.extend(self.check_dag(pipeline.slots))

        # 4. I/O compatibility
        errors.extend(self.check_io_compatibility(pipeline))

        # 5. Terminal slot
        terminal_warnings = self._check_terminal_slot(pipeline)
        warnings.extend(terminal_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def check_dag(self, slots: list[Slot]) -> list[str]:
        """Check for dependency cycles using Kahn's algorithm.

        Args:
            slots: List of Slot objects.

        Returns:
            List of error messages. Empty = no cycles.
        """
        slot_ids = {s.id for s in slots}
        # Build adjacency: for each slot, its dependents
        dependents: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {s.id: 0 for s in slots}

        for slot in slots:
            for dep in slot.depends_on:
                if dep in slot_ids:
                    dependents[dep].append(slot.id)
                    in_degree[slot.id] += 1

        queue = deque(sid for sid, deg in in_degree.items() if deg == 0)
        sorted_count = 0

        while queue:
            node = queue.popleft()
            sorted_count += 1
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if sorted_count != len(slots):
            cycle_nodes = [sid for sid, deg in in_degree.items() if deg > 0]
            return [f"Dependency cycle detected involving slots: {', '.join(cycle_nodes)}"]
        return []

    def topological_sort(self, slots: list[Slot]) -> list[str]:
        """Return slot IDs in valid execution order.

        Uses Kahn's algorithm. Slots with no dependencies come first.
        Among slots at the same level, order is stable (insertion order).

        Args:
            slots: List of Slot objects.

        Returns:
            List of slot IDs in topological order.

        Raises:
            PipelineCycleError: Dependency cycle detected.
        """
        slot_ids = {s.id for s in slots}
        dependents: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {s.id: 0 for s in slots}

        for slot in slots:
            for dep in slot.depends_on:
                if dep in slot_ids:
                    dependents[dep].append(slot.id)
                    in_degree[slot.id] += 1

        queue = deque(sid for sid, deg in in_degree.items() if deg == 0)
        result: list[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(slots):
            cycle_nodes = [sid for sid, deg in in_degree.items() if deg > 0]
            raise PipelineCycleError(
                f"Dependency cycle detected involving slots: {', '.join(cycle_nodes)}"
            )
        return result

    def check_io_compatibility(self, pipeline: Pipeline) -> list[str]:
        """Verify every data_flow edge has a matching producer output.

        For each DataFlowEdge:
        - from_slot must exist
        - to_slot must exist
        - from_slot must have an output with matching artifact name

        Returns:
            List of error messages. Empty = all compatible.
        """
        errors: list[str] = []
        slot_map = {s.id: s for s in pipeline.slots}
        output_map: dict[str, set[str]] = {}
        for slot in pipeline.slots:
            output_map[slot.id] = {o.name for o in slot.outputs}

        for edge in pipeline.data_flow:
            if edge.from_slot not in slot_map:
                errors.append(
                    f"data_flow: from_slot '{edge.from_slot}' does not exist"
                )
                continue
            if edge.to_slot not in slot_map:
                errors.append(
                    f"data_flow: to_slot '{edge.to_slot}' does not exist"
                )
                continue
            if edge.artifact not in output_map.get(edge.from_slot, set()):
                errors.append(
                    f"data_flow: slot '{edge.from_slot}' has no output named "
                    f"'{edge.artifact}' (required by '{edge.to_slot}')"
                )
        return errors

    def check_slot_types(
        self, pipeline: Pipeline, registry: SlotRegistry
    ) -> list[str]:
        """Verify all slot_type references exist in the registry.

        Args:
            pipeline: Pipeline to check.
            registry: SlotRegistry with loaded slot types.

        Returns:
            List of error messages for missing slot types.
        """
        errors: list[str] = []
        for slot in pipeline.slots:
            try:
                registry.get_slot_type(slot.slot_type)
            except Exception:
                errors.append(
                    f"Slot '{slot.id}': slot_type '{slot.slot_type}' not found in registry"
                )
        return errors

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_unique_ids(slots: list[Slot]) -> list[str]:
        """Check for duplicate slot IDs."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for slot in slots:
            if slot.id in seen:
                duplicates.append(f"Duplicate slot ID: '{slot.id}'")
            seen.add(slot.id)
        return duplicates

    @staticmethod
    def _check_valid_dependencies(slots: list[Slot]) -> list[str]:
        """Check all depends_on references point to existing slots."""
        slot_ids = {s.id for s in slots}
        errors: list[str] = []
        for slot in slots:
            for dep in slot.depends_on:
                if dep not in slot_ids:
                    errors.append(
                        f"Slot '{slot.id}': depends_on '{dep}' does not exist"
                    )
        return errors

    @staticmethod
    def _check_terminal_slot(pipeline: Pipeline) -> list[str]:
        """Check that at least one slot has no dependents."""
        warnings: list[str] = []
        all_deps: set[str] = set()
        for slot in pipeline.slots:
            all_deps.update(slot.depends_on)
        # Also check data_flow edges
        for edge in pipeline.data_flow:
            all_deps.add(edge.from_slot)

        slot_ids = {s.id for s in pipeline.slots}
        # A terminal slot is one that no other slot depends on
        terminal_slots = slot_ids - all_deps
        if not terminal_slots and pipeline.slots:
            warnings.append("No terminal slot found (every slot is a dependency of another)")
        return warnings
