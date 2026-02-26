"""Project blueprint data model and validation for meta-orchestration.

Defines the intermediate representation between CEO/PM/Architect discussion
output and generated pipelines. A ProjectBlueprint captures project identity,
roles, subsystems, phases, and dependencies -- everything needed to
programmatically generate a pipeline YAML, slot types, and agent scaffolds.

This module has minimal dependencies: models (for reuse of ValidationResult
pattern) and PyYAML for serialization. No cross-package imports.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Frozen dataclasses (Blueprint IR)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleRequirement:
    """A specialist role needed for the project."""

    role_id: str                 # kebab-case, e.g. "game-designer"
    title: str                   # Human name, e.g. "Game Designer"
    capabilities: list[str]      # Required skills
    responsibilities: list[str]  # What they produce
    slot_type: str               # Maps to existing or new SlotTypeDefinition.id
    is_custom_type: bool = False # True = needs new slot type generated


@dataclass(frozen=True)
class Subsystem:
    """A major component of the project."""

    id: str           # kebab-case
    name: str
    description: str
    roles: list[str]  # role_ids involved


@dataclass(frozen=True)
class PhaseSlot:
    """A slot within a phase."""

    slot_id: str       # kebab-case, globally unique across all phases
    role_id: str       # References RoleRequirement.role_id
    objective: str     # What this slot accomplishes
    inputs: list[str]  # Artifact names consumed (from upstream slots)
    outputs: list[str] # Artifact names produced


@dataclass(frozen=True)
class Phase:
    """An execution phase in the project plan."""

    id: str                       # kebab-case, e.g. "phase-1-design"
    name: str
    order: int                    # Sequential order (1, 2, 3...)
    slots: list[PhaseSlot]        # Slots in this phase
    depends_on: list[str] = field(default_factory=list)  # Phase IDs
    parallel_group: str | None = None  # If slots can run in parallel


@dataclass(frozen=True)
class ProjectBlueprint:
    """Complete project decomposition -- input to PipelineGenerator."""

    project_id: str       # kebab-case
    project_name: str
    domain: str           # "game", "web-app", "trading", etc.
    description: str
    roles: list[RoleRequirement]
    subsystems: list[Subsystem]
    phases: list[Phase]
    created_by: str = "meta-orchestration"
    created_at: str = ""  # ISO 8601, filled at creation time


# ---------------------------------------------------------------------------
# Validation result (mirrors validator.py pattern)
# ---------------------------------------------------------------------------


@dataclass
class BlueprintValidationResult:
    """Result of blueprint validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BlueprintLoadError(Exception):
    """Raised when blueprint YAML is malformed or missing required fields."""


class BlueprintCycleError(Exception):
    """Raised when phase dependency graph has a cycle."""


# ---------------------------------------------------------------------------
# ProjectPlanner
# ---------------------------------------------------------------------------

_BLUEPRINT_REQUIRED_FIELDS = {
    "project_id", "project_name", "domain", "description",
    "roles", "phases",
}


