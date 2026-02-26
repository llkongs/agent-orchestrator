"""Tests for pipeline.auto_executor -- Automated pipeline execution engine."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest
import yaml

from pipeline.auto_executor import (
    AgentExecutor,
    AgentResult,
    AutoExecutor,
    AutoExecutorConfig,
    CallbackExecutor,
    SubprocessExecutor,
    _SlotTask,
)
from pipeline.models import (
    ExecutionConfig,
    Pipeline,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotAssignment,
    SlotState,
    SlotStatus,
    SlotTask,
)
from pipeline.runner import PipelineExecutionError, PipelineRunner
from pipeline.slot_contract import SlotContractManager, SlotInput, SlotOutputValidation
from pipeline.slot_registry import SlotRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dirs(tmp_path):
    """Create directory structure for auto_executor tests."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "state" / "active").mkdir(parents=True)
    (tmp_path / "slot-types").mkdir()
    (tmp_path / "agents").mkdir()
    (tmp_path / "contracts").mkdir()

    # Slot types
    (tmp_path / "slot-types" / "implementer.yaml").write_text(
        yaml.dump({
            "slot_type": {
                "id": "implementer",
                "name": "Code Implementer",
                "category": "engineering",
                "description": "Writes code",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "required_capabilities": ["python"],
            }
        })
    )
    (tmp_path / "slot-types" / "designer.yaml").write_text(
        yaml.dump({
            "slot_type": {
                "id": "designer",
                "name": "Designer",
                "category": "architecture",
                "description": "Designs",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "required_capabilities": ["design"],
            }
        })
    )

    # Agents
    (tmp_path / "agents" / "eng.md").write_text(
        "---\n"
        "agent_id: ENG-001\n"
        "version: '1.0'\n"
        "capabilities:\n"
        "  - python\n"
        "compatible_slot_types:\n"
        "  - implementer\n"
        "---\n"
        "# Engineer\n"
    )
    (tmp_path / "agents" / "arch.md").write_text(
        "---\n"
        "agent_id: ARCH-001\n"
        "version: '1.0'\n"
        "capabilities:\n"
        "  - design\n"
        "compatible_slot_types:\n"
        "  - designer\n"
        "---\n"
        "# Architect\n"
    )

    return tmp_path


@pytest.fixture
def runner(project_dirs):
    """Create a PipelineRunner."""
    return PipelineRunner(
        project_root=str(project_dirs),
        templates_dir=str(project_dirs / "templates"),
        state_dir=str(project_dirs / "state" / "active"),
        slot_types_dir=str(project_dirs / "slot-types"),
        agents_dir=str(project_dirs / "agents"),
    )


@pytest.fixture
def contract_manager(project_dirs):
    """Create a SlotContractManager."""
    return SlotContractManager(
        str(project_dirs),
        str(project_dirs / "contracts"),
    )


@pytest.fixture
def registry(project_dirs):
    """Create a SlotRegistry."""
    return SlotRegistry(
        str(project_dirs / "slot-types"),
        str(project_dirs / "agents"),
    )


def _make_slot(
    slot_id: str,
    slot_type: str = "implementer",
    depends_on: list[str] | None = None,
    parallel_group: str | None = None,
    retry_on_fail: bool = True,
    max_retries: int = 2,
) -> Slot:
    """Helper to create a Slot."""
    return Slot(
        id=slot_id,
        slot_type=slot_type,
        name=f"Slot {slot_id}",
        task=SlotTask(objective=f"Do {slot_id}"),
        depends_on=depends_on or [],
        execution=ExecutionConfig(
            parallel_group=parallel_group,
            retry_on_fail=retry_on_fail,
            max_retries=max_retries,
        ),
    )


def _make_pipeline(slots: list[Slot], pipeline_id: str = "test-pipe") -> Pipeline:
    """Helper to create a Pipeline."""
    return Pipeline(
        id=pipeline_id,
        name="Test Pipeline",
        version="1.0.0",
        description="Test",
        created_by="test",
        created_at="2026-01-01T00:00:00Z",
        slots=slots,
    )


