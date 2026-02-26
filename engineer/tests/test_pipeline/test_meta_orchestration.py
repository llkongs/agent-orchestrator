"""Integration tests for meta-orchestration end-to-end flow.

Tests the complete pipeline: Blueprint YAML -> ProjectPlanner -> PipelineGenerator
-> PipelineLoader -> PipelineValidator -> all pass.
Also tests NLMatcher routing for inception requests.
"""

import pytest
import yaml

from src.pipeline.loader import PipelineLoader
from src.pipeline.nl_matcher import NLMatcher
from src.pipeline.pipeline_generator import PipelineGenerator
from src.pipeline.project_planner import ProjectPlanner
from src.pipeline.validator import PipelineValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_BLUEPRINT = {
    "blueprint": {
        "project_id": "roguelike-dungeon",
        "project_name": "Roguelike Dungeon Crawler",
        "domain": "game",
        "description": "A turn-based roguelike dungeon crawler with procedural generation",
        "created_by": "meta-orchestration",
        "created_at": "2026-02-26T00:00:00Z",
        "roles": [
            {
                "role_id": "game-designer",
                "title": "Game Designer",
                "capabilities": ["game_design", "level_design", "narrative_design"],
                "responsibilities": [
                    "Design core gameplay loop",
                    "Design dungeon generation rules",
                    "Design item and enemy systems",
                ],
                "slot_type": "game-designer",
                "is_custom_type": True,
            },
            {
                "role_id": "numerical-planner",
                "title": "Numerical Planner",
                "capabilities": ["numerical_balance", "formula_design", "data_analysis"],
                "responsibilities": [
                    "Design damage formulas",
                    "Balance progression curves",
                    "Design loot tables",
                ],
                "slot_type": "numerical-planner",
                "is_custom_type": True,
            },
            {
                "role_id": "engine-dev",
                "title": "Game Engine Developer",
                "capabilities": ["python_development", "test_writing"],
                "responsibilities": [
                    "Implement game engine",
                    "Implement procedural generation",
                ],
                "slot_type": "implementer",
                "is_custom_type": False,
            },
            {
                "role_id": "qa",
                "title": "QA Tester",
                "capabilities": ["independent_testing", "code_review", "cross_validation"],
                "responsibilities": ["Test gameplay balance", "Review code quality"],
                "slot_type": "reviewer",
                "is_custom_type": False,
            },
            {
                "role_id": "lead",
                "title": "Project Lead",
                "capabilities": ["decision_making"],
                "responsibilities": ["Approve milestones"],
                "slot_type": "approver",
                "is_custom_type": False,
            },
        ],
        "subsystems": [
            {
                "id": "game-core",
                "name": "Core Game Mechanics",
                "description": "Combat, movement, and interaction systems",
                "roles": ["game-designer", "numerical-planner", "engine-dev"],
            },
            {
                "id": "procgen",
                "name": "Procedural Generation",
                "description": "Dungeon and content generation systems",
                "roles": ["game-designer", "engine-dev"],
            },
        ],
        "phases": [
            {
                "id": "phase-1-design",
                "name": "Game Design",
                "order": 1,
                "depends_on": [],
                "parallel_group": "design-phase",
                "slots": [
                    {
                        "slot_id": "gd-mechanics",
                        "role_id": "game-designer",
                        "objective": "Design core game mechanics",
                        "inputs": [],
                        "outputs": ["game_design_doc"],
                    },
                    {
                        "slot_id": "np-balance",
                        "role_id": "numerical-planner",
                        "objective": "Design numerical balance",
                        "inputs": [],
                        "outputs": ["balance_doc"],
                    },
                ],
            },
            {
                "id": "phase-2-implement",
                "name": "Implementation",
                "order": 2,
                "depends_on": ["phase-1-design"],
                "slots": [
                    {
                        "slot_id": "eng-implement",
                        "role_id": "engine-dev",
                        "objective": "Implement game engine",
                        "inputs": ["game_design_doc", "balance_doc"],
                        "outputs": ["source_code", "test_code"],
                    },
                ],
            },
            {
                "id": "phase-3-review",
                "name": "Quality Review",
                "order": 3,
                "depends_on": ["phase-2-implement"],
                "slots": [
                    {
                        "slot_id": "qa-review",
                        "role_id": "qa",
                        "objective": "Review game quality",
                        "inputs": ["source_code"],
                        "outputs": ["review_report"],
                    },
                ],
            },
            {
                "id": "phase-4-approve",
                "name": "Launch Approval",
                "order": 4,
                "depends_on": ["phase-3-review"],
                "slots": [
                    {
                        "slot_id": "lead-approve",
                        "role_id": "lead",
                        "objective": "Approve for launch",
                        "inputs": ["review_report"],
                        "outputs": ["launch_decision"],
                    },
                ],
            },
        ],
    }
}