class ProjectPlanner:
    """Parses, validates, and serializes ProjectBlueprint objects."""

    def parse_blueprint(self, yaml_path: str) -> ProjectBlueprint:
        """Load and validate a blueprint YAML file.

        Args:
            yaml_path: Path to the blueprint YAML.

        Returns:
            ProjectBlueprint object.

        Raises:
            BlueprintLoadError: File not found, malformed, or missing fields.
        """
        path = Path(yaml_path)
        if not path.exists():
            raise BlueprintLoadError(f"Blueprint file not found: {yaml_path}")

        try:
            raw_text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise BlueprintLoadError(
                f"Malformed YAML in {yaml_path}: {exc}"
            ) from exc

        if data is None:
            raise BlueprintLoadError(f"Empty YAML file: {yaml_path}")

        if not isinstance(data, dict):
            raise BlueprintLoadError(
                f"Expected YAML mapping, got {type(data).__name__}"
            )

        # Handle optional wrapper key
        if "blueprint" in data and isinstance(data["blueprint"], dict):
            data = data["blueprint"]

        return self._hydrate_blueprint(data)

    def parse_blueprint_from_string(self, yaml_text: str) -> ProjectBlueprint:
        """Parse blueprint from a YAML string.

        Args:
            yaml_text: YAML content as string.

        Returns:
            ProjectBlueprint object.
        """
        try:
            data = yaml.safe_load(yaml_text)
        except yaml.YAMLError as exc:
            raise BlueprintLoadError(f"Malformed YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise BlueprintLoadError(
                f"Expected YAML mapping, got {type(data).__name__}"
            )

        if "blueprint" in data and isinstance(data["blueprint"], dict):
            data = data["blueprint"]

        return self._hydrate_blueprint(data)

    def validate_blueprint(
        self, bp: ProjectBlueprint
    ) -> BlueprintValidationResult:
        """Validate blueprint structural correctness.

        Checks:
        1. Unique IDs across roles, subsystems, phases, slots
        2. All role_id references in phases exist in roles list
        3. All depends_on phase IDs exist
        4. Phase dependency graph is acyclic (Kahn's algorithm)
        5. Every role is used in at least one phase slot

        Returns:
            BlueprintValidationResult with errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Unique IDs
        errors.extend(self._check_unique_ids(bp))

        # 2. Valid role references
        role_ids = {r.role_id for r in bp.roles}
        for phase in bp.phases:
            for ps in phase.slots:
                if ps.role_id not in role_ids:
                    errors.append(
                        f"Phase '{phase.id}', slot '{ps.slot_id}': "
                        f"role_id '{ps.role_id}' not found in roles"
                    )

        # 3. Valid phase dependencies
        phase_ids = {p.id for p in bp.phases}
        for phase in bp.phases:
            for dep in phase.depends_on:
                if dep not in phase_ids:
                    errors.append(
                        f"Phase '{phase.id}': depends_on '{dep}' "
                        f"does not exist"
                    )

        # 4. Acyclic phase graph
        errors.extend(self._check_phase_dag(bp.phases))

        # 5. Every role used
        used_roles: set[str] = set()
        for phase in bp.phases:
            for ps in phase.slots:
                used_roles.add(ps.role_id)
        unused = role_ids - used_roles
        for r in sorted(unused):
            warnings.append(f"Role '{r}' is defined but never used in any phase")

        # 6. Subsystem role references
        for sub in bp.subsystems:
            for rid in sub.roles:
                if rid not in role_ids:
                    errors.append(
                        f"Subsystem '{sub.id}': role '{rid}' not found"
                    )

        return BlueprintValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def serialize_blueprint(self, bp: ProjectBlueprint) -> str:
        """Serialize blueprint to YAML string.

        Args:
            bp: ProjectBlueprint to serialize.

        Returns:
            YAML string representation.
        """
        data = self._dehydrate_blueprint(bp)
        return yaml.dump(
            {"blueprint": data},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def generate_inception_context(
        self, bp: ProjectBlueprint
    ) -> dict[str, Any]:
        """Generate context dict for the pipeline-generator slot.

        This is the structured context passed from the architect-decomposition
        slot to the pipeline-generation slot in the inception pipeline.

        Args:
            bp: Validated ProjectBlueprint.

        Returns:
            Dict with blueprint summary and generation hints.
        """
        custom_roles = [r for r in bp.roles if r.is_custom_type]
        reusable_roles = [r for r in bp.roles if not r.is_custom_type]

        return {
            "project_id": bp.project_id,
            "project_name": bp.project_name,
            "domain": bp.domain,
            "total_roles": len(bp.roles),
            "custom_slot_types_needed": len(custom_roles),
            "reusable_slot_types": len(reusable_roles),
            "total_phases": len(bp.phases),
            "total_slots": sum(len(p.slots) for p in bp.phases),
            "subsystems": [s.id for s in bp.subsystems],
            "custom_roles": [
                {"role_id": r.role_id, "capabilities": r.capabilities}
                for r in custom_roles
            ],
        }

    # ------------------------------------------------------------------
    # Private: Hydration (YAML dict -> dataclasses)
    # ------------------------------------------------------------------

    def _hydrate_blueprint(self, data: dict) -> ProjectBlueprint:
        """Convert raw dict to ProjectBlueprint."""
        missing = _BLUEPRINT_REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise BlueprintLoadError(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )

        roles = [self._hydrate_role(r) for r in data.get("roles", [])]
        subsystems = [
            self._hydrate_subsystem(s) for s in data.get("subsystems", [])
        ]
        phases = [self._hydrate_phase(p) for p in data.get("phases", [])]

        created_at = str(
            data.get("created_at", "")
        ) or datetime.now(timezone.utc).isoformat()

        return ProjectBlueprint(
            project_id=str(data["project_id"]),
            project_name=str(data["project_name"]),
            domain=str(data["domain"]),
            description=str(data["description"]),
            roles=roles,
            subsystems=subsystems,
            phases=phases,
            created_by=str(data.get("created_by", "meta-orchestration")),
            created_at=created_at,
        )

    @staticmethod
    def _hydrate_role(data: dict) -> RoleRequirement:
        return RoleRequirement(
            role_id=str(data["role_id"]),
            title=str(data.get("title", data["role_id"])),
            capabilities=list(data.get("capabilities", [])),
            responsibilities=list(data.get("responsibilities", [])),
            slot_type=str(data.get("slot_type", "")),
            is_custom_type=bool(data.get("is_custom_type", False)),
        )

    @staticmethod
    def _hydrate_subsystem(data: dict) -> Subsystem:
        return Subsystem(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            description=str(data.get("description", "")),
            roles=list(data.get("roles", [])),
        )

    def _hydrate_phase(self, data: dict) -> Phase:
        slots = [
            self._hydrate_phase_slot(s) for s in data.get("slots", [])
        ]
        return Phase(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            order=int(data.get("order", 0)),
            slots=slots,
            depends_on=list(data.get("depends_on", [])),
            parallel_group=data.get("parallel_group"),
        )

    @staticmethod
    def _hydrate_phase_slot(data: dict) -> PhaseSlot:
        return PhaseSlot(
            slot_id=str(data["slot_id"]),
            role_id=str(data["role_id"]),
            objective=str(data.get("objective", "")),
            inputs=list(data.get("inputs", [])),
            outputs=list(data.get("outputs", [])),
        )

    # ------------------------------------------------------------------
    # Private: Dehydration (dataclasses -> YAML dict)
    # ------------------------------------------------------------------

    @staticmethod
    def _dehydrate_blueprint(bp: ProjectBlueprint) -> dict:
        """Convert ProjectBlueprint to serializable dict."""
        return {
            "project_id": bp.project_id,
            "project_name": bp.project_name,
            "domain": bp.domain,
            "description": bp.description,
            "created_by": bp.created_by,
            "created_at": bp.created_at,
            "roles": [
                {
                    "role_id": r.role_id,
                    "title": r.title,
                    "capabilities": list(r.capabilities),
                    "responsibilities": list(r.responsibilities),
                    "slot_type": r.slot_type,
                    "is_custom_type": r.is_custom_type,
                }
                for r in bp.roles
            ],
            "subsystems": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "roles": list(s.roles),
                }
                for s in bp.subsystems
            ],
            "phases": [
                {
                    "id": p.id,
                    "name": p.name,
                    "order": p.order,
                    "depends_on": list(p.depends_on),
                    "parallel_group": p.parallel_group,
                    "slots": [
                        {
                            "slot_id": ps.slot_id,
                            "role_id": ps.role_id,
                            "objective": ps.objective,
                            "inputs": list(ps.inputs),
                            "outputs": list(ps.outputs),
                        }
                        for ps in p.slots
                    ],
                }
                for p in bp.phases
            ],
        }

    # ------------------------------------------------------------------
    # Private: Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_unique_ids(bp: ProjectBlueprint) -> list[str]:
        """Check for duplicate IDs across roles, subsystems, phases, slots."""
        errors: list[str] = []

        # Role IDs
        seen_roles: set[str] = set()
        for r in bp.roles:
            if r.role_id in seen_roles:
                errors.append(f"Duplicate role ID: '{r.role_id}'")
            seen_roles.add(r.role_id)

        # Subsystem IDs
        seen_subs: set[str] = set()
        for s in bp.subsystems:
            if s.id in seen_subs:
                errors.append(f"Duplicate subsystem ID: '{s.id}'")
            seen_subs.add(s.id)

        # Phase IDs
        seen_phases: set[str] = set()
        for p in bp.phases:
            if p.id in seen_phases:
                errors.append(f"Duplicate phase ID: '{p.id}'")
            seen_phases.add(p.id)

        # Slot IDs (globally unique across all phases)
        seen_slots: set[str] = set()
        for p in bp.phases:
            for ps in p.slots:
                if ps.slot_id in seen_slots:
                    errors.append(f"Duplicate slot ID: '{ps.slot_id}'")
                seen_slots.add(ps.slot_id)

        return errors

    @staticmethod
    def _check_phase_dag(phases: list[Phase]) -> list[str]:
        """Check for dependency cycles in phases using Kahn's algorithm."""
        phase_ids = {p.id for p in phases}
        dependents: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {p.id: 0 for p in phases}

        for phase in phases:
            for dep in phase.depends_on:
                if dep in phase_ids:
                    dependents[dep].append(phase.id)
                    in_degree[phase.id] += 1

        queue = deque(pid for pid, deg in in_degree.items() if deg == 0)
        sorted_count = 0

        while queue:
            node = queue.popleft()
            sorted_count += 1
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if sorted_count != len(phases):
            cycle_nodes = [pid for pid, deg in in_degree.items() if deg > 0]
            return [
                f"Phase dependency cycle detected involving: "
                f"{', '.join(cycle_nodes)}"
            ]
        return []
