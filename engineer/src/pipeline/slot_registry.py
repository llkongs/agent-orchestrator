"""SlotType registry and agent capability matching.

Loads SlotType definitions from YAML files, parses agent .md front-matter
for capability metadata, and matches agents to slot types.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeline.models import (
    AgentCapabilities,
    CapabilityMatch,
    Pipeline,
    SlotTypeDefinition,
)


class SlotTypeNotFoundError(Exception):
    """Raised when a requested slot type does not exist in the registry."""


@dataclass
class SlotManifest:
    """List of slots and their required capabilities, for HR to fill."""

    pipeline_id: str
    slots: list[dict[str, Any]]


class SlotRegistry:
    """Loads SlotType definitions and matches agents to slots."""

    def __init__(self, slot_types_dir: str, agents_dir: str) -> None:
        """
        Args:
            slot_types_dir: Directory containing SlotType YAML files.
            agents_dir: Directory containing agent .md files.
        """
        self._slot_types_dir = Path(slot_types_dir)
        self._agents_dir = Path(agents_dir)
        self._slot_types: dict[str, SlotTypeDefinition] = {}
        self._agents: dict[str, AgentCapabilities] = {}
        self._loaded = False

    def load_slot_types(self) -> dict[str, SlotTypeDefinition]:
        """Load all .yaml files from slot_types_dir.

        Returns:
            Dict mapping slot type ID -> SlotTypeDefinition.

        Raises:
            yaml.YAMLError: A YAML file is malformed.
            KeyError: A YAML file is missing required fields.
        """
        self._slot_types = {}
        if not self._slot_types_dir.exists():
            return self._slot_types

        for yaml_file in sorted(self._slot_types_dir.glob("*.yaml")):
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if data is None:
                continue
            st_data = data.get("slot_type", data)
            std = SlotTypeDefinition(
                id=str(st_data["id"]),
                name=str(st_data["name"]),
                category=str(st_data["category"]),
                description=str(st_data.get("description", "")),
                input_schema=st_data.get("input_schema", {}),
                output_schema=st_data.get("output_schema", {}),
                required_capabilities=list(st_data.get("required_capabilities", [])),
                constraints=list(st_data.get("constraints", [])),
            )
            self._slot_types[std.id] = std

        self._loaded = True
        return self._slot_types

    def load_agent_capabilities(self) -> dict[str, AgentCapabilities]:
        """Parse YAML front-matter from all agent .md files.

        Front-matter is the YAML block between --- delimiters at the
        start of the file.

        Returns:
            Dict mapping agent_id -> AgentCapabilities.
        """
        self._agents = {}
        if not self._agents_dir.exists():
            return self._agents

        for md_file in sorted(self._agents_dir.glob("*.md")):
            front_matter = self._parse_front_matter(md_file)
            if front_matter is None:
                continue
            agent_id = front_matter.get("agent_id")
            if not agent_id:
                continue
            ac = AgentCapabilities(
                agent_id=str(agent_id),
                version=str(front_matter.get("version", "1.0")),
                capabilities=list(front_matter.get("capabilities", [])),
                compatible_slot_types=list(front_matter.get("compatible_slot_types", [])),
                prompt_path=str(md_file),
            )
            self._agents[ac.agent_id] = ac

        return self._agents

    def get_slot_type(self, slot_type_id: str) -> SlotTypeDefinition:
        """Look up a slot type by ID.

        Args:
            slot_type_id: The slot type ID (e.g., "designer").

        Returns:
            SlotTypeDefinition.

        Raises:
            SlotTypeNotFoundError: ID not found in registry.
        """
        if not self._loaded:
            self.load_slot_types()

        if slot_type_id not in self._slot_types:
            raise SlotTypeNotFoundError(
                f"Slot type '{slot_type_id}' not found in registry"
            )
        return self._slot_types[slot_type_id]

    def find_compatible_agents(
        self, slot_type_id: str
    ) -> list[CapabilityMatch]:
        """Find all agents whose capabilities satisfy a slot type.

        Matching rule:
            agent.capabilities SUPERSET_OF slot_type.required_capabilities

        Args:
            slot_type_id: The slot type to match against.

        Returns:
            List of CapabilityMatch objects, sorted by number of
            matched capabilities (descending).

        Raises:
            SlotTypeNotFoundError: slot_type_id not found.
        """
        slot_type = self.get_slot_type(slot_type_id)
        required = set(slot_type.required_capabilities)

        if not self._agents:
            self.load_agent_capabilities()

        matches: list[CapabilityMatch] = []
        for agent in self._agents.values():
            agent_caps = set(agent.capabilities)
            matched = sorted(required & agent_caps)
            missing = sorted(required - agent_caps)
            matches.append(CapabilityMatch(
                agent_id=agent.agent_id,
                prompt_path=agent.prompt_path,
                matched_capabilities=matched,
                missing_capabilities=missing,
                is_compatible=len(missing) == 0,
            ))

        matches.sort(key=lambda m: len(m.matched_capabilities), reverse=True)
        return matches

    def validate_assignment(
        self, slot_type_id: str, agent_id: str
    ) -> CapabilityMatch:
        """Check if a specific agent can fill a specific slot type.

        Args:
            slot_type_id: The slot type.
            agent_id: The agent to check.

        Returns:
            CapabilityMatch with is_compatible=True/False.

        Raises:
            SlotTypeNotFoundError: slot_type_id not found.
            KeyError: agent_id not found.
        """
        slot_type = self.get_slot_type(slot_type_id)
        required = set(slot_type.required_capabilities)

        if not self._agents:
            self.load_agent_capabilities()

        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not found in registry")

        agent = self._agents[agent_id]
        agent_caps = set(agent.capabilities)
        matched = sorted(required & agent_caps)
        missing = sorted(required - agent_caps)

        return CapabilityMatch(
            agent_id=agent.agent_id,
            prompt_path=agent.prompt_path,
            matched_capabilities=matched,
            missing_capabilities=missing,
            is_compatible=len(missing) == 0,
        )

    def generate_slot_manifest(self, pipeline: Pipeline) -> SlotManifest:
        """Generate a slot manifest for HR to fill.

        Lists all slots in the pipeline with their type and required
        capabilities.

        Args:
            pipeline: Pipeline definition.

        Returns:
            SlotManifest object.
        """
        if not self._loaded:
            self.load_slot_types()

        manifest_slots: list[dict[str, Any]] = []
        for slot in pipeline.slots:
            slot_entry: dict[str, Any] = {
                "slot_id": slot.id,
                "slot_type": slot.slot_type,
                "slot_name": slot.name,
            }
            if slot.slot_type in self._slot_types:
                st = self._slot_types[slot.slot_type]
                slot_entry["required_capabilities"] = list(st.required_capabilities)
            else:
                slot_entry["required_capabilities"] = []

            manifest_slots.append(slot_entry)

        return SlotManifest(
            pipeline_id=pipeline.id,
            slots=manifest_slots,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_front_matter(md_path: Path) -> dict | None:
        """Parse YAML front-matter from a markdown file.

        Front-matter is between the first --- and the second ---.
        Returns None if no front-matter found.
        """
        text = md_path.read_text(encoding="utf-8")
        lines = text.split("\n")

        if not lines or lines[0].strip() != "---":
            return None

        end_index = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break

        if end_index is None:
            return None

        yaml_text = "\n".join(lines[1:end_index])
        try:
            return yaml.safe_load(yaml_text)
        except yaml.YAMLError:
            return None
