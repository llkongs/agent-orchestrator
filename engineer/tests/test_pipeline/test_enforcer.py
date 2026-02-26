"""Tests for pipeline.enforcer -- Tool access control enforcement."""

import pytest
import yaml

from src.pipeline.enforcer import (
    AuditEntry,
    EnforcementAction,
    EnforcementResult,
    EnforcementRule,
    SlotEnforcer,
)


# ===================================================================
# Rule construction
# ===================================================================


class TestEnforcementRule:
    def test_basic_rule(self):
        rule = EnforcementRule(
            rule_id="test",
            description="Test rule",
            slot_types=["implementer"],
            denied_tools=["code_editor"],
        )
        assert rule.rule_id == "test"
        assert rule.slot_types == ["implementer"]

    def test_wildcard_rule(self):
        rule = EnforcementRule(
            rule_id="all",
            description="Applies to all",
            slot_types=["*"],
        )
        assert "*" in rule.slot_types


# ===================================================================
# check_action
# ===================================================================


class TestCheckAction:
    def test_no_rules_allows_all(self):
        enforcer = SlotEnforcer()
        result = enforcer.check_action("implementer", "code_editor")
        assert result.action == EnforcementAction.ALLOWED

    def test_denylist_blocks(self):
        rule = EnforcementRule(
            rule_id="CEO-no-code",
            description="CEO cannot edit code",
            slot_types=["approver", "coordinator"],
            denied_tools=["code_editor", "file_write", "git_commit"],
        )
        enforcer = SlotEnforcer([rule])
        result = enforcer.check_action("approver", "code_editor")
        assert result.action == EnforcementAction.DENIED
        assert result.rule_id == "CEO-no-code"

    def test_denylist_allows_other_tools(self):
        rule = EnforcementRule(
            rule_id="CEO-no-code",
            description="CEO cannot edit code",
            slot_types=["coordinator"],
            denied_tools=["code_editor"],
        )
        enforcer = SlotEnforcer([rule])
        result = enforcer.check_action("coordinator", "send_message")
        assert result.action == EnforcementAction.ALLOWED

    def test_allowlist_blocks_unlisted(self):
        rule = EnforcementRule(
            rule_id="ENG-code-only",
            description="Engineers can only use code tools",
            slot_types=["implementer"],
            allowed_tools=["code_editor", "file_write", "pytest"],
        )
        enforcer = SlotEnforcer([rule])
        result = enforcer.check_action("implementer", "deploy")
        assert result.action == EnforcementAction.DENIED

    def test_allowlist_permits_listed(self):
        rule = EnforcementRule(
            rule_id="ENG-code-only",
            description="Engineers can only use code tools",
            slot_types=["implementer"],
            allowed_tools=["code_editor", "file_write", "pytest"],
        )
        enforcer = SlotEnforcer([rule])
        result = enforcer.check_action("implementer", "pytest")
        assert result.action == EnforcementAction.ALLOWED

    def test_non_matching_slot_type_ignored(self):
        rule = EnforcementRule(
            rule_id="CEO-no-code",
            description="CEO rule",
            slot_types=["coordinator"],
            denied_tools=["code_editor"],
        )
        enforcer = SlotEnforcer([rule])
        # implementer is not in the rule's slot_types
        result = enforcer.check_action("implementer", "code_editor")
        assert result.action == EnforcementAction.ALLOWED

    def test_wildcard_matches_all_types(self):
        rule = EnforcementRule(
            rule_id="no-deploy",
            description="Nobody can deploy",
            slot_types=["*"],
            denied_tools=["deploy"],
        )
        enforcer = SlotEnforcer([rule])
        assert enforcer.check_action("implementer", "deploy").action == EnforcementAction.DENIED
        assert enforcer.check_action("reviewer", "deploy").action == EnforcementAction.DENIED
        assert enforcer.check_action("coordinator", "deploy").action == EnforcementAction.DENIED

    def test_deny_takes_precedence_over_allow(self):
        """If a tool is both allowed and denied, deny wins."""
        rules = [
            EnforcementRule(
                rule_id="allow-all",
                description="Allow everything",
                slot_types=["implementer"],
                allowed_tools=["code_editor", "git_commit"],
            ),
            EnforcementRule(
                rule_id="deny-git",
                description="But deny git",
                slot_types=["implementer"],
                denied_tools=["git_commit"],
            ),
        ]
        enforcer = SlotEnforcer(rules)
        result = enforcer.check_action("implementer", "git_commit")
        assert result.action == EnforcementAction.DENIED

    def test_multiple_rules_all_checked(self):
        rules = [
            EnforcementRule(
                rule_id="r1",
                description="Rule 1",
                slot_types=["reviewer"],
                denied_tools=["code_editor"],
            ),
            EnforcementRule(
                rule_id="r2",
                description="Rule 2",
                slot_types=["reviewer"],
                denied_tools=["deploy"],
            ),
        ]
        enforcer = SlotEnforcer(rules)
        assert enforcer.check_action("reviewer", "code_editor").action == EnforcementAction.DENIED
        assert enforcer.check_action("reviewer", "deploy").action == EnforcementAction.DENIED
        assert enforcer.check_action("reviewer", "pytest").action == EnforcementAction.ALLOWED


# ===================================================================
# check_completion_requirements
# ===================================================================