@pytest.fixture
def blueprint_file(tmp_path):
    path = tmp_path / "blueprint.yaml"
    path.write_text(yaml.dump(_SAMPLE_BLUEPRINT))
    return str(path)


@pytest.fixture
def inception_templates_dir(tmp_path):
    """Create a templates dir with the project-inception template."""
    d = tmp_path / "templates"
    d.mkdir()
    (d / "project-inception.yaml").write_text(
        yaml.dump({
            "pipeline": {
                "id": "project-inception",
                "name": "Project Inception (Meta-Orchestration)",
                "description": "Meta-pipeline for project inception",
                "version": "1.0.0",
                "created_by": "meta-orchestration",
                "created_at": "2026-02-26",
            }
        })
    )
    # Add a standard-feature for comparison
    (d / "standard-feature.yaml").write_text(
        yaml.dump({
            "pipeline": {
                "id": "standard-feature",
                "name": "Standard Feature",
                "description": "Standard feature pipeline",
                "version": "1.0.0",
                "created_by": "test",
                "created_at": "2026-01-01",
            }
        })
    )
    return str(d)


# ---------------------------------------------------------------------------
# End-to-end: Blueprint -> Generate -> Load -> Validate
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_pipeline(self, blueprint_file, tmp_path):
        """E2E: Blueprint YAML -> PipelineGenerator -> PipelineLoader -> PipelineValidator."""
        # 1. Parse blueprint
        planner = ProjectPlanner()
        bp = planner.parse_blueprint(blueprint_file)

        # 2. Validate blueprint
        bp_result = planner.validate_blueprint(bp)
        assert bp_result.is_valid, f"Blueprint errors: {bp_result.errors}"

        # 3. Generate pipeline
        generator = PipelineGenerator()
        gen_result = generator.generate(bp)
        assert gen_result.pipeline_id == "roguelike-dungeon"

        # 4. Write to disk
        output_dir = tmp_path / "output"
        paths = generator.write_all(gen_result, str(output_dir))
        assert len(paths) > 0

        # 5. Load with PipelineLoader
        pipeline_path = output_dir / "pipelines" / "roguelike-dungeon.yaml"
        assert pipeline_path.exists()

        loader = PipelineLoader()
        pipeline = loader.load(str(pipeline_path))
        assert pipeline.id == "roguelike-dungeon"
        assert pipeline.name == "Roguelike Dungeon Crawler"

        # 6. Validate with PipelineValidator
        validator = PipelineValidator(str(output_dir))
        val_result = validator.validate(pipeline)
        assert val_result.is_valid, f"Pipeline validation errors: {val_result.errors}"

    def test_correct_slot_count(self, blueprint_file, tmp_path):
        planner = ProjectPlanner()
        bp = planner.parse_blueprint(blueprint_file)
        generator = PipelineGenerator()
        gen_result = generator.generate(bp)
        output_dir = tmp_path / "output"
        generator.write_all(gen_result, str(output_dir))

        loader = PipelineLoader()
        pipeline = loader.load(
            str(output_dir / "pipelines" / "roguelike-dungeon.yaml")
        )
        # 5 slots: gd-mechanics, np-balance, eng-implement, qa-review, lead-approve
        assert len(pipeline.slots) == 5

    def test_custom_slot_types_generated(self, blueprint_file, tmp_path):
        planner = ProjectPlanner()
        bp = planner.parse_blueprint(blueprint_file)
        generator = PipelineGenerator()
        gen_result = generator.generate(bp)

        # Two custom types: game-designer, numerical-planner
        assert "game-designer" in gen_result.slot_type_yamls
        assert "numerical-planner" in gen_result.slot_type_yamls
        # Built-in types not duplicated
        assert "implementer" not in gen_result.slot_type_yamls
        assert "reviewer" not in gen_result.slot_type_yamls

    def test_all_agents_scaffolded(self, blueprint_file, tmp_path):
        planner = ProjectPlanner()
        bp = planner.parse_blueprint(blueprint_file)
        generator = PipelineGenerator()
        gen_result = generator.generate(bp)

        assert len(gen_result.agent_scaffolds) == 5
        assert "game-designer-agent" in gen_result.agent_scaffolds
        assert "numerical-planner-agent" in gen_result.agent_scaffolds
        assert "engine-dev-agent" in gen_result.agent_scaffolds

    def test_data_flow_connects_phases(self, blueprint_file, tmp_path):
        planner = ProjectPlanner()
        bp = planner.parse_blueprint(blueprint_file)
        generator = PipelineGenerator()
        gen_result = generator.generate(bp)
        data = yaml.safe_load(gen_result.pipeline_yaml)
        edges = data["pipeline"]["data_flow"]

        # game_design_doc: gd-mechanics -> eng-implement
        assert any(
            e["artifact"] == "game_design_doc"
            and e["from_slot"] == "gd-mechanics"
            for e in edges
        )
        # balance_doc: np-balance -> eng-implement
        assert any(
            e["artifact"] == "balance_doc"
            and e["from_slot"] == "np-balance"
            for e in edges
        )

    def test_parallel_group_preserved(self, blueprint_file, tmp_path):
        planner = ProjectPlanner()
        bp = planner.parse_blueprint(blueprint_file)
        generator = PipelineGenerator()
        gen_result = generator.generate(bp)
        data = yaml.safe_load(gen_result.pipeline_yaml)
        slots = {s["id"]: s for s in data["pipeline"]["slots"]}

        # Design phase slots should have parallel_group
        assert slots["gd-mechanics"]["execution"].get("parallel_group") == "design-phase"
        assert slots["np-balance"]["execution"].get("parallel_group") == "design-phase"


