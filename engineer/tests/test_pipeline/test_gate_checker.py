"""Tests for pipeline.gate_checker -- Pre/post-condition evaluation."""

import subprocess
from unittest.mock import patch

import pytest
import yaml

from src.pipeline.gate_checker import GateChecker
from src.pipeline.models import (
    Gate,
    GateCheckResult,
    PipelineState,
    PipelineStatus,
    Slot,
    SlotState,
    SlotStatus,
    SlotTask,
)


@pytest.fixture
def checker(tmp_path):
    """GateChecker rooted at tmp_path."""
    return GateChecker(str(tmp_path))


@pytest.fixture
def pipeline_state():
    """PipelineState with two slots in different statuses."""
    return PipelineState(
        pipeline_id="test-pipe",
        pipeline_version="1.0.0",
        definition_hash="sha256:abc",
        slots={
            "slot-a": SlotState(
                slot_id="slot-a", status=SlotStatus.COMPLETED
            ),
            "slot-b": SlotState(
                slot_id="slot-b", status=SlotStatus.IN_PROGRESS
            ),
        },
    )


# ===================================================================
# check_file_exists
# ===================================================================


class TestCheckFileExists:
    def test_file_present(self, checker, tmp_path):
        (tmp_path / "hello.txt").write_text("content")
        result = checker.check_file_exists("hello.txt")
        assert result.passed is True
        assert "File exists" in result.condition
        assert result.checked_at  # non-empty ISO timestamp

    def test_file_missing(self, checker):
        result = checker.check_file_exists("nonexistent.txt")
        assert result.passed is False
        assert "not found" in result.evidence

    def test_nested_path(self, checker, tmp_path):
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "deep.txt").write_text("ok")
        result = checker.check_file_exists("a/b/deep.txt")
        assert result.passed is True


# ===================================================================
# check_slot_completed
# ===================================================================


class TestCheckSlotCompleted:
    def test_completed_slot(self, checker, pipeline_state):
        result = checker.check_slot_completed("slot-a", pipeline_state)
        assert result.passed is True
        assert "COMPLETED" in result.evidence

    def test_not_completed_slot(self, checker, pipeline_state):
        result = checker.check_slot_completed("slot-b", pipeline_state)
        assert result.passed is False
        assert "in_progress" in result.evidence

    def test_unknown_slot(self, checker, pipeline_state):
        result = checker.check_slot_completed("slot-z", pipeline_state)
        assert result.passed is False
        assert "not found" in result.evidence


# ===================================================================
# check_delivery_valid
# ===================================================================


class TestCheckDeliveryValid:
    def test_valid_delivery(self, checker, tmp_path):
        data = {"version": "1.0", "agent_id": "ENG-001", "status": "done"}
        (tmp_path / "DELIVERY.yaml").write_text(yaml.dump(data))
        result = checker.check_delivery_valid("DELIVERY.yaml")
        assert result.passed is True
        assert "valid YAML" in result.evidence

    def test_missing_file(self, checker):
        result = checker.check_delivery_valid("DELIVERY.yaml")
        assert result.passed is False
        assert "not found" in result.evidence

    def test_empty_file(self, checker, tmp_path):
        (tmp_path / "DELIVERY.yaml").write_text("")
        result = checker.check_delivery_valid("DELIVERY.yaml")
        assert result.passed is False
        assert "empty" in result.evidence

    def test_missing_required_fields(self, checker, tmp_path):
        data = {"version": "1.0"}  # missing agent_id and status
        (tmp_path / "DELIVERY.yaml").write_text(yaml.dump(data))
        result = checker.check_delivery_valid("DELIVERY.yaml")
        assert result.passed is False
        assert "Missing fields" in result.evidence
        assert "agent_id" in result.evidence
        assert "status" in result.evidence

    def test_invalid_yaml(self, checker, tmp_path):
        (tmp_path / "DELIVERY.yaml").write_text(":\n  bad:\n - ][")
        result = checker.check_delivery_valid("DELIVERY.yaml")
        assert result.passed is False
        assert "Error" in result.evidence


# ===================================================================
# check_review_valid
# ===================================================================