class TestCompletionRequirements:
    def test_no_requirements(self):
        enforcer = SlotEnforcer()
        missing = enforcer.check_completion_requirements("reviewer", {"pytest"})
        assert missing == []

    def test_requirements_met(self):
        rule = EnforcementRule(
            rule_id="QA-must-test",
            description="QA must run pytest",
            slot_types=["reviewer"],
            required_tools=["pytest", "coverage"],
        )
        enforcer = SlotEnforcer([rule])
        missing = enforcer.check_completion_requirements(
            "reviewer", {"pytest", "coverage", "file_read"}
        )
        assert missing == []

    def test_requirements_not_met(self):
        rule = EnforcementRule(
            rule_id="QA-must-test",
            description="QA must run pytest and coverage",
            slot_types=["reviewer"],
            required_tools=["pytest", "coverage"],
        )
        enforcer = SlotEnforcer([rule])
        missing = enforcer.check_completion_requirements(
            "reviewer", {"file_read"}
        )
        assert "pytest" in missing
        assert "coverage" in missing

    def test_partial_requirements(self):
        rule = EnforcementRule(
            rule_id="QA-must-test",
            description="QA must run pytest and coverage",
            slot_types=["reviewer"],
            required_tools=["pytest", "coverage"],
        )
        enforcer = SlotEnforcer([rule])
        missing = enforcer.check_completion_requirements(
            "reviewer", {"pytest"}
        )
        assert missing == ["coverage"]

    def test_non_matching_type_no_requirements(self):
        rule = EnforcementRule(
            rule_id="QA-must-test",
            description="QA rule",
            slot_types=["reviewer"],
            required_tools=["pytest"],
        )
        enforcer = SlotEnforcer([rule])
        missing = enforcer.check_completion_requirements("implementer", set())
        assert missing == []


# ===================================================================
# Audit logging
# ===================================================================


class TestAuditLogging:
    def test_record_action(self):
        enforcer = SlotEnforcer()
        result = EnforcementResult(
            action=EnforcementAction.ALLOWED,
            tool_name="pytest",
            slot_type="reviewer",
            rule_id=None,
            reason="allowed",
        )
        enforcer.record_action("slot-1", "QA-001", "pytest", result)
        log = enforcer.get_audit_log()
        assert len(log) == 1
        assert log[0].tool_name == "pytest"
        assert log[0].slot_id == "slot-1"

    def test_tools_used_tracking(self):
        enforcer = SlotEnforcer()
        allowed = EnforcementResult(
            action=EnforcementAction.ALLOWED,
            tool_name="pytest", slot_type="reviewer",
            rule_id=None, reason="ok",
        )
        denied = EnforcementResult(
            action=EnforcementAction.DENIED,
            tool_name="deploy", slot_type="reviewer",
            rule_id="r1", reason="denied",
        )
        enforcer.record_action("slot-1", "QA-001", "pytest", allowed)
        enforcer.record_action("slot-1", "QA-001", "deploy", denied)

        tools = enforcer.get_tools_used("slot-1")
        assert "pytest" in tools
        assert "deploy" not in tools  # denied tools not tracked

    def test_get_denied_actions(self):
        enforcer = SlotEnforcer()
        allowed = EnforcementResult(
            action=EnforcementAction.ALLOWED,
            tool_name="pytest", slot_type="reviewer",
            rule_id=None, reason="ok",
        )
        denied = EnforcementResult(
            action=EnforcementAction.DENIED,
            tool_name="deploy", slot_type="reviewer",
            rule_id="r1", reason="denied",
        )
        enforcer.record_action("slot-1", "QA-001", "pytest", allowed)
        enforcer.record_action("slot-1", "QA-001", "deploy", denied)

        denied_list = enforcer.get_denied_actions()
        assert len(denied_list) == 1
        assert denied_list[0].tool_name == "deploy"


# ===================================================================
# YAML loading
# ===================================================================


class TestFromYaml:
    def test_load_rules(self, tmp_path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml.dump({
            "rules": [
                {
                    "rule_id": "CEO-no-code",
                    "description": "CEO cannot edit code",
                    "slot_types": ["coordinator"],
                    "denied_tools": ["code_editor"],
                },
                {
                    "rule_id": "QA-must-test",
                    "description": "QA must run pytest",
                    "slot_types": ["reviewer"],
                    "required_tools": ["pytest"],
                },
            ]
        }))
        enforcer = SlotEnforcer.from_yaml(str(rules_file))
        assert enforcer.check_action("coordinator", "code_editor").action == EnforcementAction.DENIED
        missing = enforcer.check_completion_requirements("reviewer", set())
        assert "pytest" in missing

    def test_missing_file(self, tmp_path):
        enforcer = SlotEnforcer.from_yaml(str(tmp_path / "nonexistent.yaml"))
        # No rules -> everything allowed
        assert enforcer.check_action("any", "any").action == EnforcementAction.ALLOWED

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        enforcer = SlotEnforcer.from_yaml(str(f))
        assert enforcer.check_action("any", "any").action == EnforcementAction.ALLOWED


# ===================================================================
# add_rule
# ===================================================================


class TestAddRule:
    def test_runtime_rule_addition(self):
        enforcer = SlotEnforcer()
        assert enforcer.check_action("coordinator", "code_editor").action == EnforcementAction.ALLOWED
        enforcer.add_rule(EnforcementRule(
            rule_id="new-rule",
            description="Block code_editor",
            slot_types=["coordinator"],
            denied_tools=["code_editor"],
        ))
        assert enforcer.check_action("coordinator", "code_editor").action == EnforcementAction.DENIED