def _make_state(
    pipeline: Pipeline,
    status: PipelineStatus = PipelineStatus.VALIDATED,
) -> PipelineState:
    """Helper to create a PipelineState."""
    slots = {}
    for slot in pipeline.slots:
        slots[slot.id] = SlotState(slot_id=slot.id, status=SlotStatus.PENDING)
    return PipelineState(
        pipeline_id=pipeline.id,
        pipeline_version=pipeline.version,
        definition_hash="abc123",
        status=status,
        slots=slots,
    )


def _make_slot_input(slot_id: str = "slot-a") -> SlotInput:
    """Helper to create a SlotInput."""
    return SlotInput(
        slot_id=slot_id,
        slot_type="implementer",
        task_objective="Do work",
        context_files=[],
        constraints=[],
        input_artifacts={},
        required_outputs=[],
        kpis=[],
        generated_at="2026-01-01T00:00:00Z",
    )


# ===========================================================================
# TestAgentResult
# ===========================================================================


class TestAgentResult:
    """Tests for AgentResult frozen dataclass."""

    def test_creation(self):
        r = AgentResult(
            slot_id="s1", agent_id="a1", success=True,
            exit_code=0, stdout="ok", stderr="",
            duration_seconds=1.5,
        )
        assert r.slot_id == "s1"
        assert r.success is True
        assert r.exit_code == 0

    def test_frozen(self):
        r = AgentResult(
            slot_id="s1", agent_id="a1", success=True,
            exit_code=0, stdout="", stderr="",
            duration_seconds=0.0,
        )
        with pytest.raises(AttributeError):
            r.success = False  # type: ignore[misc]

    def test_fields(self):
        r = AgentResult(
            slot_id="x", agent_id="y", success=False,
            exit_code=42, stdout="out", stderr="err",
            duration_seconds=3.14,
        )
        assert r.agent_id == "y"
        assert r.exit_code == 42
        assert r.stdout == "out"
        assert r.stderr == "err"
        assert r.duration_seconds == pytest.approx(3.14)


# ===========================================================================
# TestAutoExecutorConfig
# ===========================================================================


class TestAutoExecutorConfig:
    """Tests for AutoExecutorConfig."""

    def test_defaults(self):
        cfg = AutoExecutorConfig()
        assert cfg.max_parallel == 4
        assert cfg.timeout_default_hours == 4.0
        assert cfg.dry_run is False

    def test_custom(self):
        cfg = AutoExecutorConfig(max_parallel=8, dry_run=True)
        assert cfg.max_parallel == 8
        assert cfg.dry_run is True


# ===========================================================================
# TestCallbackExecutor
# ===========================================================================


class TestCallbackExecutor:
    """Tests for CallbackExecutor."""

    def test_success(self):
        executor = CallbackExecutor(lambda si, aid: True)
        slot_input = _make_slot_input()
        result = executor.execute(slot_input, "prompt.md", "ENG-001")
        assert result.success is True
        assert result.exit_code == 0
        assert result.slot_id == "slot-a"
        assert result.agent_id == "ENG-001"
        assert result.duration_seconds >= 0

    def test_failure(self):
        executor = CallbackExecutor(lambda si, aid: False)
        result = executor.execute(_make_slot_input(), "p.md", "ENG-001")
        assert result.success is False
        assert result.exit_code == 1

    def test_exception_caught(self):
        def boom(si, aid):
            raise RuntimeError("kaboom")

        executor = CallbackExecutor(boom)
        result = executor.execute(_make_slot_input(), "p.md", "ENG-001")
        assert result.success is False
        assert "kaboom" in result.stderr

    def test_stdout_fn(self):
        executor = CallbackExecutor(
            lambda si, aid: True,
            stdout_fn=lambda si, aid: f"stdout-{aid}",
        )
        result = executor.execute(_make_slot_input(), "p.md", "A1")
        assert result.stdout == "stdout-A1"

    def test_stderr_fn(self):
        executor = CallbackExecutor(
            lambda si, aid: True,
            stderr_fn=lambda si, aid: f"stderr-{si.slot_id}",
        )
        result = executor.execute(_make_slot_input("slot-x"), "p.md", "A1")
        assert result.stderr == "stderr-slot-x"

    def test_timing(self):
        import time

        def slow_callback(si, aid):
            time.sleep(0.05)
            return True

        executor = CallbackExecutor(slow_callback)
        result = executor.execute(_make_slot_input(), "p.md", "A1")
        assert result.duration_seconds >= 0.04


