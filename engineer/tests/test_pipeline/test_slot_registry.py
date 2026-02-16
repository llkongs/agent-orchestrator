"""Tests for pipeline.slot_registry -- SlotType loading and agent matching."""

import pytest
from pathlib import Path

from src.pipeline.slot_registry import SlotRegistry, SlotTypeNotFoundError, SlotManifest
from src.pipeline.models import (
    AgentCapabilities,
    CapabilityMatch,
    Pipeline,
    Slot,
    SlotTask,
    SlotTypeDefinition,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def slot_types_dir(tmp_path):
    """Create temp dir with sample slot type YAML files."""
    d = tmp_path / "slot-types"
    d.mkdir()
    (d / "implementer.yaml").write_text(
        (FIXTURES_DIR / "sample-slot-type.yaml").read_text()
    )
    (d / "designer.yaml").write_text(
        (FIXTURES_DIR / "sample-slot-type-designer.yaml").read_text()
    )
    return d


@pytest.fixture
def agents_dir(tmp_path):
    """Create temp dir with sample agent .md files."""
    d = tmp_path / "agents"
    d.mkdir()
    (d / "02-engineer-agent.md").write_text(
        (FIXTURES_DIR / "sample-agent.md").read_text()
    )
    (d / "01-architect-agent.md").write_text(
        (FIXTURES_DIR / "sample-agent-2.md").read_text()
    )
    return d


@pytest.fixture
def registry(slot_types_dir, agents_dir):
    return SlotRegistry(str(slot_types_dir), str(agents_dir))


class TestLoadSlotTypes:
    def test_loads_all_types(self, registry):
        types = registry.load_slot_types()
        assert len(types) >= 2
        assert "implementer" in types
        assert "designer" in types

    def test_slot_type_fields(self, registry):
        types = registry.load_slot_types()
        impl = types["implementer"]
        assert impl.id == "implementer"
        assert impl.name == "Code Implementer"
        assert impl.category == "engineering"
        assert "python_development" in impl.required_capabilities
        assert len(impl.constraints) > 0

    def test_empty_dir(self, tmp_path):
        empty = tmp_path / "empty-types"
        empty.mkdir()
        reg = SlotRegistry(str(empty), str(tmp_path / "agents"))
        types = reg.load_slot_types()
        assert types == {}

    def test_nonexistent_dir(self, tmp_path):
        reg = SlotRegistry(str(tmp_path / "nonexistent"), str(tmp_path / "agents"))
        types = reg.load_slot_types()
        assert types == {}


class TestLoadAgentCapabilities:
    def test_loads_all_agents(self, registry):
        agents = registry.load_agent_capabilities()
        assert len(agents) == 2
        assert "ENG-001" in agents
        assert "ARCH-001" in agents

    def test_agent_fields(self, registry):
        agents = registry.load_agent_capabilities()
        eng = agents["ENG-001"]
        assert eng.agent_id == "ENG-001"
        assert eng.version == "2.1"
        assert "python_development" in eng.capabilities
        assert "implementer" in eng.compatible_slot_types
        assert "02-engineer-agent.md" in eng.prompt_path

    def test_no_front_matter(self, tmp_path):
        """Agent .md without front-matter is skipped."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "no-fm.md").write_text("# No Front Matter\nJust text.")
        reg = SlotRegistry(str(tmp_path / "types"), str(agents_dir))
        agents = reg.load_agent_capabilities()
        assert len(agents) == 0

    def test_empty_dir(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        reg = SlotRegistry(str(tmp_path / "types"), str(agents_dir))
        agents = reg.load_agent_capabilities()
        assert agents == {}


class TestGetSlotType:
    def test_found(self, registry):
        registry.load_slot_types()
        st = registry.get_slot_type("implementer")
        assert st.id == "implementer"

    def test_not_found(self, registry):
        registry.load_slot_types()
        with pytest.raises(SlotTypeNotFoundError, match="nonexistent"):
            registry.get_slot_type("nonexistent")

    def test_auto_loads(self, registry):
        """get_slot_type auto-loads if not yet loaded."""
        st = registry.get_slot_type("implementer")
        assert st.id == "implementer"


class TestFindCompatibleAgents:
    def test_compatible_engineer(self, registry):
        registry.load_slot_types()
        registry.load_agent_capabilities()
        matches = registry.find_compatible_agents("implementer")
        compatible = [m for m in matches if m.is_compatible]
        assert len(compatible) == 1
        assert compatible[0].agent_id == "ENG-001"

    def test_incompatible_agent(self, registry):
        registry.load_slot_types()
        registry.load_agent_capabilities()
        matches = registry.find_compatible_agents("implementer")
        arch = next(m for m in matches if m.agent_id == "ARCH-001")
        assert arch.is_compatible is False
        assert len(arch.missing_capabilities) > 0

    def test_designer_match(self, registry):
        registry.load_slot_types()
        registry.load_agent_capabilities()
        matches = registry.find_compatible_agents("designer")
        compatible = [m for m in matches if m.is_compatible]
        assert len(compatible) == 1
        assert compatible[0].agent_id == "ARCH-001"

    def test_sorted_by_match_count(self, registry):
        registry.load_slot_types()
        registry.load_agent_capabilities()
        matches = registry.find_compatible_agents("implementer")
        # Should be sorted by matched count descending
        counts = [len(m.matched_capabilities) for m in matches]
        assert counts == sorted(counts, reverse=True)


class TestValidateAssignment:
    def test_valid_assignment(self, registry):
        registry.load_slot_types()
        registry.load_agent_capabilities()
        match = registry.validate_assignment("implementer", "ENG-001")
        assert match.is_compatible is True

    def test_invalid_assignment(self, registry):
        registry.load_slot_types()
        registry.load_agent_capabilities()
        match = registry.validate_assignment("implementer", "ARCH-001")
        assert match.is_compatible is False

    def test_unknown_agent(self, registry):
        registry.load_slot_types()
        registry.load_agent_capabilities()
        with pytest.raises(KeyError, match="UNKNOWN"):
            registry.validate_assignment("implementer", "UNKNOWN")

    def test_unknown_slot_type(self, registry):
        with pytest.raises(SlotTypeNotFoundError):
            registry.validate_assignment("nonexistent", "ENG-001")


class TestGenerateSlotManifest:
    def test_manifest_contents(self, registry, sample_pipeline):
        registry.load_slot_types()
        manifest = registry.generate_slot_manifest(sample_pipeline)
        assert isinstance(manifest, SlotManifest)
        assert manifest.pipeline_id == "test-pipeline"
        assert len(manifest.slots) == 2

    def test_manifest_capabilities(self, registry, sample_pipeline):
        registry.load_slot_types()
        manifest = registry.generate_slot_manifest(sample_pipeline)
        designer_slot = next(
            s for s in manifest.slots if s["slot_type"] == "designer"
        )
        assert "system_design" in designer_slot["required_capabilities"]

    def test_unknown_slot_type_empty_caps(self, registry):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[Slot(id="s", slot_type="unknown_type", name="S")],
        )
        registry.load_slot_types()
        manifest = registry.generate_slot_manifest(pipeline)
        assert manifest.slots[0]["required_capabilities"] == []
