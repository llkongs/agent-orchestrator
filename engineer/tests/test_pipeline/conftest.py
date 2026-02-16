"""Shared pytest fixtures for pipeline tests."""

import pytest

from src.pipeline.models import (
    ArtifactOutput,
    ArtifactRef,
    DataFlowEdge,
    ExecutionConfig,
    Gate,
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotAssignment,
    SlotState,
    SlotStatus,
    SlotTask,
    SlotTypeDefinition,
)


@pytest.fixture
def sample_slot_task():
    """Minimal SlotTask for unit tests."""
    return SlotTask(objective="Do work")


@pytest.fixture
def sample_slot(sample_slot_task):
    """Minimal Slot with defaults for unit tests."""
    return Slot(
        id="slot-a",
        slot_type="implementer",
        name="Slot A",
        task=sample_slot_task,
    )


@pytest.fixture
def sample_pipeline():
    """Minimal valid Pipeline for unit tests."""
    return Pipeline(
        id="test-pipeline",
        name="Test Pipeline",
        version="1.0.0",
        description="A test pipeline",
        created_by="test",
        created_at="2026-01-01T00:00:00Z",
        slots=[
            Slot(
                id="slot-design",
                slot_type="designer",
                name="Design",
                task=SlotTask(objective="Create design"),
                outputs=[ArtifactOutput(name="design_doc", type="design_doc")],
            ),
            Slot(
                id="slot-implement",
                slot_type="implementer",
                name="Implement",
                depends_on=["slot-design"],
                task=SlotTask(objective="Write code"),
            ),
        ],
        data_flow=[
            DataFlowEdge(
                from_slot="slot-design",
                to_slot="slot-implement",
                artifact="design_doc",
            ),
        ],
    )


@pytest.fixture
def sample_pipeline_state():
    """Minimal PipelineState for unit tests."""
    return PipelineState(
        pipeline_id="test-pipeline",
        pipeline_version="1.0.0",
        definition_hash="sha256:abc123",
        slots={
            "slot-design": SlotState(slot_id="slot-design"),
            "slot-implement": SlotState(slot_id="slot-implement"),
        },
    )


@pytest.fixture
def project_root(tmp_path):
    """Create a minimal project structure for testing."""
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "pipelines" / "slot-types").mkdir(parents=True)
    (tmp_path / "specs" / "pipelines" / "templates").mkdir(parents=True)
    (tmp_path / "agents").mkdir()
    (tmp_path / "engineer" / "src").mkdir(parents=True)
    (tmp_path / "engineer" / "tests").mkdir(parents=True)
    (tmp_path / "state" / "active").mkdir(parents=True)
    (tmp_path / "state" / "archive").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def state_dir(tmp_path):
    """Temp directory for state files."""
    d = tmp_path / "active"
    d.mkdir()
    (tmp_path / "archive").mkdir()
    return d