# ===========================================================================
# TestSubprocessExecutor
# ===========================================================================


class TestSubprocessExecutor:
    """Tests for SubprocessExecutor."""

    def test_success(self, tmp_path):
        executor = SubprocessExecutor(
            "echo hello", str(tmp_path / "contracts")
        )
        slot_input = _make_slot_input()
        with patch.object(SlotContractManager, "write_slot_input", return_value="/tmp/input.yaml"):
            result = executor.execute(slot_input, "p.md", "ENG-001", project_root=str(tmp_path))
        assert result.success is True
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_failure(self, tmp_path):
        executor = SubprocessExecutor(
            "false", str(tmp_path / "contracts")
        )
        slot_input = _make_slot_input()
        with patch.object(SlotContractManager, "write_slot_input", return_value="/tmp/input.yaml"):
            result = executor.execute(slot_input, "p.md", "ENG-001", project_root=str(tmp_path))
        assert result.success is False
        assert result.exit_code != 0

    def test_timeout(self, tmp_path):
        executor = SubprocessExecutor(
            "sleep 10", str(tmp_path / "contracts")
        )
        slot_input = _make_slot_input()
        with patch.object(SlotContractManager, "write_slot_input", return_value="/tmp/input.yaml"):
            result = executor.execute(
                slot_input, "p.md", "ENG-001",
                timeout_seconds=0.1,
                project_root=str(tmp_path),
            )
        assert result.success is False
        assert result.exit_code == -1
        assert "timed out" in result.stderr

    def test_command_not_found(self, tmp_path):
        executor = SubprocessExecutor(
            "nonexistent_command_xyz_12345", str(tmp_path / "contracts")
        )
        slot_input = _make_slot_input()
        with patch.object(SlotContractManager, "write_slot_input", return_value="/tmp/input.yaml"):
            result = executor.execute(
                slot_input, "p.md", "ENG-001",
                project_root=str(tmp_path),
            )
        assert result.success is False
        assert result.exit_code == -2
        assert "error" in result.stderr.lower()

    def test_no_shell_true(self, tmp_path):
        """Verify we never use shell=True (Constitution §6.1)."""
        executor = SubprocessExecutor(
            "echo test", str(tmp_path / "contracts")
        )
        slot_input = _make_slot_input()
        with patch.object(SlotContractManager, "write_slot_input", return_value="/tmp/input.yaml"):
            with patch("pipeline.auto_executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="", stderr=""
                )
                executor.execute(
                    slot_input, "p.md", "ENG-001",
                    project_root=str(tmp_path),
                )
                # Verify shell is not in kwargs or is False
                call_kwargs = mock_run.call_args
                assert call_kwargs.kwargs.get("shell", False) is False


# ===========================================================================
# TestAutoExecutorRun
# ===========================================================================


