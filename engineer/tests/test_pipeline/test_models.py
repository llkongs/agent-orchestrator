"""Tests for pipeline.models -- all enums, dataclasses, and state containers."""

import pytest
from dataclasses import FrozenInstanceError, asdict, fields

from src.pipeline.models import (
    AgentCapabilities,
    ArtifactOutput,
    ArtifactRef,
    ArtifactType,
    CapabilityMatch,
    ConditionType,
    DataFlowEdge,
    ExecutionConfig,
    Gate,
    GateCheckResult,
    Parameter,
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotAssignment,
    SlotState,
    SlotStatus,
    SlotTask,
    SlotTypeDefinition,
    ValidationLevel,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestSlotStatus:
    def test_all_values(self):
        expected = {
            "pending", "blocked", "ready", "pre_check",
            "in_progress", "post_check", "completed",
            "failed", "skipped", "retrying",
        }
        actual = {s.value for s in SlotStatus}
        assert actual == expected

    def test_string_representation(self):
        assert str(SlotStatus.PENDING) == "pending"
        assert str(SlotStatus.COMPLETED) == "completed"

    def test_is_str(self):
        assert isinstance(SlotStatus.PENDING, str)

    def test_member_count(self):
        assert len(SlotStatus) == 10


class TestPipelineStatus:
    def test_all_values(self):
        expected = {
            "loaded", "validated", "running", "paused",
            "completed", "failed", "aborted",
        }
        actual = {s.value for s in PipelineStatus}
        assert actual == expected

    def test_member_count(self):
        assert len(PipelineStatus) == 7


class TestArtifactType:
    def test_all_values(self):
        expected = {
            "design_doc", "code", "test_code", "delivery_yaml",
            "review_yaml", "config", "research", "audit_report",
            "agent_prompt", "approval", "deployment", "slot_output",
        }
        actual = {a.value for a in ArtifactType}
        assert actual == expected

    def test_member_count(self):
        assert len(ArtifactType) == 12


class TestConditionType:
    def test_all_values(self):
        expected = {
            "file_exists", "slot_completed", "approval",
            "artifact_valid", "delivery_valid", "review_valid",
            "tests_pass", "custom",
        }
        actual = {c.value for c in ConditionType}
        assert actual == expected

    def test_member_count(self):
        assert len(ConditionType) == 8


class TestValidationLevel:
    def test_all_values(self):
        expected = {"checksum", "schema", "exists", "none"}
        actual = {v.value for v in ValidationLevel}
        assert actual == expected

    def test_member_count(self):
        assert len(ValidationLevel) == 4


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------


class TestParameter:
    def test_creation_with_defaults(self):
        p = Parameter(name="feature", type="string", description="Feature name")
        assert p.name == "feature"
        assert p.type == "string"
        assert p.description == "Feature name"
        assert p.default is None
        assert p.required is False

    def test_creation_with_all_fields(self):
        p = Parameter(
            name="count", type="int", description="Count",
            default=5, required=True,
        )
        assert p.default == 5
        assert p.required is True

    def test_frozen_immutability(self):
        p = Parameter(name="x", type="string", description="desc")
        with pytest.raises(FrozenInstanceError):
            p.name = "y"


class TestArtifactRef:
    def test_creation_with_defaults(self):
        ref = ArtifactRef(name="design", from_slot="slot-design", artifact="design_doc")
        assert ref.name == "design"
        assert ref.from_slot == "slot-design"
        assert ref.artifact == "design_doc"
        assert ref.required is True

    def test_optional_not_required(self):
        ref = ArtifactRef(name="ctx", from_slot="external", artifact="context", required=False)
        assert ref.required is False

    def test_frozen_immutability(self):
        ref = ArtifactRef(name="x", from_slot="s", artifact="a")
        with pytest.raises(FrozenInstanceError):
            ref.name = "y"


class TestArtifactOutput:
    def test_creation_with_defaults(self):
        out = ArtifactOutput(name="source", type="code")
        assert out.name == "source"
        assert out.type == "code"
        assert out.path is None
        assert out.validation == "exists"

    def test_creation_with_all_fields(self):
        out = ArtifactOutput(
            name="delivery", type="delivery_yaml",
            path="engineer/DELIVERY.yaml", validation="checksum",
        )
        assert out.path == "engineer/DELIVERY.yaml"
        assert out.validation == "checksum"

    def test_frozen_immutability(self):
        out = ArtifactOutput(name="x", type="code")
        with pytest.raises(FrozenInstanceError):
            out.name = "y"


class TestGate:
    def test_creation(self):
        g = Gate(check="File exists", type="file_exists", target="engineer/src/main.py")
        assert g.check == "File exists"
        assert g.type == "file_exists"
        assert g.target == "engineer/src/main.py"

    def test_frozen_immutability(self):
        g = Gate(check="c", type="custom", target="t")
        with pytest.raises(FrozenInstanceError):
            g.check = "new"


class TestDataFlowEdge:
    def test_creation_with_defaults(self):
        e = DataFlowEdge(from_slot="a", to_slot="b", artifact="design_doc")
        assert e.from_slot == "a"
        assert e.to_slot == "b"
        assert e.artifact == "design_doc"
        assert e.required is True

    def test_optional_edge(self):
        e = DataFlowEdge(from_slot="a", to_slot="b", artifact="ctx", required=False)
        assert e.required is False

    def test_frozen_immutability(self):
        e = DataFlowEdge(from_slot="a", to_slot="b", artifact="x")
        with pytest.raises(FrozenInstanceError):
            e.from_slot = "c"


class TestGateCheckResult:
    def test_creation(self):
        r = GateCheckResult(
            condition="File exists",
            passed=True,
            evidence="File found at path/to/file",
            checked_at="2026-01-01T00:00:00Z",
        )
        assert r.condition == "File exists"
        assert r.passed is True
        assert r.evidence == "File found at path/to/file"
        assert r.checked_at == "2026-01-01T00:00:00Z"

    def test_frozen_immutability(self):
        r = GateCheckResult(condition="c", passed=True, evidence="e", checked_at="t")
        with pytest.raises(FrozenInstanceError):
            r.passed = False


# ---------------------------------------------------------------------------
# Mutable dataclass tests
# ---------------------------------------------------------------------------


class TestSlotTask:
    def test_creation_minimal(self):
        t = SlotTask(objective="Do the thing")
        assert t.objective == "Do the thing"
        assert t.context_files == []
        assert t.deliverables == []
        assert t.constraints == []
        assert t.kpis == []

    def test_creation_full(self):
        t = SlotTask(
            objective="Implement module",
            context_files=["arch.md"],
            deliverables=["src/mod.py"],
            constraints=["no external deps"],
            kpis=[">=95% coverage"],
        )
        assert len(t.context_files) == 1
        assert t.kpis[0] == ">=95% coverage"

    def test_mutable(self):
        t = SlotTask(objective="x")
        t.objective = "y"
        assert t.objective == "y"

    def test_default_factory_isolation(self):
        """Each instance gets its own list, not a shared reference."""
        t1 = SlotTask(objective="a")
        t2 = SlotTask(objective="b")
        t1.context_files.append("file.md")
        assert t2.context_files == []


class TestExecutionConfig:
    def test_defaults(self):
        ec = ExecutionConfig()
        assert ec.timeout_hours == 4.0
        assert ec.retry_on_fail is True
        assert ec.max_retries == 2
        assert ec.parallel_group is None

    def test_custom_values(self):
        ec = ExecutionConfig(
            timeout_hours=8.0, retry_on_fail=False,
            max_retries=0, parallel_group="parallel-1",
        )
        assert ec.timeout_hours == 8.0
        assert ec.parallel_group == "parallel-1"


class TestSlot:
    def test_creation_minimal(self):
        s = Slot(id="slot-a", slot_type="designer", name="Design")
        assert s.id == "slot-a"
        assert s.slot_type == "designer"
        assert s.name == "Design"
        assert s.inputs == []
        assert s.outputs == []
        assert s.pre_conditions == []
        assert s.post_conditions == []
        assert s.depends_on == []
        assert s.task is None
        assert isinstance(s.execution, ExecutionConfig)

    def test_creation_full(self):
        s = Slot(
            id="slot-impl",
            slot_type="implementer",
            name="Implement",
            inputs=[ArtifactRef(name="design", from_slot="slot-d", artifact="design_doc")],
            outputs=[ArtifactOutput(name="code", type="code")],
            pre_conditions=[Gate(check="Design done", type="slot_completed", target="slot-d")],
            post_conditions=[Gate(check="Tests pass", type="tests_pass", target="tests/")],
            depends_on=["slot-d"],
            task=SlotTask(objective="Write code"),
            execution=ExecutionConfig(timeout_hours=8.0),
        )
        assert len(s.inputs) == 1
        assert len(s.outputs) == 1
        assert len(s.pre_conditions) == 1
        assert s.depends_on == ["slot-d"]
        assert s.task.objective == "Write code"
        assert s.execution.timeout_hours == 8.0

    def test_default_factory_isolation(self):
        s1 = Slot(id="a", slot_type="x", name="A")
        s2 = Slot(id="b", slot_type="x", name="B")
        s1.depends_on.append("c")
        assert s2.depends_on == []


class TestPipeline:
    def test_creation_minimal(self):
        p = Pipeline(
            id="p1", name="P1", version="1.0.0",
            description="Test", created_by="user", created_at="2026-01-01",
        )
        assert p.id == "p1"
        assert p.parameters == []
        assert p.slots == []
        assert p.data_flow == []

    def test_creation_with_slots(self, sample_pipeline):
        assert sample_pipeline.id == "test-pipeline"
        assert len(sample_pipeline.slots) == 2
        assert len(sample_pipeline.data_flow) == 1
        assert sample_pipeline.data_flow[0].from_slot == "slot-design"


# ---------------------------------------------------------------------------
# State dataclass tests
# ---------------------------------------------------------------------------


class TestSlotState:
    def test_defaults(self):
        ss = SlotState(slot_id="slot-a")
        assert ss.slot_id == "slot-a"
        assert ss.status == SlotStatus.PENDING
        assert ss.started_at is None
        assert ss.completed_at is None
        assert ss.retry_count == 0
        assert ss.error is None
        assert ss.agent_id is None
        assert ss.agent_prompt is None
        assert ss.pre_check_results == []
        assert ss.post_check_results == []

    def test_mutable_status(self):
        ss = SlotState(slot_id="slot-a")
        ss.status = SlotStatus.IN_PROGRESS
        assert ss.status == SlotStatus.IN_PROGRESS

    def test_with_gate_results(self):
        r = GateCheckResult(
            condition="test", passed=True,
            evidence="ok", checked_at="2026-01-01T00:00:00Z",
        )
        ss = SlotState(slot_id="s", pre_check_results=[r])
        assert len(ss.pre_check_results) == 1
        assert ss.pre_check_results[0].passed is True


class TestPipelineState:
    def test_defaults(self):
        ps = PipelineState(
            pipeline_id="p", pipeline_version="1.0.0",
            definition_hash="sha256:abc",
        )
        assert ps.pipeline_id == "p"
        assert ps.status == PipelineStatus.LOADED
        assert ps.started_at is None
        assert ps.completed_at is None
        assert ps.parameters == {}
        assert ps.slots == {}

    def test_with_slot_states(self, sample_pipeline_state):
        assert "slot-design" in sample_pipeline_state.slots
        assert "slot-implement" in sample_pipeline_state.slots
        assert sample_pipeline_state.slots["slot-design"].status == SlotStatus.PENDING

    def test_dict_roundtrip(self):
        """PipelineState can be converted to dict and key structure is preserved."""
        ps = PipelineState(
            pipeline_id="p", pipeline_version="1.0.0",
            definition_hash="sha256:abc",
            parameters={"feature": "kline"},
            slots={"s1": SlotState(slot_id="s1")},
        )
        d = asdict(ps)
        assert d["pipeline_id"] == "p"
        assert d["parameters"]["feature"] == "kline"
        assert d["slots"]["s1"]["slot_id"] == "s1"
        assert d["slots"]["s1"]["status"] == "pending"


# ---------------------------------------------------------------------------
# Slot system dataclass tests
# ---------------------------------------------------------------------------


class TestSlotTypeDefinition:
    def test_creation_minimal(self):
        std = SlotTypeDefinition(
            id="implementer",
            name="Code Implementer",
            category="engineering",
            description="Writes code",
            input_schema={"type": "object", "required": ["design_doc"]},
            output_schema={"type": "object", "required": ["delivery_yaml"]},
            required_capabilities=["python_development", "test_writing"],
        )
        assert std.id == "implementer"
        assert std.constraints == []

    def test_with_constraints(self):
        std = SlotTypeDefinition(
            id="reviewer",
            name="Reviewer",
            category="quality",
            description="Reviews",
            input_schema={},
            output_schema={},
            required_capabilities=["code_review"],
            constraints=["Must not trust producer"],
        )
        assert len(std.constraints) == 1

    def test_frozen_immutability(self):
        std = SlotTypeDefinition(
            id="x", name="X", category="c", description="d",
            input_schema={}, output_schema={},
            required_capabilities=[],
        )
        with pytest.raises(FrozenInstanceError):
            std.id = "y"


class TestAgentCapabilities:
    def test_creation(self):
        ac = AgentCapabilities(
            agent_id="ENG-001",
            version="2.1",
            capabilities=["python_development", "test_writing", "delivery_protocol"],
            compatible_slot_types=["implementer"],
            prompt_path="agents/02-engineer-agent.md",
        )
        assert ac.agent_id == "ENG-001"
        assert "python_development" in ac.capabilities
        assert ac.prompt_path == "agents/02-engineer-agent.md"

    def test_frozen_immutability(self):
        ac = AgentCapabilities(
            agent_id="X", version="1.0", capabilities=[],
            compatible_slot_types=[], prompt_path="x.md",
        )
        with pytest.raises(FrozenInstanceError):
            ac.agent_id = "Y"


class TestCapabilityMatch:
    def test_compatible(self):
        cm = CapabilityMatch(
            agent_id="ENG-001",
            prompt_path="agents/02-engineer-agent.md",
            matched_capabilities=["python_development", "test_writing"],
            missing_capabilities=[],
            is_compatible=True,
        )
        assert cm.is_compatible is True
        assert cm.missing_capabilities == []

    def test_incompatible(self):
        cm = CapabilityMatch(
            agent_id="QA-001",
            prompt_path="agents/03-qa-agent.md",
            matched_capabilities=["code_review"],
            missing_capabilities=["python_development"],
            is_compatible=False,
        )
        assert cm.is_compatible is False
        assert "python_development" in cm.missing_capabilities


class TestSlotAssignment:
    def test_creation_minimal(self):
        sa = SlotAssignment(
            slot_id="slot-impl",
            slot_type="implementer",
            agent_id="ENG-001",
            agent_prompt="agents/02-engineer-agent.md",
        )
        assert sa.reason == ""

    def test_creation_with_reason(self):
        sa = SlotAssignment(
            slot_id="slot-impl",
            slot_type="implementer",
            agent_id="ENG-001",
            agent_prompt="agents/02-engineer-agent.md",
            reason="Primary engineer",
        )
        assert sa.reason == "Primary engineer"

    def test_mutable(self):
        sa = SlotAssignment(
            slot_id="s", slot_type="t",
            agent_id="A", agent_prompt="a.md",
        )
        sa.reason = "Updated reason"
        assert sa.reason == "Updated reason"
