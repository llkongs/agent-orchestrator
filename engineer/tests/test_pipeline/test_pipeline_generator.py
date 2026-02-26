"""Tests for pipeline.pipeline_generator -- Pipeline generation from blueprints."""

import pytest
import yaml

from src.pipeline.pipeline_generator import (
    GenerationResult,
    PipelineGenerator,
)
from src.pipeline.project_planner import (
    Phase,
    PhaseSlot,
    ProjectBlueprint,
    ProjectPlanner,
    RoleRequirement,
    Subsystem,
)
from src.pipeline.loader import PipelineLoader
from src.pipeline.validator import PipelineValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_blueprint() -> ProjectBlueprint:
    """Create a valid blueprint for testing."""
    return ProjectBlueprint(
        project_id="test-project",
        project_name="Test Project",
        domain="web-app",
        description="A test web application",
        roles=[
            RoleRequirement(
                role_id="architect",
                title="System Architect",
                capabilities=["system_design", "interface_definition"],
                responsibilities=["Design system architecture"],
                slot_type="designer",
                is_custom_type=False,
            ),
            RoleRequirement(
                role_id="dev",
                title="Developer",
                capabilities=["python_development", "test_writing"],
                responsibilities=["Implement features", "Write tests"],
                slot_type="implementer",
                is_custom_type=False,
            ),
            RoleRequirement(
                role_id="qa",
                title="QA Engineer",
                capabilities=["code_review", "cross_validation"],
                responsibilities=["Review code quality"],
                slot_type="reviewer",
                is_custom_type=False,
            ),
        ],
        subsystems=[
            Subsystem(
                id="backend",
                name="Backend",
                description="Server-side logic",
                roles=["architect", "dev"],
            ),
        ],
        phases=[
            Phase(
                id="phase-1",
                name="Design",
                order=1,
                slots=[
                    PhaseSlot(
                        slot_id="arch-design",
                        role_id="architect",
                        objective="Design system architecture",
                        inputs=[],
                        outputs=["design_doc"],
                    ),
                ],
                depends_on=[],
            ),
            Phase(
                id="phase-2",
                name="Implementation",
                order=2,
                slots=[
                    PhaseSlot(
                        slot_id="dev-implement",
                        role_id="dev",
                        objective="Implement backend",
                        inputs=["design_doc"],
                        outputs=["source_code", "test_code"],
                    ),
                ],
                depends_on=["phase-1"],
            ),
            Phase(
                id="phase-3",
                name="Review",
                order=3,
                slots=[
                    PhaseSlot(
                        slot_id="qa-review",
                        role_id="qa",
                        objective="Review implementation",
                        inputs=["source_code"],
                        outputs=["review_report"],
                    ),
                ],
                depends_on=["phase-2"],
            ),
        ],
        created_by="test",
        created_at="2026-02-26T00:00:00Z",
    )


def _make_custom_role_blueprint() -> ProjectBlueprint:
    """Create a blueprint with a custom role."""
    return ProjectBlueprint(
        project_id="roguelike-game",
        project_name="Roguelike Game",
        domain="game",
        description="A dungeon crawler roguelike",
        roles=[
            RoleRequirement(
                role_id="game-designer",
                title="Game Designer",
                capabilities=["game_design", "level_design", "narrative_design"],
                responsibilities=["Design game mechanics", "Design levels"],
                slot_type="game-designer",
                is_custom_type=True,
            ),
            RoleRequirement(
                role_id="dev",
                title="Game Developer",
                capabilities=["python_development", "test_writing"],
                responsibilities=["Implement game logic"],
                slot_type="implementer",
                is_custom_type=False,
            ),
        ],
        subsystems=[],
        phases=[
            Phase(
                id="phase-1",
                name="Design",
                order=1,
                slots=[
                    PhaseSlot(
                        slot_id="gd-design",
                        role_id="game-designer",
                        objective="Design game mechanics",
                        inputs=[],
                        outputs=["game_design_doc"],
                    ),
                ],
                depends_on=[],
            ),
            Phase(
                id="phase-2",
                name="Implement",
                order=2,
                slots=[
                    PhaseSlot(
                        slot_id="dev-implement",
                        role_id="dev",
                        objective="Implement game logic",
                        inputs=["game_design_doc"],
                        outputs=["game_code"],
                    ),
                ],
                depends_on=["phase-1"],
            ),
        ],
        created_by="test",
        created_at="2026-02-26T00:00:00Z",
    )


@pytest.fixture
def generator():
    return PipelineGenerator()