class TestAutoExecutorRun:
    """Tests for AutoExecutor.run() -- the main execution loop."""

    def test_single_slot_sequential(self, runner, contract_manager, registry, project_dirs):
        """Single slot pipeline completes successfully."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.COMPLETED

    def test_two_slots_sequential(self, runner, contract_manager, registry, project_dirs):
        """Two-slot chain: A -> B."""
        slot_a = _make_slot("slot-a")
        slot_b = _make_slot("slot-b", depends_on=["slot-a"])
        pipeline = _make_pipeline([slot_a, slot_b])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.COMPLETED
        assert final.slots["slot-b"].status == SlotStatus.COMPLETED

    def test_parallel_slots(self, runner, contract_manager, registry, project_dirs):
        """Slots in same parallel_group execute concurrently."""
        slot_a = _make_slot("slot-a", parallel_group="group1")
        slot_b = _make_slot("slot-b", parallel_group="group1")
        pipeline = _make_pipeline([slot_a, slot_b])
        state = _make_state(pipeline)

        executed_ids = []

        def track_callback(si, aid):
            executed_ids.append(si.slot_id)
            return True

        executor = CallbackExecutor(track_callback)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.COMPLETED
        assert final.slots["slot-b"].status == SlotStatus.COMPLETED
        assert set(executed_ids) == {"slot-a", "slot-b"}

    def test_diamond_dependency(self, runner, contract_manager, registry, project_dirs):
        """Diamond: A -> B,C -> D."""
        slot_a = _make_slot("slot-a")
        slot_b = _make_slot("slot-b", depends_on=["slot-a"])
        slot_c = _make_slot("slot-c", depends_on=["slot-a"])
        slot_d = _make_slot("slot-d", depends_on=["slot-b", "slot-c"])
        pipeline = _make_pipeline([slot_a, slot_b, slot_c, slot_d])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        for sid in ["slot-a", "slot-b", "slot-c", "slot-d"]:
            assert final.slots[sid].status == SlotStatus.COMPLETED

    def test_failed_slot_stops_dependents(self, runner, contract_manager, registry, project_dirs):
        """If A fails, B (depends on A) never executes."""
        slot_a = _make_slot("slot-a", retry_on_fail=False)
        slot_b = _make_slot("slot-b", depends_on=["slot-a"])
        pipeline = _make_pipeline([slot_a, slot_b])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: False)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.FAILED
        assert final.slots["slot-b"].status == SlotStatus.PENDING

    def test_empty_pipeline(self, runner, contract_manager, registry, project_dirs):
        """Empty pipeline completes immediately."""
        pipeline = _make_pipeline([])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert len(final.slots) == 0

    def test_mixed_parallel_and_sequential(self, runner, contract_manager, registry, project_dirs):
        """Mix of parallel and sequential slots."""
        slot_a = _make_slot("slot-a")  # sequential
        slot_b = _make_slot("slot-b", depends_on=["slot-a"], parallel_group="p1")
        slot_c = _make_slot("slot-c", depends_on=["slot-a"], parallel_group="p1")
        slot_d = _make_slot("slot-d", depends_on=["slot-b", "slot-c"])
        pipeline = _make_pipeline([slot_a, slot_b, slot_c, slot_d])
        state = _make_state(pipeline)

        execution_order = []

        def ordered_callback(si, aid):
            execution_order.append(si.slot_id)
            return True

        executor = CallbackExecutor(ordered_callback)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        # A must be first, D must be last
        assert execution_order[0] == "slot-a"
        assert execution_order[-1] == "slot-d"
        for sid in ["slot-a", "slot-b", "slot-c", "slot-d"]:
            assert final.slots[sid].status == SlotStatus.COMPLETED

    def test_all_slots_completed_pipeline_complete(self, runner, contract_manager, registry, project_dirs):
        """Pipeline transitions to COMPLETED when all slots complete."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.status == PipelineStatus.COMPLETED

    def test_max_parallel_respected(self, runner, contract_manager, registry, project_dirs):
        """max_parallel limits concurrent execution."""
        slots = [_make_slot(f"slot-{i}", parallel_group="all") for i in range(6)]
        pipeline = _make_pipeline(slots)
        state = _make_state(pipeline)

        concurrent_count = []
        lock = threading.Lock()
        active = [0]

        def counting_callback(si, aid):
            import time
            with lock:
                active[0] += 1
                concurrent_count.append(active[0])
            time.sleep(0.02)
            with lock:
                active[0] -= 1
            return True

        executor = CallbackExecutor(counting_callback)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            config=AutoExecutorConfig(max_parallel=2),
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert max(concurrent_count) <= 2
        for s in slots:
            assert final.slots[s.id].status == SlotStatus.COMPLETED

    def test_three_sequential_slots(self, runner, contract_manager, registry, project_dirs):
        """Three sequential slots A -> B -> C."""
        slot_a = _make_slot("slot-a")
        slot_b = _make_slot("slot-b", depends_on=["slot-a"])
        slot_c = _make_slot("slot-c", depends_on=["slot-b"])
        pipeline = _make_pipeline([slot_a, slot_b, slot_c])
        state = _make_state(pipeline)

        order = []

        def track(si, aid):
            order.append(si.slot_id)
            return True

        executor = CallbackExecutor(track)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert order == ["slot-a", "slot-b", "slot-c"]
        for sid in order:
            assert final.slots[sid].status == SlotStatus.COMPLETED

    def test_run_with_explicit_assignments(self, runner, contract_manager, registry, project_dirs):
        """Explicit assignments override auto-match."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        assignments = [
            SlotAssignment(
                slot_id="slot-a",
                slot_type="implementer",
                agent_id="CUSTOM-001",
                agent_prompt="custom-agent.md",
            )
        ]

        received_agents = []

        def check_agent(si, aid):
            received_agents.append(aid)
            return True

        executor = CallbackExecutor(check_agent)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            assignments=assignments,
            project_root=str(project_dirs),
        )
        auto.run(pipeline, state)
        assert received_agents == ["CUSTOM-001"]

    def test_single_task_no_threadpool(self, runner, contract_manager, registry, project_dirs):
        """Single task is executed directly without ThreadPoolExecutor."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )

        with patch("pipeline.auto_executor.ThreadPoolExecutor") as mock_pool:
            auto.run(pipeline, state)
            mock_pool.assert_not_called()