class TestCheckReviewValid:
    def test_valid_review(self, checker, tmp_path):
        data = {"version": "1.0", "agent_id": "QA-001", "verdict": "pass"}
        (tmp_path / "REVIEW.yaml").write_text(yaml.dump(data))
        result = checker.check_review_valid("REVIEW.yaml")
        assert result.passed is True

    def test_missing_file(self, checker):
        result = checker.check_review_valid("REVIEW.yaml")
        assert result.passed is False
        assert "not found" in result.evidence

    def test_empty_file(self, checker, tmp_path):
        (tmp_path / "REVIEW.yaml").write_text("")
        result = checker.check_review_valid("REVIEW.yaml")
        assert result.passed is False
        assert "empty" in result.evidence

    def test_missing_required_fields(self, checker, tmp_path):
        data = {"version": "1.0"}  # missing agent_id and verdict
        (tmp_path / "REVIEW.yaml").write_text(yaml.dump(data))
        result = checker.check_review_valid("REVIEW.yaml")
        assert result.passed is False
        assert "Missing fields" in result.evidence

    def test_invalid_yaml(self, checker, tmp_path):
        (tmp_path / "REVIEW.yaml").write_text(":\n  bad:\n - ][")
        result = checker.check_review_valid("REVIEW.yaml")
        assert result.passed is False
        assert "Error" in result.evidence


# ===================================================================
# check_tests_pass
# ===================================================================


class TestCheckTestsPass:
    def test_missing_test_dir(self, checker):
        result = checker.check_tests_pass("tests/nonexistent")
        assert result.passed is False
        assert "not found" in result.evidence

    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_tests_pass(self, mock_run, checker, tmp_path):
        (tmp_path / "tests").mkdir()
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="3 passed", stderr=""
        )
        result = checker.check_tests_pass("tests")
        assert result.passed is True
        assert "passed" in result.evidence

    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_tests_fail(self, mock_run, checker, tmp_path):
        (tmp_path / "tests").mkdir()
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="1 failed, 2 passed", stderr=""
        )
        result = checker.check_tests_pass("tests")
        assert result.passed is False
        assert "failed" in result.evidence

    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_tests_timeout(self, mock_run, checker, tmp_path):
        (tmp_path / "tests").mkdir()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=300)
        result = checker.check_tests_pass("tests")
        assert result.passed is False
        assert "Error" in result.evidence

    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_tests_pass_empty_stdout(self, mock_run, checker, tmp_path):
        (tmp_path / "tests").mkdir()
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = checker.check_tests_pass("tests")
        assert result.passed is True
        assert "Tests passed" in result.evidence


# ===================================================================
# evaluate_custom -- yaml_field
# ===================================================================


class TestEvalYamlField:
    def test_equality_pass(self, checker, tmp_path):
        data = {"status": "pass", "coverage": 95}
        (tmp_path / "report.yaml").write_text(yaml.dump(data))
        result = checker.evaluate_custom("yaml_field:report.yaml:status == pass")
        assert result.passed is True

    def test_equality_fail(self, checker, tmp_path):
        data = {"status": "fail"}
        (tmp_path / "report.yaml").write_text(yaml.dump(data))
        result = checker.evaluate_custom("yaml_field:report.yaml:status == pass")
        assert result.passed is False
        assert "FAIL" in result.evidence

    def test_numeric_greater_than(self, checker, tmp_path):
        data = {"metrics": {"coverage": 92}}
        (tmp_path / "report.yaml").write_text(yaml.dump(data))
        result = checker.evaluate_custom(
            "yaml_field:report.yaml:metrics.coverage >= 85"
        )
        assert result.passed is True

    def test_numeric_less_than_fail(self, checker, tmp_path):
        data = {"metrics": {"coverage": 80}}
        (tmp_path / "report.yaml").write_text(yaml.dump(data))
        result = checker.evaluate_custom(
            "yaml_field:report.yaml:metrics.coverage >= 85"
        )
        assert result.passed is False

    def test_not_equal(self, checker, tmp_path):
        data = {"verdict": "pass"}
        (tmp_path / "r.yaml").write_text(yaml.dump(data))
        result = checker.evaluate_custom("yaml_field:r.yaml:verdict != fail")
        assert result.passed is True

    def test_nested_path(self, checker, tmp_path):
        data = {"a": {"b": {"c": "deep_value"}}}
        (tmp_path / "nested.yaml").write_text(yaml.dump(data))
        result = checker.evaluate_custom(
            "yaml_field:nested.yaml:a.b.c == deep_value"
        )
        assert result.passed is True

    def test_missing_field(self, checker, tmp_path):
        data = {"other_field": "val"}
        (tmp_path / "d.yaml").write_text(yaml.dump(data))
        result = checker.evaluate_custom("yaml_field:d.yaml:missing_key == x")
        assert result.passed is False
        assert "not found" in result.evidence

    def test_missing_file(self, checker):
        result = checker.evaluate_custom(
            "yaml_field:nonexistent.yaml:field == val"
        )
        assert result.passed is False
        assert "not found" in result.evidence

    def test_invalid_expression_no_operator(self, checker):
        result = checker.evaluate_custom("yaml_field:file.yaml:field")
        assert result.passed is False
        assert "missing operator" in result.evidence

    def test_invalid_expression_no_field_path(self, checker):
        result = checker.evaluate_custom("yaml_field:file_only == val")
        assert result.passed is False
        assert "expected file:field_path" in result.evidence

    def test_invalid_operator(self, checker):
        result = checker.evaluate_custom("yaml_field:f.yaml:x ~~ val")
        assert result.passed is False
        assert "Invalid operator" in result.evidence


