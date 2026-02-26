"""Pipeline generator for meta-orchestration.

Takes a ProjectBlueprint and generates:
1. Pipeline YAML compatible with loader.py
2. New slot type YAML files for custom roles
3. Agent scaffold .md files with front-matter

Follows the reuse-first strategy: existing slot types are preferred over
generating new ones. Only roles with is_custom_type=True get new slot types.

Dependencies: models, project_planner, PyYAML only. No cross-package imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pipeline.project_planner import (
    Phase,
    PhaseSlot,
    ProjectBlueprint,
    RoleRequirement,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenerationResult:
    """Output of pipeline generation."""

    pipeline_yaml: str                    # Generated pipeline YAML content
    pipeline_id: str                      # Generated pipeline ID
    slot_type_yamls: dict[str, str]       # slot_type_id -> YAML content
    agent_scaffolds: dict[str, str]       # agent_id -> markdown content
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Built-in slot type capability mapping
# ---------------------------------------------------------------------------

# Maps frozenset of capabilities -> existing slot type ID.
# Used for reuse-first resolution: if a role's capabilities are a subset
# of an existing type's capabilities, reuse the existing type.
_BUILTIN_CAPABILITIES: dict[str, list[str]] = {
    "designer": [
        "system_design", "interface_definition", "technical_documentation",
    ],
    "implementer": [
        "python_development", "test_writing", "delivery_protocol",
    ],
    "reviewer": [
        "independent_testing", "code_review", "delivery_protocol",
        "cross_validation",
    ],
    "auditor": [
        "security_audit", "owasp_review", "infrastructure_review",
    ],
    "approver": [
        "decision_making",
    ],
    "deployer": [
        "deployment", "ssh_operations", "service_management",
    ],
    "researcher": [
        "web_search", "technical_analysis", "structured_report_writing",
    ],
    "compliance-auditor": [
        "process_audit", "artifact_validation", "noncompliance_tracking",
        "trend_analysis", "objective_evaluation", "structured_report_writing",
    ],
}


# ---------------------------------------------------------------------------
# PipelineGenerator
# ---------------------------------------------------------------------------


class PipelineGenerator:
    """Generates pipeline YAML, slot types, and agent scaffolds from a blueprint."""

    def __init__(
        self,
        slot_types_dir: str = "",
        agents_dir: str = "",
    ) -> None:
        """
        Args:
            slot_types_dir: Directory containing existing SlotType YAML files.
            agents_dir: Directory containing existing agent .md files.
        """
        self._slot_types_dir = Path(slot_types_dir) if slot_types_dir else None
        self._agents_dir = Path(agents_dir) if agents_dir else None

    def generate(self, blueprint: ProjectBlueprint) -> GenerationResult:
        """Generate everything from a blueprint.

        Args:
            blueprint: Validated ProjectBlueprint.

        Returns:
            GenerationResult with pipeline YAML, slot types, and agents.
        """
        warnings: list[str] = []

        # Resolve slot types (reuse-first)
        role_type_map: dict[str, str] = {}
        for role in blueprint.roles:
            resolved = self._resolve_slot_type(role)
            role_type_map[role.role_id] = resolved

        # Generate pipeline YAML
        pipeline_yaml = self._generate_pipeline_yaml(blueprint, role_type_map)

        # Generate custom slot type YAMLs
        slot_type_yamls: dict[str, str] = {}
        for role in blueprint.roles:
            if role.is_custom_type:
                st_id = role_type_map[role.role_id]
                slot_type_yamls[st_id] = self._generate_slot_type_yaml(role)

        # Generate agent scaffolds
        agent_scaffolds: dict[str, str] = {}
        for role in blueprint.roles:
            agent_id = f"{role.role_id}-agent"
            agent_scaffolds[agent_id] = self._generate_agent_scaffold(
                role, blueprint
            )

        return GenerationResult(
            pipeline_yaml=pipeline_yaml,
            pipeline_id=blueprint.project_id,
            slot_type_yamls=slot_type_yamls,
            agent_scaffolds=agent_scaffolds,
            warnings=warnings,
        )

    def _resolve_slot_type(self, role: RoleRequirement) -> str:
        """Map role to existing slot type or use custom type.

        Strategy: If the role explicitly specifies a slot_type and
        is_custom_type is False, use the specified type. If is_custom_type
        is True, use the role's slot_type as the custom type ID.
        If no slot_type specified, try to match capabilities to built-in types.
        """
        if role.slot_type and not role.is_custom_type:
            return role.slot_type

        if role.is_custom_type and role.slot_type:
            return role.slot_type

        # Try capability matching against built-in types
        role_caps = set(role.capabilities)
        best_match = ""
        best_overlap = 0

        for type_id, type_caps in _BUILTIN_CAPABILITIES.items():
            overlap = len(role_caps & set(type_caps))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = type_id

        if best_match:
            return best_match

        # Fallback: use role_id as custom type
        return role.role_id

    def _generate_pipeline_yaml(
        self,
        bp: ProjectBlueprint,
        role_type_map: dict[str, str],
    ) -> str:
        """Build pipeline YAML matching loader.py format exactly."""
        now = datetime.now(timezone.utc).isoformat()

        # Build slots from phases
        slots_data: list[dict[str, Any]] = []
        for phase in sorted(bp.phases, key=lambda p: p.order):
            # Compute slot dependencies from phase dependencies
            upstream_slot_ids = self._get_upstream_slot_ids(phase, bp.phases)

            for ps in phase.slots:
                slot_data = self._build_slot_dict(
                    ps, role_type_map, phase, upstream_slot_ids, bp
                )
                slots_data.append(slot_data)

        # Build data flow edges
        data_flow = self._build_data_flow(bp)

        pipeline_data: dict[str, Any] = {
            "pipeline": {
                "id": bp.project_id,
                "name": bp.project_name,
                "version": "1.0.0",
                "description": bp.description,
                "created_by": bp.created_by,
                "created_at": now,
                "parameters": [
                    {
                        "name": "user_request",
                        "type": "string",
                        "description": "The original user request",
                        "required": True,
                    },
                ],
                "slots": slots_data,
                "data_flow": data_flow,
            }
        }

        return yaml.dump(
            pipeline_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def _build_slot_dict(
        self,
        ps: PhaseSlot,
        role_type_map: dict[str, str],
        phase: Phase,
        upstream_slot_ids: list[str],
        bp: ProjectBlueprint,
    ) -> dict[str, Any]:
        """Build a single slot dict for the pipeline YAML."""
        role = self._find_role(bp, ps.role_id)
        slot_type = role_type_map.get(ps.role_id, ps.role_id)

        # Build inputs from declared artifact names
        inputs: list[dict[str, Any]] = []
        for artifact_name in ps.inputs:
            # Find which upstream slot produces this artifact
            from_slot = self._find_artifact_producer(
                artifact_name, phase, bp.phases
            )
            inputs.append({
                "name": artifact_name,
                "from_slot": from_slot or "external",
                "artifact": artifact_name,
                "required": True,
            })

        # Build outputs
        outputs: list[dict[str, Any]] = []
        for artifact_name in ps.outputs:
            outputs.append({
                "name": artifact_name,
                "type": "slot_output",
                "validation": "exists",
            })

        slot_data: dict[str, Any] = {
            "id": ps.slot_id,
            "slot_type": slot_type,
            "name": f"{role.title if role else ps.role_id} — {ps.objective}",
            "inputs": inputs,
            "outputs": outputs,
            "depends_on": upstream_slot_ids,
            "task": {
                "objective": ps.objective,
                "deliverables": list(role.responsibilities) if role else [],
                "constraints": [],
            },
            "execution": {
                "timeout_hours": 4.0,
                "retry_on_fail": True,
                "max_retries": 2,
            },
        }

        if phase.parallel_group:
            slot_data["execution"]["parallel_group"] = phase.parallel_group

        return slot_data

    def _generate_slot_type_yaml(self, role: RoleRequirement) -> str:
        """Generate new slot type YAML matching SlotTypeDefinition schema."""
        # Infer category from capabilities
        category = self._infer_category(role.capabilities)

        # Build input/output schemas
        input_schema: dict[str, Any] = {
            "type": "object",
            "required": ["requirements"],
            "properties": {
                "requirements": {
                    "type": "string",
                    "description": "Requirements or directive for this role",
                },
                "context_artifacts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Paths to context files",
                },
            },
        }

        output_schema: dict[str, Any] = {
            "type": "object",
            "required": ["deliverable"],
            "properties": {
                "deliverable": {
                    "type": "string",
                    "description": f"Primary output from {role.title}",
                },
            },
        }

        slot_type_data = {
            "slot_type": {
                "id": role.slot_type or role.role_id,
                "name": role.title,
                "category": category,
                "description": (
                    f"Custom slot type for {role.title}. "
                    f"Responsibilities: {', '.join(role.responsibilities)}"
                ),
                "input_schema": input_schema,
                "output_schema": output_schema,
                "required_capabilities": list(role.capabilities),
                "constraints": [
                    f"Must fulfill: {r}" for r in role.responsibilities
                ],
            }
        }

        return yaml.dump(
            slot_type_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def _generate_agent_scaffold(
        self,
        role: RoleRequirement,
        bp: ProjectBlueprint,
    ) -> str:
        """Generate agent prompt .md with front-matter."""
        slot_type = role.slot_type or role.role_id
        capabilities_yaml = yaml.dump(
            list(role.capabilities),
            default_flow_style=True,
        ).strip()

        lines = [
            "---",
            f"agent_id: \"{role.role_id}-agent\"",
            "version: \"1.0.0\"",
            f"capabilities: {capabilities_yaml}",
            f"compatible_slot_types: [\"{slot_type}\"]",
            "---",
            "",
            f"# {role.title}",
            "",
            "## Role",
        ]

        for resp in role.responsibilities:
            lines.append(f"- {resp}")

        lines.extend([
            "",
            "## Capabilities",
        ])
        for cap in role.capabilities:
            lines.append(f"- {cap}")

        lines.extend([
            "",
            "## Context",
            f"- **Project**: {bp.project_name}",
            f"- **Domain**: {bp.domain}",
            f"- **Description**: {bp.description}",
            "",
        ])

        return "\n".join(lines)

    def _build_data_flow(
        self, bp: ProjectBlueprint
    ) -> list[dict[str, Any]]:
        """Infer data_flow edges from phase slot inputs/outputs.

        For each slot input, find the upstream slot that produces that
        artifact name in its outputs.
        """
        edges: list[dict[str, Any]] = []

        # Build output registry: artifact_name -> slot_id
        output_registry: dict[str, str] = {}
        for phase in sorted(bp.phases, key=lambda p: p.order):
            for ps in phase.slots:
                for artifact in ps.outputs:
                    output_registry[artifact] = ps.slot_id

        # Build edges
        for phase in sorted(bp.phases, key=lambda p: p.order):
            for ps in phase.slots:
                for artifact in ps.inputs:
                    if artifact in output_registry:
                        from_slot = output_registry[artifact]
                        if from_slot != ps.slot_id:
                            edges.append({
                                "from_slot": from_slot,
                                "to_slot": ps.slot_id,
                                "artifact": artifact,
                                "required": True,
                            })

        return edges

    def write_all(
        self,
        result: GenerationResult,
        output_dir: str,
    ) -> list[str]:
        """Write all generated files to disk.

        Directory structure:
            output_dir/
                pipelines/{pipeline_id}.yaml
                slot-types/{slot_type_id}.yaml
                agents/{agent_id}.md

        Args:
            result: GenerationResult from generate().
            output_dir: Root output directory.

        Returns:
            List of file paths written.
        """
        out = Path(output_dir)
        written: list[str] = []

        # Pipeline YAML
        pipeline_dir = out / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        pipeline_path = pipeline_dir / f"{result.pipeline_id}.yaml"
        pipeline_path.write_text(result.pipeline_yaml, encoding="utf-8")
        written.append(str(pipeline_path))

        # Slot type YAMLs
        if result.slot_type_yamls:
            st_dir = out / "slot-types"
            st_dir.mkdir(parents=True, exist_ok=True)
            for st_id, st_yaml in result.slot_type_yamls.items():
                st_path = st_dir / f"{st_id}.yaml"
                st_path.write_text(st_yaml, encoding="utf-8")
                written.append(str(st_path))

        # Agent scaffolds
        if result.agent_scaffolds:
            agents_dir = out / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)
            for agent_id, scaffold in result.agent_scaffolds.items():
                agent_path = agents_dir / f"{agent_id}.md"
                agent_path.write_text(scaffold, encoding="utf-8")
                written.append(str(agent_path))

        return written

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_role(
        bp: ProjectBlueprint, role_id: str
    ) -> RoleRequirement | None:
        """Find a role by ID in the blueprint."""
        for r in bp.roles:
            if r.role_id == role_id:
                return r
        return None

    @staticmethod
    def _get_upstream_slot_ids(
        phase: Phase, all_phases: list[Phase]
    ) -> list[str]:
        """Get all slot IDs from phases that this phase depends on."""
        dep_phase_ids = set(phase.depends_on)
        upstream_slots: list[str] = []
        for p in all_phases:
            if p.id in dep_phase_ids:
                for ps in p.slots:
                    upstream_slots.append(ps.slot_id)
        return upstream_slots

    @staticmethod
    def _find_artifact_producer(
        artifact_name: str,
        current_phase: Phase,
        all_phases: list[Phase],
    ) -> str | None:
        """Find which upstream slot produces a given artifact."""
        # Search phases with lower order
        for phase in sorted(all_phases, key=lambda p: p.order):
            if phase.order >= current_phase.order:
                continue
            for ps in phase.slots:
                if artifact_name in ps.outputs:
                    return ps.slot_id
        # Also check current phase (for intra-phase dependencies)
        for ps in current_phase.slots:
            if artifact_name in ps.outputs:
                return ps.slot_id
        return None

    @staticmethod
    def _infer_category(capabilities: list[str]) -> str:
        """Infer a category from capabilities list."""
        cap_set = set(capabilities)
        if cap_set & {"system_design", "interface_definition", "architecture"}:
            return "architecture"
        if cap_set & {"python_development", "coding", "implementation"}:
            return "engineering"
        if cap_set & {"code_review", "testing", "qa"}:
            return "quality"
        if cap_set & {"security_audit", "owasp_review"}:
            return "security"
        if cap_set & {"decision_making", "approval"}:
            return "governance"
        if cap_set & {"deployment", "operations"}:
            return "operations"
        if cap_set & {"web_search", "research"}:
            return "research"
        return "custom"
