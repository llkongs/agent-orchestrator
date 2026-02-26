"""Pipeline Engine for Agent Team Orchestration.

Usage:
    from pipeline import PipelineRunner

    runner = PipelineRunner(
        project_root="/path/to/project",
        templates_dir="/path/to/specs/pipelines/templates",
        state_dir="/path/to/state/active",
        slot_types_dir="/path/to/specs/pipelines/slot-types",
        agents_dir="/path/to/agents",
    )

    pipeline, state = runner.prepare("templates/standard-feature.yaml", params)
    next_slots = runner.get_next_slots(pipeline, state)
    print(runner.get_summary(state))
"""

from pipeline.context_router import ContextRouter
from pipeline.enforcer import SlotEnforcer, EnforcementRule, EnforcementResult, EnforcementAction
from pipeline.gate_checker import GateChecker
from pipeline.loader import PipelineLoader, PipelineLoadError, PipelineParameterError
from pipeline.models import (
    AgentCapabilities,
    ArtifactOutput,
    ArtifactRef,
    ArtifactType,
    CapabilityMatch,
    ConditionType,
    ContextItem,
    ContextTier,
    DataFlowEdge,
    DeterministicMetrics,
    ExecutionConfig,
    Gate,
    GateCheckResult,
    Parameter,
    Pipeline,
    PipelineObserver,
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
from pipeline.nl_matcher import NLMatcher, TemplateMatch
from pipeline.observer import ComplianceObserver
from pipeline.runner import PipelineExecutionError, PipelineRunner
from pipeline.slot_contract import SlotContractManager, SlotInput, SlotOutputValidation
from pipeline.slot_registry import SlotRegistry, SlotTypeNotFoundError
from pipeline.state import PipelineStateTracker, InvalidTransitionError
from pipeline.validator import PipelineCycleError, PipelineValidator, ValidationResult

__all__ = [
    # Context Router
    "ContextRouter",
    "ContextItem",
    "ContextTier",
    # Enforcer
    "SlotEnforcer",
    "EnforcementRule",
    "EnforcementResult",
    "EnforcementAction",
    # Models
    "AgentCapabilities",
    "ArtifactOutput",
    "ArtifactRef",
    "ArtifactType",
    "CapabilityMatch",
    "ConditionType",
    "DataFlowEdge",
    "DeterministicMetrics",
    "ExecutionConfig",
    "Gate",
    "GateCheckResult",
    "Parameter",
    "Pipeline",
    "PipelineState",
    "PipelineStatus",
    "Slot",
    "SlotAssignment",
    "SlotState",
    "SlotStatus",
    "SlotTask",
    "SlotTypeDefinition",
    "PipelineObserver",
    "ValidationLevel",
    # Observer
    "ComplianceObserver",
    # Loader
    "PipelineLoader",
    "PipelineLoadError",
    "PipelineParameterError",
    # Validator
    "PipelineValidator",
    "PipelineCycleError",
    "ValidationResult",
    # State
    "PipelineStateTracker",
    "InvalidTransitionError",
    # Slot Contract
    "SlotContractManager",
    "SlotInput",
    "SlotOutputValidation",
    # Slot Registry
    "SlotRegistry",
    "SlotTypeNotFoundError",
    # Gate Checker
    "GateChecker",
    # Runner
    "PipelineRunner",
    "PipelineExecutionError",
    # NL Matcher
    "NLMatcher",
    "TemplateMatch",
]