# ===================================================================
# evaluate_custom -- command
# ===================================================================


class TestEvalCommand:
    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_command_success(self, mock_run, checker):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="OK", stderr=""
        )
        result = checker.evaluate_custom("command:echo hello")
        assert result.passed is True
        assert "OK" in result.evidence

    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_command_failure(self, mock_run, checker):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error msg"
        )
        result = checker.evaluate_custom("command:false")
        assert result.passed is False
        assert "error msg" in result.evidence

    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_command_no_output(self, mock_run, checker):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=""
        )
        result = checker.evaluate_custom("command:false")
        assert result.passed is False
        assert "Exit code: 1" in result.evidence

    @patch("src.pipeline.gate_checker.subprocess.run")
    def test_command_exception(self, mock_run, checker):
        mock_run.side_effect = FileNotFoundError("cmd not found")
        result = checker.evaluate_custom("command:nonexistent_binary")
        assert result.passed is False
        assert "Error" in result.evidence

    def test_unknown_custom_format(self, checker):
        result = checker.evaluate_custom("unknown_prefix:something")
        assert result.passed is False
        assert "Unknown custom expression" in result.evidence


# ===================================================================
# all_passed
# ===================================================================


class TestAllPassed:
    def test_all_true(self, checker):
        results = [
            GateCheckResult(
                condition="c1", passed=True, evidence="ok", checked_at="t"
            ),
            GateCheckResult(
                condition="c2", passed=True, evidence="ok", checked_at="t"
            ),
        ]
        assert checker.all_passed(results) is True

    def test_one_false(self, checker):
        results = [
            GateCheckResult(
                condition="c1", passed=True, evidence="ok", checked_at="t"
            ),
            GateCheckResult(
                condition="c2", passed=False, evidence="fail", checked_at="t"
            ),
        ]
        assert checker.all_passed(results) is False

    def test_empty_list(self, checker):
        assert checker.all_passed([]) is True


# ===================================================================
# check_pre_conditions / check_post_conditions (dispatch)
# ===================================================================


class TestPrePostConditions:
    def test_pre_conditions_dispatch(self, checker, tmp_path, pipeline_state):
        (tmp_path / "design.md").write_text("design content")
        slot = Slot(
            id="s1",
            slot_type="implementer",
            name="S1",
            pre_conditions=[
                Gate(
                    check="Design file exists",
                    type="file_exists",
                    target="design.md",
                ),
                Gate(
                    check="Slot A completed",
                    type="slot_completed",
                    target="slot-a",
                ),
            ],
        )
        results = checker.check_pre_conditions(slot, pipeline_state)
        assert len(results) == 2
        assert results[0].passed is True  # file_exists
        assert results[1].passed is True  # slot_completed (slot-a is COMPLETED)

    def test_post_conditions_dispatch(self, checker, tmp_path, pipeline_state):
        data = {"version": "1.0", "agent_id": "ENG-001", "status": "done"}
        (tmp_path / "DELIVERY.yaml").write_text(yaml.dump(data))
        slot = Slot(
            id="s1",
            slot_type="implementer",
            name="S1",
            post_conditions=[
                Gate(
                    check="Delivery is valid",
                    type="delivery_valid",
                    target="DELIVERY.yaml",
                ),
            ],
        )
        results = checker.check_post_conditions(slot, pipeline_state)
        assert len(results) == 1
        assert results[0].passed is True

    def test_empty_conditions(self, checker, pipeline_state):
        slot = Slot(id="s1", slot_type="implementer", name="S1")
        pre = checker.check_pre_conditions(slot, pipeline_state)
        post = checker.check_post_conditions(slot, pipeline_state)
        assert pre == []
        assert post == []


