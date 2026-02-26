"""Enforcement layer for slot-level tool access control.

Provides structural constraints on what tools each slot type can use.
Prevents role boundary violations (e.g., CEO editing code, QA skipping tests)
at the engine level, not through prompting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import yaml
from pathlib import Path


class EnforcementAction(StrEnum):
    """Result of an enforcement check."""

    ALLOWED = "allowed"
    DENIED = "denied"


@dataclass(frozen=True)
class EnforcementRule:
    """A rule constraining tool usage for specific slot types.

    Rules are evaluated in order:
    1. If denied_tools contains the tool -> DENIED
    2. If allowed_tools is non-empty and doesn't contain the tool -> DENIED
    3. Otherwise -> ALLOWED

    required_tools lists tools that MUST be invoked before a slot can
    be marked as completed.
    """

    rule_id: str
    description: str
    slot_types: list[str]  # ["*"] matches all types
    allowed_tools: list[str] | None = None  # None = no allowlist
    denied_tools: list[str] | None = None  # None = no denylist
    required_tools: list[str] | None = None  # None = no requirements


@dataclass(frozen=True)
class EnforcementResult:
    """Result of checking a single action."""

    action: EnforcementAction
    tool_name: str
    slot_type: str
    rule_id: str | None  # Which rule triggered the decision
    reason: str


@dataclass
class AuditEntry:
    """A recorded action for auditing."""

    slot_id: str
    agent_id: str
    tool_name: str
    action: EnforcementAction
    rule_id: str | None
    timestamp: str


class SlotEnforcer:
    """Enforces tool usage constraints per slot type.

    This is the structural enforcement layer that makes role violations
    physically impossible rather than relying on prompts.
    """

    def __init__(self, rules: list[EnforcementRule] | None = None) -> None:
        self._rules: list[EnforcementRule] = rules or []
        self._audit_log: list[AuditEntry] = []
        self._tools_used: dict[str, set[str]] = {}  # slot_id -> {tools}

    @classmethod
    def from_yaml(cls, path: str) -> SlotEnforcer:
        """Load enforcement rules from a YAML file.

        Expected format:
            rules:
              - rule_id: "CEO-no-code"
                description: "CEO cannot use code editing tools"
                slot_types: ["approver", "coordinator"]
                denied_tools: ["code_editor", "file_write"]
        """
        p = Path(path)
        if not p.exists():
            return cls()
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not data or "rules" not in data:
            return cls()
        rules = []
        for r in data["rules"]:
            rules.append(EnforcementRule(
                rule_id=r["rule_id"],
                description=r.get("description", ""),
                slot_types=r.get("slot_types", ["*"]),
                allowed_tools=r.get("allowed_tools"),
                denied_tools=r.get("denied_tools"),
                required_tools=r.get("required_tools"),
            ))
        return cls(rules)

    def add_rule(self, rule: EnforcementRule) -> None:
        """Add a rule at runtime."""
        self._rules.append(rule)

    def check_action(
        self, slot_type: str, tool_name: str
    ) -> EnforcementResult:
        """Check if a tool is allowed for a given slot type.

        Evaluation order:
        1. Find all rules matching this slot_type
        2. If any rule's denied_tools contains tool_name -> DENIED
        3. If any rule has allowed_tools and tool_name not in it -> DENIED
        4. Otherwise -> ALLOWED

        Args:
            slot_type: The slot type (e.g., "approver", "implementer").
            tool_name: The tool being requested (e.g., "code_editor").

        Returns:
            EnforcementResult with action and reason.
        """
        matching_rules = self._get_matching_rules(slot_type)

        if not matching_rules:
            return EnforcementResult(
                action=EnforcementAction.ALLOWED,
                tool_name=tool_name,
                slot_type=slot_type,
                rule_id=None,
                reason="No enforcement rules for this slot type",
            )

        # Check denylists first
        for rule in matching_rules:
            if rule.denied_tools and tool_name in rule.denied_tools:
                return EnforcementResult(
                    action=EnforcementAction.DENIED,
                    tool_name=tool_name,
                    slot_type=slot_type,
                    rule_id=rule.rule_id,
                    reason=f"Tool '{tool_name}' is denied by rule '{rule.rule_id}': {rule.description}",
                )

        # Check allowlists
        for rule in matching_rules:
            if rule.allowed_tools is not None and tool_name not in rule.allowed_tools:
                return EnforcementResult(
                    action=EnforcementAction.DENIED,
                    tool_name=tool_name,
                    slot_type=slot_type,
                    rule_id=rule.rule_id,
                    reason=f"Tool '{tool_name}' not in allowlist of rule '{rule.rule_id}': {rule.description}",
                )

        return EnforcementResult(
            action=EnforcementAction.ALLOWED,
            tool_name=tool_name,
            slot_type=slot_type,
            rule_id=None,
            reason="Tool is allowed",
        )

    def check_completion_requirements(
        self, slot_type: str, tools_used: set[str]
    ) -> list[str]:
        """Check if all required tools have been invoked.

        Args:
            slot_type: The slot type being completed.
            tools_used: Set of tool names that were actually used.

        Returns:
            List of missing required tools. Empty = all satisfied.
        """
        matching_rules = self._get_matching_rules(slot_type)
        missing: list[str] = []

        for rule in matching_rules:
            if rule.required_tools:
                for tool in rule.required_tools:
                    if tool not in tools_used:
                        missing.append(tool)

        return sorted(set(missing))

    def record_action(
        self,
        slot_id: str,
        agent_id: str,
        tool_name: str,
        result: EnforcementResult,
    ) -> None:
        """Record an action to the audit log and track tools used."""
        now = datetime.now(timezone.utc).isoformat()
        self._audit_log.append(AuditEntry(
            slot_id=slot_id,
            agent_id=agent_id,
            tool_name=tool_name,
            action=result.action,
            rule_id=result.rule_id,
            timestamp=now,
        ))

        if result.action == EnforcementAction.ALLOWED:
            self._tools_used.setdefault(slot_id, set()).add(tool_name)

    def get_tools_used(self, slot_id: str) -> set[str]:
        """Get the set of tools used by a specific slot."""
        return set(self._tools_used.get(slot_id, set()))

    def get_audit_log(self) -> list[AuditEntry]:
        """Get the full audit log."""
        return list(self._audit_log)

    def get_denied_actions(self) -> list[AuditEntry]:
        """Get only denied actions from the audit log."""
        return [e for e in self._audit_log if e.action == EnforcementAction.DENIED]

    # --- Private ---

    def _get_matching_rules(self, slot_type: str) -> list[EnforcementRule]:
        """Find all rules that apply to a given slot type."""
        matching = []
        for rule in self._rules:
            if "*" in rule.slot_types or slot_type in rule.slot_types:
                matching.append(rule)
        return matching