# ===========================================================================
# TestAgentResolution
# ===========================================================================


class TestAgentResolution:
    """Tests for agent resolution logic."""

    def test_explicit_assignment(self, runner, contract_manager, registry, project_dirs):
        """Explicit assignment takes priority."""
        slot = _make_slot("slot-a")
        assignments = [
            SlotAssignment(
                slot_id="slot-a",
                slot_type="implementer",
                agent_id="MY-AGENT",
                agent_prompt="my-agent.md",
            )
        ]
        auto = AutoExecutor(
            runner, CallbackExecutor(lambda si, aid: True),
            contract_manager, registry,
            assignments=assignments,
        )
        agent_id, prompt = auto._resolve_agent(slot)
        assert agent_id == "MY-AGENT"
        assert prompt == "my-agent.md"

    def test_auto_match(self, runner, contract_manager, registry, project_dirs):
        """Auto-match finds compatible agent from registry."""
        slot = _make_slot("slot-a", slot_type="implementer")
        auto = AutoExecutor(
            runner, CallbackExecutor(lambda si, aid: True),
            contract_manager, registry,
        )
        agent_id, prompt = auto._resolve_agent(slot)
        assert agent_id == "ENG-001"
        assert prompt is not None

    def test_auto_match_designer(self, runner, contract_manager, registry, project_dirs):
        """Auto-match finds designer agent."""
        slot = _make_slot("slot-a", slot_type="designer")
        auto = AutoExecutor(
            runner, CallbackExecutor(lambda si, aid: True),
            contract_manager, registry,
        )
        agent_id, prompt = auto._resolve_agent(slot)
        assert agent_id == "ARCH-001"

    def test_no_match_graceful(self, runner, contract_manager, project_dirs):
        """No matching agent returns (None, None)."""
        empty_registry = SlotRegistry(
            str(project_dirs / "slot-types"),
            str(project_dirs / "empty-agents"),
        )
        (project_dirs / "empty-agents").mkdir()

        # Use a slot type that exists but has no matching agent
        slot = _make_slot("slot-a", slot_type="implementer")
        auto = AutoExecutor(
            runner, CallbackExecutor(lambda si, aid: True),
            contract_manager, empty_registry,
        )
        agent_id, prompt = auto._resolve_agent(slot)
        # No compatible agents (empty dir) -> (None, None)
        assert agent_id is None
        assert prompt is None

    def test_explicit_overrides_auto(self, runner, contract_manager, registry, project_dirs):
        """Explicit assignment overrides auto-match even when auto would find one."""
        slot = _make_slot("slot-a", slot_type="implementer")
        assignments = [
            SlotAssignment(
                slot_id="slot-a",
                slot_type="implementer",
                agent_id="OVERRIDE-001",
                agent_prompt="override.md",
            )
        ]
        auto = AutoExecutor(
            runner, CallbackExecutor(lambda si, aid: True),
            contract_manager, registry,
            assignments=assignments,
        )
        agent_id, prompt = auto._resolve_agent(slot)
        assert agent_id == "OVERRIDE-001"

    def test_registry_error_graceful(self, runner, contract_manager, project_dirs):
        """Registry error falls through to (None, None)."""
        mock_registry = MagicMock(spec=SlotRegistry)
        mock_registry.find_compatible_agents.side_effect = RuntimeError("broken")

        slot = _make_slot("slot-a", slot_type="unknown-type")
        auto = AutoExecutor(
            runner, CallbackExecutor(lambda si, aid: True),
            contract_manager, mock_registry,
        )
        agent_id, prompt = auto._resolve_agent(slot)
        assert agent_id is None
        assert prompt is None