# ---------------------------------------------------------------------------
# NLMatcher inception routing
# ---------------------------------------------------------------------------


class TestNLMatcherInception:
    def test_create_game_routes_to_inception(self, inception_templates_dir):
        matcher = NLMatcher(inception_templates_dir)
        # Rich input with many inception keywords to exceed threshold
        results = matcher.match(
            "create a roguelike game project, build the team and design the system"
        )
        assert len(results) > 0
        # project-inception should be among results
        template_ids = [r.template_id for r in results]
        assert "project-inception" in template_ids

    def test_build_application_routes_to_inception(self, inception_templates_dir):
        matcher = NLMatcher(inception_templates_dir)
        results = matcher.match("build a web application platform system from scratch")
        assert len(results) > 0
        assert results[0].template_id == "project-inception"

    def test_chinese_creation_routes_to_inception(self, inception_templates_dir):
        matcher = NLMatcher(inception_templates_dir)
        results = matcher.match("创建一个roguelike游戏项目 构建团队 设计系统")
        assert len(results) > 0
        template_ids = [r.template_id for r in results]
        assert "project-inception" in template_ids

    def test_inception_matches_with_enough_keywords(self, inception_templates_dir):
        matcher = NLMatcher(inception_templates_dir)
        # Input hitting many inception keywords
        results = matcher.match(
            "develop a game product, create team pipeline, design and build system"
        )
        template_ids = [r.template_id for r in results]
        assert "project-inception" in template_ids

    def test_specific_feature_still_matches_standard(self, inception_templates_dir):
        matcher = NLMatcher(inception_templates_dir)
        results = matcher.match("implement a new feature for user authentication")
        # "feature" + "implement" should favor standard-feature
        # Both may match, but standard-feature should be strong
        template_ids = [r.template_id for r in results]
        assert "standard-feature" in template_ids


# ---------------------------------------------------------------------------
# Blueprint serialization roundtrip with generation
# ---------------------------------------------------------------------------


class TestBlueprintRoundtrip:
    def test_serialize_then_generate(self, tmp_path):
        """Serialize blueprint, reload, generate — same result."""
        planner = ProjectPlanner()
        data = _SAMPLE_BLUEPRINT["blueprint"]
        bp1 = planner.parse_blueprint_from_string(yaml.dump(data))

        # Serialize
        yaml_text = planner.serialize_blueprint(bp1)
        bp2 = planner.parse_blueprint_from_string(yaml_text)

        # Generate from both
        gen = PipelineGenerator()
        r1 = gen.generate(bp1)
        r2 = gen.generate(bp2)

        assert r1.pipeline_id == r2.pipeline_id
        assert len(r1.slot_type_yamls) == len(r2.slot_type_yamls)
        assert len(r1.agent_scaffolds) == len(r2.agent_scaffolds)
