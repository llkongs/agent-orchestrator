"""Tests for pipeline.project_planner -- Blueprint data model and validation."""

import pytest
import yaml

from src.pipeline.project_planner import (
    BlueprintLoadError,
    BlueprintValidationResult,
    Phase,
    PhaseSlot,
    ProjectBlueprint,
    ProjectPlanner,
    RoleRequirement,
    Subsystem,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_valid_blueprint_dict() -> dict:
    """Return a minimal valid blueprint dict."""
    return {
        "project_id": "roguelike-game",
        "project_name": "Roguelike Game",
        "domain": "game",
        "description": "A roguelike dungeon crawler",
        "created_by": "meta-orchestration",
        "created_at": "2026-02-26T00:00:00Z",
        "roles": [
            {
                "role_id": "game-designer",
                "title": "Game Designer",
                "capabilities": ["game_design", "level_design"],
                "responsibilities": ["Design game mechanics", "Design levels"],
                "slot_type": "game-designer",
                "is_custom_type": True,
            },
            {
                "role_id": "engineer",
                "title": "Game Engineer",
                "capabilities": ["python_development", "test_writing"],
                "responsibilities": ["Implement game logic", "Write tests"],
                "slot_type": "implementer",
                "is_custom_type": False,
            },
        ],
        "subsystems": [
            {
                "id": "game-core",
                "name": "Game Core",
                "description": "Core game mechanics",
                "roles": ["game-designer", "engineer"],
            },
        ],
        "phases": [
            {
                "id": "phase-1-design",
                "name": "Design Phase",
                "order": 1,
                "depends_on": [],
                "slots": [
                    {
                        "slot_id": "design-mechanics",
                        "role_id": "game-designer",
                        "objective": "Design core game mechanics",
                        "inputs": [],
                        "outputs": ["game_design_doc"],
                    },
                ],
            },
            {
                "id": "phase-2-implement",
                "name": "Implementation Phase",
                "order": 2,
                "depends_on": ["phase-1-design"],
                "slots": [
                    {
                        "slot_id": "implement-core",
                        "role_id": "engineer",
                        "objective": "Implement core game logic",
                        "inputs": ["game_design_doc"],
                        "outputs": ["game_code"],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def planner():
    return ProjectPlanner()


@pytest.fixture
def valid_blueprint_yaml(tmp_path):
    """Write valid blueprint YAML to a temp file."""
    data = _make_valid_blueprint_dict()
    path = tmp_path / "blueprint.yaml"
    path.write_text(yaml.dump({"blueprint": data}))
    return str(path)


@pytest.fixture
def valid_blueprint(planner, valid_blueprint_yaml):
    return planner.parse_blueprint(valid_blueprint_yaml)


# ---------------------------------------------------------------------------
# Tests: parse_blueprint
# ---------------------------------------------------------------------------


class TestParseBlueprint:
    def test_parse_valid_blueprint(self, planner, valid_blueprint_yaml):
        bp = planner.parse_blueprint(valid_blueprint_yaml)
        assert bp.project_id == "roguelike-game"
        assert bp.project_name == "Roguelike Game"
        assert bp.domain == "game"
        assert len(bp.roles) == 2
        assert len(bp.subsystems) == 1
        assert len(bp.phases) == 2

    def test_parse_without_wrapper_key(self, planner, tmp_path):
        data = _make_valid_blueprint_dict()
        path = tmp_path / "bare.yaml"
        path.write_text(yaml.dump(data))
        bp = planner.parse_blueprint(str(path))
        assert bp.project_id == "roguelike-game"

    def test_parse_file_not_found(self, planner):
        with pytest.raises(BlueprintLoadError, match="not found"):
            planner.parse_blueprint("/nonexistent/path.yaml")

    def test_parse_empty_file(self, planner, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("")
        with pytest.raises(BlueprintLoadError, match="Empty"):
            planner.parse_blueprint(str(path))

    def test_parse_malformed_yaml(self, planner, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(":\n  - :\n    - [invalid")
        with pytest.raises(BlueprintLoadError, match="Malformed"):
            planner.parse_blueprint(str(path))

    def test_parse_missing_required_fields(self, planner, tmp_path):
        data = {"project_id": "test"}  # Missing most fields
        path = tmp_path / "incomplete.yaml"
        path.write_text(yaml.dump(data))
        with pytest.raises(BlueprintLoadError, match="Missing required"):
            planner.parse_blueprint(str(path))

    def test_parse_roles_hydration(self, valid_blueprint):
        gd = valid_blueprint.roles[0]
        assert gd.role_id == "game-designer"
        assert gd.title == "Game Designer"
        assert gd.capabilities == ["game_design", "level_design"]
        assert gd.is_custom_type is True

    def test_parse_phases_hydration(self, valid_blueprint):
        p2 = valid_blueprint.phases[1]
        assert p2.id == "phase-2-implement"
        assert p2.order == 2
        assert p2.depends_on == ["phase-1-design"]
        assert len(p2.slots) == 1
        assert p2.slots[0].slot_id == "implement-core"

    def test_parse_from_string(self, planner):
        data = _make_valid_blueprint_dict()
        yaml_text = yaml.dump(data)
        bp = planner.parse_blueprint_from_string(yaml_text)
        assert bp.project_id == "roguelike-game"
        assert len(bp.roles) == 2


# ---------------------------------------------------------------------------
# Tests: validate_blueprint
# ---------------------------------------------------------------------------


class TestValidateBlueprint:
    def test_valid_blueprint_passes(self, planner, valid_blueprint):
        result = planner.validate_blueprint(valid_blueprint)
        assert result.is_valid is True
        assert result.errors == []

    def test_duplicate_role_ids(self, planner):
        data = _make_valid_blueprint_dict()
        data["roles"].append(data["roles"][0])  # Duplicate
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert not result.is_valid
        assert any("Duplicate role ID" in e for e in result.errors)

    def test_duplicate_slot_ids(self, planner):
        data = _make_valid_blueprint_dict()
        # Add a slot with same ID in phase 2
        data["phases"][1]["slots"].append({
            "slot_id": "design-mechanics",  # Same as phase 1
            "role_id": "engineer",
            "objective": "Duplicate",
            "inputs": [],
            "outputs": [],
        })
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert not result.is_valid
        assert any("Duplicate slot ID" in e for e in result.errors)

    def test_invalid_role_reference(self, planner):
        data = _make_valid_blueprint_dict()
        data["phases"][0]["slots"][0]["role_id"] = "nonexistent-role"
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert not result.is_valid
        assert any("not found in roles" in e for e in result.errors)

    def test_invalid_phase_dependency(self, planner):
        data = _make_valid_blueprint_dict()
        data["phases"][1]["depends_on"] = ["nonexistent-phase"]
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert not result.is_valid
        assert any("does not exist" in e for e in result.errors)

    def test_cyclic_phase_dependencies(self, planner):
        data = _make_valid_blueprint_dict()
        # Make phase-1 depend on phase-2 (creating a cycle)
        data["phases"][0]["depends_on"] = ["phase-2-implement"]
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert not result.is_valid
        assert any("cycle" in e.lower() for e in result.errors)

    def test_unused_role_warning(self, planner):
        data = _make_valid_blueprint_dict()
        data["roles"].append({
            "role_id": "unused-role",
            "title": "Unused",
            "capabilities": ["nothing"],
            "responsibilities": ["nothing"],
            "slot_type": "designer",
        })
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert result.is_valid  # Warnings don't fail validation
        assert any("never used" in w for w in result.warnings)

    def test_invalid_subsystem_role_ref(self, planner):
        data = _make_valid_blueprint_dict()
        data["subsystems"][0]["roles"].append("nonexistent-role")
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert not result.is_valid
        assert any("not found" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Tests: serialize_blueprint
# ---------------------------------------------------------------------------


class TestSerializeBlueprint:
    def test_roundtrip(self, planner, valid_blueprint):
        yaml_text = planner.serialize_blueprint(valid_blueprint)
        bp2 = planner.parse_blueprint_from_string(yaml_text)
        assert bp2.project_id == valid_blueprint.project_id
        assert bp2.project_name == valid_blueprint.project_name
        assert len(bp2.roles) == len(valid_blueprint.roles)
        assert len(bp2.phases) == len(valid_blueprint.phases)

    def test_serialize_produces_valid_yaml(self, planner, valid_blueprint):
        yaml_text = planner.serialize_blueprint(valid_blueprint)
        data = yaml.safe_load(yaml_text)
        assert "blueprint" in data
        assert data["blueprint"]["project_id"] == "roguelike-game"


# ---------------------------------------------------------------------------
# Tests: generate_inception_context
# ---------------------------------------------------------------------------


class TestGenerateInceptionContext:
    def test_context_has_required_fields(self, planner, valid_blueprint):
        ctx = planner.generate_inception_context(valid_blueprint)
        assert ctx["project_id"] == "roguelike-game"
        assert ctx["domain"] == "game"
        assert ctx["total_roles"] == 2
        assert ctx["custom_slot_types_needed"] == 1  # game-designer
        assert ctx["reusable_slot_types"] == 1  # engineer
        assert ctx["total_phases"] == 2
        assert ctx["total_slots"] == 2

    def test_custom_roles_listed(self, planner, valid_blueprint):
        ctx = planner.generate_inception_context(valid_blueprint)
        assert len(ctx["custom_roles"]) == 1
        assert ctx["custom_roles"][0]["role_id"] == "game-designer"


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_phase_project(self, planner):
        data = _make_valid_blueprint_dict()
        data["phases"] = [data["phases"][0]]  # Only design phase
        # Remove engineer role reference since phase 2 is gone
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        # Engineer role is unused now, so warning
        assert result.is_valid
        assert any("engineer" in w for w in result.warnings)

    def test_empty_subsystems(self, planner):
        data = _make_valid_blueprint_dict()
        data["subsystems"] = []
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        result = planner.validate_blueprint(bp)
        assert result.is_valid  # Subsystems are optional

    def test_phase_with_parallel_group(self, planner):
        data = _make_valid_blueprint_dict()
        data["phases"][0]["parallel_group"] = "design-parallel"
        bp = planner.parse_blueprint_from_string(yaml.dump(data))
        assert bp.phases[0].parallel_group == "design-parallel"

    def test_frozen_dataclasses(self, valid_blueprint):
        with pytest.raises(AttributeError):
            valid_blueprint.project_id = "mutated"  # type: ignore

        with pytest.raises(AttributeError):
            valid_blueprint.roles[0].role_id = "mutated"  # type: ignore