# ===========================================================================
# TestRetry
# ===========================================================================


class TestRetry:
    """Tests for retry logic."""

    def test_retry_success(self, runner, contract_manager, registry, project_dirs):
        """Slot fails once, succeeds on retry."""
        slot = _make_slot("slot-a", max_retries=2)
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        call_count = [0]

        def fail_then_succeed(si, aid):
            call_count[0] += 1
            return call_count[0] > 1

        executor = CallbackExecutor(fail_then_succeed)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.COMPLETED
        assert call_count[0] == 2

    def test_retry_exhausted(self, runner, contract_manager, registry, project_dirs):
        """Slot fails all retries and remains FAILED."""
        slot = _make_slot("slot-a", max_retries=1)
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: False)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.FAILED

    def test_retry_disabled(self, runner, contract_manager, registry, project_dirs):
        """retry_on_fail=False skips retries."""
        slot = _make_slot("slot-a", retry_on_fail=False)
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        call_count = [0]

        def always_fail(si, aid):
            call_count[0] += 1
            return False

        executor = CallbackExecutor(always_fail)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.FAILED
        assert call_count[0] == 1  # No retries

    def test_retry_count_incremented(self, runner, contract_manager, registry, project_dirs):
        """Retry count is incremented on each retry."""
        slot = _make_slot("slot-a", max_retries=2)
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        call_count = [0]

        def fail_twice(si, aid):
            call_count[0] += 1
            return call_count[0] > 2

        executor = CallbackExecutor(fail_twice)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.COMPLETED
        assert final.slots["slot-a"].retry_count == 2

    def test_max_retries_zero(self, runner, contract_manager, registry, project_dirs):
        """max_retries=0 means no retries."""
        slot = _make_slot("slot-a", max_retries=0)
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        call_count = [0]

        def always_fail(si, aid):
            call_count[0] += 1
            return False

        executor = CallbackExecutor(always_fail)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.FAILED
        assert call_count[0] == 1


# ===========================================================================
# TestOutputValidation
# ===========================================================================


class TestOutputValidation:
    """Tests for output validation in finalization."""

    def test_missing_output_fails_slot(self, runner, contract_manager, registry, project_dirs):
        """Missing required output file fails the slot."""
        from pipeline.models import ArtifactOutput
        slot = Slot(
            id="slot-a",
            slot_type="implementer",
            name="Slot A",
            task=SlotTask(objective="Do A"),
            outputs=[
                ArtifactOutput(
                    name="result",
                    type="code",
                    path="nonexistent/file.py",
                )
            ],
            execution=ExecutionConfig(retry_on_fail=False),
        )
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.FAILED
        assert "missing" in (final.slots["slot-a"].error or "").lower()

    def test_invalid_output_fails_slot(self, runner, contract_manager, registry, project_dirs):
        """Invalid output (bad YAML schema) fails the slot."""
        from pipeline.models import ArtifactOutput

        # Create a file with invalid YAML for schema validation
        bad_file = project_dirs / "bad-output.yaml"
        bad_file.write_text("invalid: yaml: [broken", encoding="utf-8")

        slot = Slot(
            id="slot-a",
            slot_type="implementer",
            name="Slot A",
            task=SlotTask(objective="Do A"),
            outputs=[
                ArtifactOutput(
                    name="result",
                    type="config",
                    path="bad-output.yaml",
                    validation="schema",
                )
            ],
            execution=ExecutionConfig(retry_on_fail=False),
        )
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.FAILED

    def test_valid_output_completes(self, runner, contract_manager, registry, project_dirs):
        """Valid output passes and slot completes."""
        from pipeline.models import ArtifactOutput

        # Create a valid output file
        good_file = project_dirs / "output.yaml"
        good_file.write_text("key: value\n", encoding="utf-8")

        slot = Slot(
            id="slot-a",
            slot_type="implementer",
            name="Slot A",
            task=SlotTask(objective="Do A"),
            outputs=[
                ArtifactOutput(
                    name="result",
                    type="config",
                    path="output.yaml",
                    validation="schema",
                )
            ],
        )
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.COMPLETED