@pytest.fixture
def blueprint():
    return _make_blueprint()


@pytest.fixture
def custom_blueprint():
    return _make_custom_role_blueprint()


# ---------------------------------------------------------------------------
# Tests: generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_generate_returns_result(self, generator, blueprint):
        result = generator.generate(blueprint)
        assert isinstance(result, GenerationResult)
        assert result.pipeline_id == "test-project"
        assert result.pipeline_yaml  # Non-empty

    def test_generated_yaml_is_valid_yaml(self, generator, blueprint):
        result = generator.generate(blueprint)
        data = yaml.safe_load(result.pipeline_yaml)
        assert "pipeline" in data
        assert data["pipeline"]["id"] == "test-project"

    def test_generated_pipeline_has_all_slots(self, generator, blueprint):
        result = generator.generate(blueprint)
        data = yaml.safe_load(result.pipeline_yaml)
        slots = data["pipeline"]["slots"]
        slot_ids = [s["id"] for s in slots]
        assert "arch-design" in slot_ids
        assert "dev-implement" in slot_ids
        assert "qa-review" in slot_ids

    def test_generated_pipeline_has_data_flow(self, generator, blueprint):
        result = generator.generate(blueprint)
        data = yaml.safe_load(result.pipeline_yaml)
        data_flow = data["pipeline"]["data_flow"]
        # design_doc flows from arch-design to dev-implement
        design_flow = [
            e for e in data_flow
            if e["artifact"] == "design_doc"
        ]
        assert len(design_flow) >= 1
        assert design_flow[0]["from_slot"] == "arch-design"
        assert design_flow[0]["to_slot"] == "dev-implement"

    def test_generated_pipeline_has_dependencies(self, generator, blueprint):
        result = generator.generate(blueprint)
        data = yaml.safe_load(result.pipeline_yaml)
        slots = {s["id"]: s for s in data["pipeline"]["slots"]}
        # dev-implement depends on arch-design (via phase dependency)
        assert "arch-design" in slots["dev-implement"]["depends_on"]

    def test_agent_scaffolds_generated(self, generator, blueprint):
        result = generator.generate(blueprint)
        assert "architect-agent" in result.agent_scaffolds
        assert "dev-agent" in result.agent_scaffolds
        assert "qa-agent" in result.agent_scaffolds

    def test_agent_scaffold_has_frontmatter(self, generator, blueprint):
        result = generator.generate(blueprint)
        scaffold = result.agent_scaffolds["architect-agent"]
        assert scaffold.startswith("---")
        assert 'agent_id: "architect-agent"' in scaffold
        assert "system_design" in scaffold

    def test_no_custom_slot_types_for_builtin_roles(self, generator, blueprint):
        result = generator.generate(blueprint)
        assert result.slot_type_yamls == {}


# ---------------------------------------------------------------------------
# Tests: Custom slot types
# ---------------------------------------------------------------------------


class TestCustomSlotTypes:
    def test_custom_type_generated(self, generator, custom_blueprint):
        result = generator.generate(custom_blueprint)
        assert "game-designer" in result.slot_type_yamls

    def test_custom_type_is_valid_yaml(self, generator, custom_blueprint):
        result = generator.generate(custom_blueprint)
        data = yaml.safe_load(result.slot_type_yamls["game-designer"])
        assert "slot_type" in data
        assert data["slot_type"]["id"] == "game-designer"

    def test_custom_type_has_capabilities(self, generator, custom_blueprint):
        result = generator.generate(custom_blueprint)
        data = yaml.safe_load(result.slot_type_yamls["game-designer"])
        caps = data["slot_type"]["required_capabilities"]
        assert "game_design" in caps
        assert "level_design" in caps
        assert "narrative_design" in caps

    def test_builtin_role_not_duplicated(self, generator, custom_blueprint):
        result = generator.generate(custom_blueprint)
        # implementer is built-in, should not appear in custom types
        assert "implementer" not in result.slot_type_yamls


# ---------------------------------------------------------------------------
# Tests: Slot type resolution
# ---------------------------------------------------------------------------


