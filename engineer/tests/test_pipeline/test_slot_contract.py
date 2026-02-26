"""Tests for pipeline.slot_contract -- Slot execution contracts."""

import pytest
import yaml

from src.pipeline.slot_contract import SlotContractManager, SlotInput, SlotOutputValidation
from src.pipeline.models import (
    ArtifactOutput,
    ArtifactRef,
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotState,
    SlotStatus,
    SlotTask,
)


@pytest.fixture
def contract_dir(tmp_path):
    d = tmp_path / "contracts"
    d.mkdir()
    return d


@pytest.fixture
def project_root(tmp_path):
    return tmp_path


@pytest.fixture
def simple_pipeline():
    return Pipeline(
        id="test", name="Test", version="1.0.0",
        description="T", created_by="t", created_at="t",
        slots=[
            Slot(
                id="slot-design",
                slot_type="designer",
                name="Design",
                task=SlotTask(
                    objective="Create design document",
                    context_files=["README.md"],
                    constraints=["Must follow standards"],
                    kpis=["design_completeness >= 90%"],
                ),
                outputs=[
                    ArtifactOutput(
                        name="design_doc", type="design_doc",
                        path="docs/design.md", validation="exists",
                    ),
                ],
            ),
            Slot(
                id="slot-implement",
                slot_type="implementer",
                name="Implement",
                depends_on=["slot-design"],
                task=SlotTask(objective="Write code"),
                inputs=[
                    ArtifactRef(
                        name="design_input",
                        from_slot="slot-design",
                        artifact="design_doc",
                    ),
                ],
                outputs=[
                    ArtifactOutput(
                        name="source_code", type="code",
                        path="src/module.py", validation="exists",
                    ),
                    ArtifactOutput(
                        name="delivery", type="delivery_yaml",
                        path="DELIVERY.yaml", validation="schema",
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def simple_state():
    return PipelineState(
        pipeline_id="test",
        pipeline_version="1.0.0",
        definition_hash="sha256:x",
        slots={
            "slot-design": SlotState(
                slot_id="slot-design", status=SlotStatus.COMPLETED,
            ),
            "slot-implement": SlotState(
                slot_id="slot-implement", status=SlotStatus.PENDING,
            ),
        },
    )


class TestGenerateSlotInput:
    def test_basic_generation(self, project_root, contract_dir, simple_pipeline, simple_state):
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        slot = simple_pipeline.slots[0]
        result = mgr.generate_slot_input(slot, simple_pipeline, simple_state)
        assert isinstance(result, SlotInput)
        assert result.slot_id == "slot-design"
        assert result.slot_type == "designer"
        assert result.task_objective == "Create design document"
        assert "README.md" in result.context_files
        assert "Must follow standards" in result.constraints
        assert len(result.kpis) == 1

    def test_input_artifacts_from_upstream(self, project_root, contract_dir, simple_pipeline, simple_state):
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        slot = simple_pipeline.slots[1]  # slot-implement
        result = mgr.generate_slot_input(slot, simple_pipeline, simple_state)
        assert "design_input" in result.input_artifacts

    def test_required_outputs_listed(self, project_root, contract_dir, simple_pipeline, simple_state):
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        slot = simple_pipeline.slots[1]
        result = mgr.generate_slot_input(slot, simple_pipeline, simple_state)
        assert len(result.required_outputs) == 2
        names = [o["name"] for o in result.required_outputs]
        assert "source_code" in names
        assert "delivery" in names

    def test_no_task(self, project_root, contract_dir, simple_state):
        pipeline = Pipeline(
            id="t", name="T", version="1.0.0",
            description="T", created_by="t", created_at="t",
            slots=[Slot(id="s", slot_type="x", name="S")],
        )
        state = PipelineState(
            pipeline_id="t", pipeline_version="1.0.0",
            definition_hash="sha256:x",
            slots={"s": SlotState(slot_id="s")},
        )
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.generate_slot_input(pipeline.slots[0], pipeline, state)
        assert result.task_objective == ""
        assert result.context_files == []

    def test_generated_at_set(self, project_root, contract_dir, simple_pipeline, simple_state):
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.generate_slot_input(simple_pipeline.slots[0], simple_pipeline, simple_state)
        assert result.generated_at is not None


class TestWriteSlotInput:
    def test_writes_yaml_file(self, project_root, contract_dir, simple_pipeline, simple_state):
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        slot_input = mgr.generate_slot_input(simple_pipeline.slots[0], simple_pipeline, simple_state)
        path = mgr.write_slot_input(slot_input)
        assert "slot-design-input.yaml" in path
        data = yaml.safe_load(open(path, encoding="utf-8"))
        assert data["slot_id"] == "slot-design"
        assert data["task_objective"] == "Create design document"

    def test_creates_contracts_dir(self, project_root, tmp_path, simple_pipeline, simple_state):
        new_dir = tmp_path / "new_contracts"
        mgr = SlotContractManager(str(project_root), str(new_dir))
        slot_input = mgr.generate_slot_input(simple_pipeline.slots[0], simple_pipeline, simple_state)
        path = mgr.write_slot_input(slot_input)
        assert new_dir.exists()


class TestValidateSlotOutput:
    def test_all_outputs_present(self, project_root, contract_dir, simple_pipeline):
        # Create the output files
        (project_root / "docs").mkdir(parents=True)
        (project_root / "docs" / "design.md").write_text("# Design")
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.validate_slot_output(simple_pipeline.slots[0])
        assert result.valid is True
        assert result.missing_outputs == []

    def test_missing_output(self, project_root, contract_dir, simple_pipeline):
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.validate_slot_output(simple_pipeline.slots[0])
        assert result.valid is False
        assert "design_doc" in result.missing_outputs

    def test_invalid_yaml_output(self, project_root, contract_dir, simple_pipeline):
        # Create source_code but invalid DELIVERY.yaml
        (project_root / "src").mkdir(parents=True)
        (project_root / "src" / "module.py").write_text("x = 1")
        (project_root / "DELIVERY.yaml").write_text("::invalid yaml: {[")
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.validate_slot_output(simple_pipeline.slots[1])
        assert result.valid is False
        assert "delivery" in result.invalid_outputs

    def test_no_outputs_is_valid(self, project_root, contract_dir):
        slot = Slot(id="s", slot_type="x", name="S")
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.validate_slot_output(slot)
        assert result.valid is True

    def test_validated_at_set(self, project_root, contract_dir, simple_pipeline):
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.validate_slot_output(simple_pipeline.slots[0])
        assert result.validated_at is not None

    def test_output_without_path_skipped(self, project_root, contract_dir):
        slot = Slot(
            id="s", slot_type="x", name="S",
            outputs=[ArtifactOutput(name="approval", type="approval")],
        )
        mgr = SlotContractManager(str(project_root), str(contract_dir))
        result = mgr.validate_slot_output(slot)
        assert result.valid is True
        assert result.missing_outputs == []
