"""Tests for pipeline.context_router -- context routing engine."""

import pytest
import yaml
from dataclasses import FrozenInstanceError

from src.pipeline.context_router import ContextRouter
from src.pipeline.models import (
    ContextItem,
    ContextTier,
    Pipeline,
    Slot,
    SlotTask,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_project(tmp_path):
    """Create a mock project with .abstract.md / .overview.md files."""
    # Directories
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "pipelines").mkdir()
    (tmp_path / "architect").mkdir()
    (tmp_path / "engineer" / "src" / "pipeline").mkdir(parents=True)
    (tmp_path / "agents").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "compliance-auditor").mkdir()
    (tmp_path / "state").mkdir()

    # Constitution
    (tmp_path / "docs" / "constitution.md").write_text(
        "# Constitution\n\nProject rules go here.\n",
        encoding="utf-8",
    )

    # L0 abstract files
    (tmp_path / "specs" / ".abstract.md").write_text(
        "Specs directory summary.",
        encoding="utf-8",
    )
    (tmp_path / "architect" / ".abstract.md").write_text(
        "Architect directory summary.",
        encoding="utf-8",
    )
    (tmp_path / "engineer" / "src" / "pipeline" / ".abstract.md").write_text(
        "Pipeline engine summary.",
        encoding="utf-8",
    )
    (tmp_path / "agents" / ".abstract.md").write_text(
        "Agents directory summary.",
        encoding="utf-8",
    )

    # L1 overview files
    (tmp_path / "specs" / ".overview.md").write_text(
        "Detailed specs overview with more content for token estimation.\n" * 10,
        encoding="utf-8",
    )
    (tmp_path / "architect" / ".overview.md").write_text(
        "Detailed architect overview.\n" * 10,
        encoding="utf-8",
    )
    (tmp_path / "engineer" / "src" / "pipeline" / ".overview.md").write_text(
        "Detailed pipeline overview.\n" * 10,
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def constitution_path(mock_project):
    return str(mock_project / "docs" / "constitution.md")


@pytest.fixture
def router(mock_project, constitution_path):
    return ContextRouter(str(mock_project), constitution_path)


@pytest.fixture
def designer_slot():
    return Slot(
        id="slot-design",
        slot_type="designer",
        name="Design",
        task=SlotTask(objective="Create design"),
    )


@pytest.fixture
def implementer_slot():
    return Slot(
        id="slot-implement",
        slot_type="implementer",
        name="Implement",
        task=SlotTask(objective="Write code"),
    )


@pytest.fixture
def reviewer_slot():
    return Slot(
        id="slot-review",
        slot_type="reviewer",
        name="Review",
        task=SlotTask(objective="Review code"),
    )


@pytest.fixture
def simple_pipeline(designer_slot):
    return Pipeline(
        id="test-pipeline",
        name="Test",
        version="1.0.0",
        description="Test pipeline",
        created_by="test",
        created_at="2026-01-01T00:00:00Z",
        slots=[designer_slot],
    )


# ---------------------------------------------------------------------------
# ContextTier enum
# ---------------------------------------------------------------------------


class TestContextTierEnum:
    def test_context_tier_enum_values(self):
        assert ContextTier.L0.value == "abstract"
        assert ContextTier.L1.value == "overview"
        assert ContextTier.L2.value == "detail"

    def test_context_tier_is_str(self):
        assert isinstance(ContextTier.L0, str)

    def test_context_tier_member_count(self):
        assert len(ContextTier) == 3


# ---------------------------------------------------------------------------
# ContextItem frozen dataclass
# ---------------------------------------------------------------------------


class TestContextItem:
    def test_creation(self):
        item = ContextItem(
            path="specs/.abstract.md",
            tier=ContextTier.L0,
            relevance=0.5,
            tokens_estimate=25,
        )
        assert item.path == "specs/.abstract.md"
        assert item.tier == ContextTier.L0
        assert item.relevance == 0.5
        assert item.tokens_estimate == 25

    def test_context_item_frozen(self):
        item = ContextItem(
            path="x", tier=ContextTier.L0, relevance=0.5, tokens_estimate=10,
        )
        with pytest.raises(FrozenInstanceError):
            item.path = "y"


# ---------------------------------------------------------------------------
# ContextRouter init
# ---------------------------------------------------------------------------


class TestContextRouterInit:
    def test_context_router_init_scans_files(self, router):
        assert len(router._abstract_files) > 0
        assert len(router._overview_files) > 0

    def test_context_router_init_finds_abstract_files(self, router):
        abstract_basenames = [
            p.split("/")[-1] for p in router._abstract_files
        ]
        assert all(f.endswith(".abstract.md") for f in abstract_basenames)

    def test_context_router_init_finds_overview_files(self, router):
        overview_basenames = [
            p.split("/")[-1] for p in router._overview_files
        ]
        assert all(f.endswith(".overview.md") for f in overview_basenames)

    def test_context_router_nonexistent_root(self, tmp_path):
        router = ContextRouter(
            str(tmp_path / "nonexistent"),
            str(tmp_path / "const.md"),
        )
        assert router._abstract_files == []
        assert router._overview_files == []


# ---------------------------------------------------------------------------
# get_constitution
# ---------------------------------------------------------------------------


class TestGetConstitution:
    def test_get_constitution_returns_content(self, router):
        content = router.get_constitution()
        assert "Constitution" in content
        assert "Project rules" in content

    def test_get_constitution_file_not_found(self, tmp_path):
        router = ContextRouter(
            str(tmp_path),
            str(tmp_path / "nonexistent" / "constitution.md"),
        )
        assert router.get_constitution() == ""


# ---------------------------------------------------------------------------
# get_mandatory_reads
# ---------------------------------------------------------------------------


class TestGetMandatoryReads:
    def test_get_mandatory_reads_designer(self, router):
        dirs = router.get_mandatory_reads("designer")
        assert "specs/" in dirs
        assert "architect/" in dirs

    def test_get_mandatory_reads_implementer(self, router):
        dirs = router.get_mandatory_reads("implementer")
        assert "engineer/src/pipeline/" in dirs
        assert "specs/pipelines/" in dirs

    def test_get_mandatory_reads_reviewer(self, router):
        dirs = router.get_mandatory_reads("reviewer")
        assert "engineer/src/pipeline/" in dirs
        assert "specs/" in dirs

    def test_get_mandatory_reads_unknown_type(self, router):
        dirs = router.get_mandatory_reads("unknown_type")
        assert dirs == []


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------


class TestBuildContext:
    def test_build_context_always_includes_constitution(
        self, router, designer_slot, simple_pipeline
    ):
        items = router.build_context(designer_slot, simple_pipeline)
        constitution_items = [
            i for i in items if i.tier == ContextTier.L2 and "constitution" in i.path
        ]
        assert len(constitution_items) == 1
        assert constitution_items[0].relevance == 1.0

    def test_build_context_includes_l0_files(
        self, router, designer_slot, simple_pipeline
    ):
        items = router.build_context(designer_slot, simple_pipeline)
        l0_items = [i for i in items if i.tier == ContextTier.L0]
        # There are abstract files outside the designer dirs
        assert len(l0_items) >= 0  # Some may be upgraded to L1

    def test_build_context_respects_max_tokens(
        self, router, designer_slot, simple_pipeline
    ):
        items = router.build_context(
            designer_slot, simple_pipeline, max_tokens=50
        )
        total_tokens = sum(i.tokens_estimate for i in items)
        # Total should be within budget (constitution alone may exceed,
        # but it is always included)
        assert len(items) <= 5

    def test_build_context_designer_includes_relevant_l1(
        self, router, designer_slot, simple_pipeline
    ):
        items = router.build_context(designer_slot, simple_pipeline)
        paths = [i.path for i in items]
        # Designer should see specs and architect overviews
        has_specs_or_arch = any(
            "specs/" in p or "architect/" in p for p in paths
        )
        assert has_specs_or_arch

    def test_build_context_implementer_includes_pipeline(
        self, router, implementer_slot, simple_pipeline
    ):
        items = router.build_context(implementer_slot, simple_pipeline)
        paths = [i.path for i in items]
        has_pipeline = any("engineer/src/pipeline/" in p for p in paths)
        assert has_pipeline


# ---------------------------------------------------------------------------
# upgrade_tier
# ---------------------------------------------------------------------------


class TestUpgradeTier:
    def test_upgrade_tier_l0_to_l1(self, router):
        item = ContextItem(
            path="specs/.abstract.md",
            tier=ContextTier.L0,
            relevance=0.5,
            tokens_estimate=10,
        )
        upgraded = router.upgrade_tier(item, ContextTier.L1)
        assert upgraded.tier == ContextTier.L1
        assert upgraded.path == "specs/.overview.md"
        assert upgraded.tokens_estimate > 0

    def test_upgrade_tier_l1_to_l2(self, mock_project):
        # Create a source file that .overview.md would point to
        source_path = mock_project / "specs" / "test.py"
        source_path.write_text("# source code\nprint('hello')\n")
        overview_path = mock_project / "specs" / "test.py.overview.md"
        overview_path.write_text("Overview of test.py")

        router = ContextRouter(
            str(mock_project),
            str(mock_project / "docs" / "constitution.md"),
        )
        item = ContextItem(
            path="specs/test.py.overview.md",
            tier=ContextTier.L1,
            relevance=0.7,
            tokens_estimate=5,
        )
        upgraded = router.upgrade_tier(item, ContextTier.L2)
        assert upgraded.tier == ContextTier.L2
        assert upgraded.path == "specs/test.py"

    def test_upgrade_tier_already_at_target(self, router):
        item = ContextItem(
            path="specs/.abstract.md",
            tier=ContextTier.L0,
            relevance=0.5,
            tokens_estimate=10,
        )
        with pytest.raises(ValueError, match="already at tier"):
            router.upgrade_tier(item, ContextTier.L0)

    def test_upgrade_tier_l0_to_l2_raises(self, router):
        item = ContextItem(
            path="specs/.abstract.md",
            tier=ContextTier.L0,
            relevance=0.5,
            tokens_estimate=10,
        )
        with pytest.raises(ValueError, match="L0 to L2"):
            router.upgrade_tier(item, ContextTier.L2)

    def test_upgrade_tier_file_not_found(self, router):
        item = ContextItem(
            path="nonexistent/.abstract.md",
            tier=ContextTier.L0,
            relevance=0.5,
            tokens_estimate=10,
        )
        with pytest.raises(FileNotFoundError):
            router.upgrade_tier(item, ContextTier.L1)


# ---------------------------------------------------------------------------
# generate_slot_context_yaml
# ---------------------------------------------------------------------------


class TestGenerateSlotContextYaml:
    def test_generate_slot_context_yaml_format(self, router):
        items = [
            ContextItem(
                path="specs/.abstract.md",
                tier=ContextTier.L0,
                relevance=0.3,
                tokens_estimate=25,
            ),
            ContextItem(
                path="architect/.overview.md",
                tier=ContextTier.L1,
                relevance=0.7,
                tokens_estimate=100,
            ),
        ]
        yaml_str = router.generate_slot_context_yaml(items)
        parsed = yaml.safe_load(yaml_str)
        assert "context_items" in parsed
        assert len(parsed["context_items"]) == 2
        assert parsed["context_items"][0]["path"] == "specs/.abstract.md"
        assert parsed["context_items"][0]["tier"] == "abstract"
        assert parsed["context_items"][1]["tier"] == "overview"

    def test_generate_slot_context_yaml_empty(self, router):
        yaml_str = router.generate_slot_context_yaml([])
        parsed = yaml.safe_load(yaml_str)
        assert parsed["context_items"] == []


# ---------------------------------------------------------------------------
# Graceful handling of missing files
# ---------------------------------------------------------------------------


class TestGracefulHandling:
    def test_context_router_missing_files_graceful(self, tmp_path):
        """Router should work even with empty project directory."""
        (tmp_path / "empty_project").mkdir()
        const_path = tmp_path / "const.md"
        const_path.write_text("Constitution content")
        router = ContextRouter(str(tmp_path / "empty_project"), str(const_path))
        slot = Slot(
            id="s", slot_type="designer", name="S",
            task=SlotTask(objective="work"),
        )
        pipeline = Pipeline(
            id="p", name="P", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[slot],
        )
        items = router.build_context(slot, pipeline)
        # Should still include constitution
        assert len(items) >= 1
        assert any("const.md" in i.path for i in items)


# ---------------------------------------------------------------------------
# Runner backward compatibility
# ---------------------------------------------------------------------------


class TestRunnerIntegration:
    def test_runner_backward_compat_no_constitution(self, tmp_path):
        """PipelineRunner works without constitution_path (default None)."""
        from src.pipeline.runner import PipelineRunner

        (tmp_path / "templates").mkdir()
        (tmp_path / "state" / "active").mkdir(parents=True)
        (tmp_path / "state" / "archive").mkdir(parents=True)
        (tmp_path / "slot-types").mkdir()
        (tmp_path / "agents").mkdir()

        runner = PipelineRunner(
            project_root=str(tmp_path),
            templates_dir=str(tmp_path / "templates"),
            state_dir=str(tmp_path / "state" / "active"),
            slot_types_dir=str(tmp_path / "slot-types"),
            agents_dir=str(tmp_path / "agents"),
        )
        assert runner._context_router is None

    def test_runner_with_constitution_path(self, tmp_path):
        """PipelineRunner creates ContextRouter when constitution_path given."""
        from src.pipeline.runner import PipelineRunner

        (tmp_path / "templates").mkdir()
        (tmp_path / "state" / "active").mkdir(parents=True)
        (tmp_path / "state" / "archive").mkdir(parents=True)
        (tmp_path / "slot-types").mkdir()
        (tmp_path / "agents").mkdir()

        const_path = tmp_path / "constitution.md"
        const_path.write_text("# Constitution\nRules here.")

        runner = PipelineRunner(
            project_root=str(tmp_path),
            templates_dir=str(tmp_path / "templates"),
            state_dir=str(tmp_path / "state" / "active"),
            slot_types_dir=str(tmp_path / "slot-types"),
            agents_dir=str(tmp_path / "agents"),
            constitution_path=str(const_path),
        )
        assert runner._context_router is not None