class TestSlotTypeResolution:
    def test_designer_capabilities_match(self, generator):
        role = RoleRequirement(
            role_id="arch",
            title="Architect",
            capabilities=["system_design", "interface_definition"],
            responsibilities=["Design"],
            slot_type="designer",
            is_custom_type=False,
        )
        assert generator._resolve_slot_type(role) == "designer"

    def test_implementer_capabilities_match(self, generator):
        role = RoleRequirement(
            role_id="eng",
            title="Engineer",
            capabilities=["python_development", "test_writing"],
            responsibilities=["Code"],
            slot_type="implementer",
            is_custom_type=False,
        )
        assert generator._resolve_slot_type(role) == "implementer"

    def test_custom_type_preserves_slot_type(self, generator):
        role = RoleRequirement(
            role_id="gd",
            title="Game Designer",
            capabilities=["game_design"],
            responsibilities=["Design games"],
            slot_type="game-designer",
            is_custom_type=True,
        )
        assert generator._resolve_slot_type(role) == "game-designer"

    def test_no_slot_type_uses_capability_matching(self, generator):
        role = RoleRequirement(
            role_id="sec",
            title="Security Auditor",
            capabilities=["security_audit", "owasp_review"],
            responsibilities=["Audit security"],
            slot_type="",
            is_custom_type=False,
        )
        assert generator._resolve_slot_type(role) == "auditor"


# ---------------------------------------------------------------------------
# Tests: write_all
# ---------------------------------------------------------------------------


class TestWriteAll:
    def test_write_creates_files(self, generator, blueprint, tmp_path):
        result = generator.generate(blueprint)
        paths = generator.write_all(result, str(tmp_path))
        assert len(paths) > 0
        # Pipeline YAML
        pipeline_path = tmp_path / "pipelines" / "test-project.yaml"
        assert pipeline_path.exists()
        # Agent scaffolds
        for agent_id in result.agent_scaffolds:
            agent_path = tmp_path / "agents" / f"{agent_id}.md"
            assert agent_path.exists()

    def test_write_custom_slot_types(self, generator, custom_blueprint, tmp_path):
        result = generator.generate(custom_blueprint)
        generator.write_all(result, str(tmp_path))
        st_path = tmp_path / "slot-types" / "game-designer.yaml"
        assert st_path.exists()

    def test_written_pipeline_is_loadable(self, generator, blueprint, tmp_path):
        result = generator.generate(blueprint)
        generator.write_all(result, str(tmp_path))
        pipeline_path = tmp_path / "pipelines" / "test-project.yaml"
        loader = PipelineLoader()
        pipeline = loader.load(str(pipeline_path))
        assert pipeline.id == "test-project"
        assert len(pipeline.slots) == 3

    def test_written_pipeline_validates(self, generator, blueprint, tmp_path):
        result = generator.generate(blueprint)
        generator.write_all(result, str(tmp_path))
        pipeline_path = tmp_path / "pipelines" / "test-project.yaml"
        loader = PipelineLoader()
        pipeline = loader.load(str(pipeline_path))
        validator = PipelineValidator(str(tmp_path))
        vr = validator.validate(pipeline)
        assert vr.is_valid, f"Validation errors: {vr.errors}"


# ---------------------------------------------------------------------------
# Tests: Data flow inference
# ---------------------------------------------------------------------------


class TestDataFlowInference:
    def test_data_flow_edges_inferred(self, generator, blueprint):
        result = generator.generate(blueprint)
        data = yaml.safe_load(result.pipeline_yaml)
        edges = data["pipeline"]["data_flow"]
        # design_doc: arch-design -> dev-implement
        assert any(
            e["artifact"] == "design_doc"
            and e["from_slot"] == "arch-design"
            and e["to_slot"] == "dev-implement"
            for e in edges
        )
        # source_code: dev-implement -> qa-review
        assert any(
            e["artifact"] == "source_code"
            and e["from_slot"] == "dev-implement"
            and e["to_slot"] == "qa-review"
            for e in edges
        )

    def test_no_self_referencing_edges(self, generator, blueprint):
        result = generator.generate(blueprint)
        data = yaml.safe_load(result.pipeline_yaml)
        for edge in data["pipeline"]["data_flow"]:
            assert edge["from_slot"] != edge["to_slot"]


# ---------------------------------------------------------------------------
# Tests: Category inference
# ---------------------------------------------------------------------------


class TestCategoryInference:
    def test_architecture_category(self, generator):
        assert generator._infer_category(["system_design"]) == "architecture"

    def test_engineering_category(self, generator):
        assert generator._infer_category(["python_development"]) == "engineering"

    def test_quality_category(self, generator):
        assert generator._infer_category(["code_review"]) == "quality"

    def test_security_category(self, generator):
        assert generator._infer_category(["security_audit"]) == "security"

    def test_custom_category(self, generator):
        assert generator._infer_category(["game_design"]) == "custom"