# ===================================================================
# _dispatch edge cases
# ===================================================================


class TestDispatch:
    def test_unknown_gate_type(self, checker, pipeline_state):
        slot = Slot(
            id="s1",
            slot_type="implementer",
            name="S1",
            pre_conditions=[
                Gate(
                    check="Unknown check",
                    type="nonexistent_type",
                    target="x",
                ),
            ],
        )
        results = checker.check_pre_conditions(slot, pipeline_state)
        assert len(results) == 1
        assert results[0].passed is False
        assert "Unknown gate type" in results[0].evidence

    def test_approval_auto_pass(self, checker, pipeline_state):
        slot = Slot(
            id="s1",
            slot_type="implementer",
            name="S1",
            pre_conditions=[
                Gate(
                    check="CEO approval",
                    type="approval",
                    target="ceo",
                ),
            ],
        )
        results = checker.check_pre_conditions(slot, pipeline_state)
        assert len(results) == 1
        assert results[0].passed is True
        assert "auto-passed" in results[0].evidence

    def test_artifact_valid_auto_pass(self, checker, pipeline_state):
        slot = Slot(
            id="s1",
            slot_type="implementer",
            name="S1",
            pre_conditions=[
                Gate(
                    check="Artifact valid",
                    type="artifact_valid",
                    target="design.md",
                ),
            ],
        )
        results = checker.check_pre_conditions(slot, pipeline_state)
        assert len(results) == 1
        assert results[0].passed is True


# ===================================================================
# _navigate_path
# ===================================================================


class TestNavigatePath:
    def test_simple_path(self):
        data = {"a": "value"}
        assert GateChecker._navigate_path(data, "a") == "value"

    def test_nested_path(self):
        data = {"a": {"b": {"c": 42}}}
        assert GateChecker._navigate_path(data, "a.b.c") == 42

    def test_missing_key(self):
        data = {"a": 1}
        assert GateChecker._navigate_path(data, "b") is None

    def test_missing_nested(self):
        data = {"a": {"b": 1}}
        assert GateChecker._navigate_path(data, "a.c") is None

    def test_non_dict_intermediate(self):
        data = {"a": "string_not_dict"}
        assert GateChecker._navigate_path(data, "a.b") is None


# ===================================================================
# _compare
# ===================================================================


class TestCompare:
    def test_eq_pass(self):
        assert GateChecker._compare("pass", "==", "pass") is True

    def test_eq_fail(self):
        assert GateChecker._compare("fail", "==", "pass") is False

    def test_ne_pass(self):
        assert GateChecker._compare("fail", "!=", "pass") is True

    def test_ne_fail(self):
        assert GateChecker._compare("pass", "!=", "pass") is False

    def test_gt(self):
        assert GateChecker._compare("10", ">", "5") is True
        assert GateChecker._compare("3", ">", "5") is False

    def test_lt(self):
        assert GateChecker._compare("3", "<", "5") is True
        assert GateChecker._compare("10", "<", "5") is False

    def test_gte(self):
        assert GateChecker._compare("5", ">=", "5") is True
        assert GateChecker._compare("6", ">=", "5") is True
        assert GateChecker._compare("4", ">=", "5") is False

    def test_lte(self):
        assert GateChecker._compare("5", "<=", "5") is True
        assert GateChecker._compare("4", "<=", "5") is True
        assert GateChecker._compare("6", "<=", "5") is False

    def test_non_numeric_comparison(self):
        # Non-numeric values with >, <, >=, <= should return False
        assert GateChecker._compare("abc", ">", "def") is False
        assert GateChecker._compare("abc", "<", "def") is False