# ===========================================================================
# TestDryRun
# ===========================================================================


class TestDryRun:
    """Tests for dry run mode."""

    def test_contracts_generated(self, runner, contract_manager, registry, project_dirs):
        """Dry run generates contracts to disk."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            config=AutoExecutorConfig(dry_run=True),
            project_root=str(project_dirs),
        )
        auto.run(pipeline, state)

        # Check contract was written
        contract_file = project_dirs / "contracts" / "slot-a-input.yaml"
        assert contract_file.exists()

    def test_no_execution(self, runner, contract_manager, registry, project_dirs):
        """Dry run does not execute agents."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        call_count = [0]

        def should_not_be_called(si, aid):
            call_count[0] += 1
            return True

        executor = CallbackExecutor(should_not_be_called)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            config=AutoExecutorConfig(dry_run=True),
            project_root=str(project_dirs),
        )
        auto.run(pipeline, state)
        assert call_count[0] == 0

    def test_slots_skipped(self, runner, contract_manager, registry, project_dirs):
        """Dry run marks slots as SKIPPED."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            config=AutoExecutorConfig(dry_run=True),
            project_root=str(project_dirs),
        )
        final = auto.run(pipeline, state)
        assert final.slots["slot-a"].status == SlotStatus.SKIPPED


# ===========================================================================
# TestRunSingleSlot
# ===========================================================================


class TestRunSingleSlot:
    """Tests for run_single_slot()."""

    def test_success(self, runner, contract_manager, registry, project_dirs):
        """Single slot executes and returns result."""
        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final_state, result = auto.run_single_slot(slot, pipeline, state)
        assert result is not None
        assert result.success is True
        assert final_state.slots["slot-a"].status == SlotStatus.COMPLETED

    def test_failure(self, runner, contract_manager, registry, project_dirs):
        """Failed single slot returns failed result."""
        slot = _make_slot("slot-a", retry_on_fail=False)
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: False)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final_state, result = auto.run_single_slot(slot, pipeline, state)
        assert result is not None
        assert result.success is False
        assert final_state.slots["slot-a"].status == SlotStatus.FAILED

    def test_precondition_fail_returns_none(self, runner, contract_manager, registry, project_dirs):
        """Pre-condition failure returns None result."""
        from pipeline.models import Gate
        slot = Slot(
            id="slot-a",
            slot_type="implementer",
            name="Slot A",
            task=SlotTask(objective="Do A"),
            pre_conditions=[
                Gate(
                    check="File must exist",
                    type="file_exists",
                    target="nonexistent-file.txt",
                )
            ],
        )
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        final_state, result = auto.run_single_slot(slot, pipeline, state)
        assert result is None
        assert final_state.slots["slot-a"].status == SlotStatus.FAILED


# ===========================================================================
# TestObserverIntegration
# ===========================================================================


class TestObserverIntegration:
    """Tests that observer events fire correctly through AutoExecutor."""

    def test_slot_started_event(self, runner, contract_manager, registry, project_dirs):
        """Observer receives on_slot_started."""
        from pipeline.models import PipelineObserver, GateCheckResult

        class TrackingObserver(PipelineObserver):
            def __init__(self):
                self.events = []

            def on_pipeline_started(self, pid, state):
                self.events.append(("pipeline_started", pid))

            def on_pipeline_completed(self, pid, state):
                self.events.append(("pipeline_completed", pid))

            def on_pipeline_failed(self, pid, state, error):
                self.events.append(("pipeline_failed", pid))

            def on_slot_started(self, pid, sid, aid):
                self.events.append(("slot_started", sid))

            def on_slot_completed(self, pid, sid):
                self.events.append(("slot_completed", sid))

            def on_slot_failed(self, pid, sid, error):
                self.events.append(("slot_failed", sid))

            def on_gate_check_completed(self, pid, sid, gate_type, results):
                pass

            def on_status_changed(self, pid, old, new):
                self.events.append(("status_changed", old, new))

        observer = TrackingObserver()
        runner.add_observer(observer)

        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        auto.run(pipeline, state)

        event_types = [e[0] for e in observer.events]
        assert "slot_started" in event_types
        assert "slot_completed" in event_types

    def test_slot_failed_event(self, runner, contract_manager, registry, project_dirs):
        """Observer receives on_slot_failed."""
        from pipeline.models import PipelineObserver

        class FailObserver(PipelineObserver):
            def __init__(self):
                self.failed_slots = []

            def on_pipeline_started(self, pid, state): pass
            def on_pipeline_completed(self, pid, state): pass
            def on_pipeline_failed(self, pid, state, error): pass
            def on_slot_started(self, pid, sid, aid): pass
            def on_slot_completed(self, pid, sid): pass
            def on_slot_failed(self, pid, sid, error):
                self.failed_slots.append(sid)
            def on_gate_check_completed(self, pid, sid, gt, r): pass
            def on_status_changed(self, pid, old, new): pass

        observer = FailObserver()
        runner.add_observer(observer)

        slot = _make_slot("slot-a", retry_on_fail=False)
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: False)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        auto.run(pipeline, state)
        assert "slot-a" in observer.failed_slots

    def test_pipeline_completed_event(self, runner, contract_manager, registry, project_dirs):
        """Observer receives on_pipeline_completed when all slots done."""
        from pipeline.models import PipelineObserver

        class CompletionObserver(PipelineObserver):
            def __init__(self):
                self.completed = False

            def on_pipeline_started(self, pid, state): pass
            def on_pipeline_completed(self, pid, state):
                self.completed = True
            def on_pipeline_failed(self, pid, state, error): pass
            def on_slot_started(self, pid, sid, aid): pass
            def on_slot_completed(self, pid, sid): pass
            def on_slot_failed(self, pid, sid, error): pass
            def on_gate_check_completed(self, pid, sid, gt, r): pass
            def on_status_changed(self, pid, old, new): pass

        observer = CompletionObserver()
        runner.add_observer(observer)

        slot = _make_slot("slot-a")
        pipeline = _make_pipeline([slot])
        state = _make_state(pipeline)

        executor = CallbackExecutor(lambda si, aid: True)
        auto = AutoExecutor(
            runner, executor, contract_manager, registry,
            project_root=str(project_dirs),
        )
        auto.run(pipeline, state)
        assert observer.completed is True


# ===========================================================================
# TestGroupByParallel
# ===========================================================================


class TestGroupByParallel:
    """Tests for _group_by_parallel static method."""

    def test_no_parallel_group(self):
        """Slots without parallel_group get singleton groups."""
        slots = [_make_slot("a"), _make_slot("b")]
        pipeline = _make_pipeline(slots)
        groups = AutoExecutor._group_by_parallel(slots, pipeline)
        assert len(groups) == 2
        for group in groups.values():
            assert len(group) == 1

    def test_same_parallel_group(self):
        """Slots with same parallel_group are grouped."""
        slots = [
            _make_slot("a", parallel_group="g1"),
            _make_slot("b", parallel_group="g1"),
        ]
        pipeline = _make_pipeline(slots)
        groups = AutoExecutor._group_by_parallel(slots, pipeline)
        assert len(groups) == 1
        assert len(list(groups.values())[0]) == 2

    def test_mixed_groups(self):
        """Mix of grouped and singleton slots."""
        slots = [
            _make_slot("a", parallel_group="g1"),
            _make_slot("b", parallel_group="g1"),
            _make_slot("c"),  # singleton
        ]
        pipeline = _make_pipeline(slots)
        groups = AutoExecutor._group_by_parallel(slots, pipeline)
        assert len(groups) == 2
        assert "g1" in groups
        assert len(groups["g1"]) == 2
