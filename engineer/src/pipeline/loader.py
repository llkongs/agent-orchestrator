"""YAML loading and parameter resolution for pipeline definitions.

Loads pipeline YAML files, hydrates them into Pipeline objects, and
resolves {parameter} placeholders with concrete values.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from pipeline.models import (
    ArtifactOutput,
    ArtifactRef,
    DataFlowEdge,
    ExecutionConfig,
    Gate,
    Parameter,
    Pipeline,
    Slot,
    SlotTask,
)


class PipelineLoadError(Exception):
    """Raised when pipeline YAML is malformed or missing required fields."""


class PipelineParameterError(Exception):
    """Raised when a required parameter is not provided."""


_PIPELINE_REQUIRED_FIELDS = {"id", "name", "version", "description", "created_by", "created_at"}


class PipelineLoader:
    """Loads pipeline YAML files and hydrates them into Pipeline objects."""

    def load(self, yaml_path: str) -> Pipeline:
        """Parse YAML file into Pipeline object.

        Args:
            yaml_path: Absolute or relative path to the pipeline YAML.

        Returns:
            Pipeline object with all fields populated.

        Raises:
            PipelineLoadError: File not found, YAML malformed, or required
                               fields missing.
        """
        path = Path(yaml_path)
        if not path.exists():
            raise PipelineLoadError(f"Pipeline file not found: {yaml_path}")

        try:
            raw_text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise PipelineLoadError(f"Malformed YAML in {yaml_path}: {exc}") from exc

        if data is None:
            raise PipelineLoadError(f"Empty YAML file: {yaml_path}")

        if not isinstance(data, dict):
            raise PipelineLoadError(f"Expected YAML mapping, got {type(data).__name__}")

        # Handle both `pipeline:` wrapper key and bare fields
        if "pipeline" in data and isinstance(data["pipeline"], dict):
            data = data["pipeline"]

        missing = _PIPELINE_REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise PipelineLoadError(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )

        return self._hydrate_pipeline(data)

    def resolve(self, pipeline: Pipeline, params: dict[str, Any]) -> Pipeline:
        """Replace {parameter} placeholders with concrete values.

        Args:
            pipeline: The Pipeline to resolve (not modified).
            params: Parameter name -> value mapping.

        Returns:
            New Pipeline instance with placeholders replaced.

        Raises:
            PipelineParameterError: A required parameter has no value and no default.
        """
        resolved_params = self._resolve_params(pipeline.parameters, params)
        return self._apply_params(pipeline, resolved_params)

    def load_and_resolve(
        self, yaml_path: str, params: dict[str, Any]
    ) -> Pipeline:
        """Convenience: load() then resolve().

        Args:
            yaml_path: Path to pipeline YAML.
            params: Parameter values.

        Returns:
            Resolved Pipeline object.
        """
        pipeline = self.load(yaml_path)
        return self.resolve(pipeline, params)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _hydrate_pipeline(self, data: dict) -> Pipeline:
        """Convert raw dict to Pipeline dataclass."""
        parameters = [
            self._hydrate_parameter(p)
            for p in data.get("parameters", []) or []
        ]
        slots = [
            self._hydrate_slot(s)
            for s in data.get("slots", []) or []
        ]
        data_flow = [
            self._hydrate_data_flow(df)
            for df in data.get("data_flow", []) or []
        ]
        return Pipeline(
            id=str(data["id"]),
            name=str(data["name"]),
            version=str(data["version"]),
            description=str(data["description"]),
            created_by=str(data["created_by"]),
            created_at=str(data["created_at"]),
            parameters=parameters,
            slots=slots,
            data_flow=data_flow,
        )

    @staticmethod
    def _hydrate_parameter(data: dict) -> Parameter:
        return Parameter(
            name=str(data["name"]),
            type=str(data.get("type", "string")),
            description=str(data.get("description", "")),
            default=data.get("default"),
            required=bool(data.get("required", False)),
        )

    def _hydrate_slot(self, data: dict) -> Slot:
        inputs = [
            self._hydrate_artifact_ref(i)
            for i in data.get("inputs", []) or []
        ]
        outputs = [
            self._hydrate_artifact_output(o)
            for o in data.get("outputs", []) or []
        ]
        pre_conditions = [
            self._hydrate_gate(g)
            for g in data.get("pre_conditions", []) or []
        ]
        post_conditions = [
            self._hydrate_gate(g)
            for g in data.get("post_conditions", []) or []
        ]
        task = None
        if data.get("task"):
            task = self._hydrate_slot_task(data["task"])
        execution = ExecutionConfig()
        if data.get("execution"):
            execution = self._hydrate_execution_config(data["execution"])
        return Slot(
            id=str(data["id"]),
            slot_type=str(data.get("slot_type", "")),
            name=str(data["name"]),
            inputs=inputs,
            outputs=outputs,
            pre_conditions=pre_conditions,
            post_conditions=post_conditions,
            depends_on=list(data.get("depends_on", []) or []),
            task=task,
            execution=execution,
        )

    @staticmethod
    def _hydrate_artifact_ref(data: dict) -> ArtifactRef:
        return ArtifactRef(
            name=str(data["name"]),
            from_slot=str(data["from_slot"]),
            artifact=str(data["artifact"]),
            required=bool(data.get("required", True)),
        )

    @staticmethod
    def _hydrate_artifact_output(data: dict) -> ArtifactOutput:
        return ArtifactOutput(
            name=str(data["name"]),
            type=str(data.get("type", "slot_output")),
            path=data.get("path"),
            validation=str(data.get("validation", "exists")),
        )

    @staticmethod
    def _hydrate_gate(data: dict) -> Gate:
        return Gate(
            check=str(data.get("check", "")),
            type=str(data.get("type", "custom")),
            target=str(data.get("target", "")),
        )

    @staticmethod
    def _hydrate_slot_task(data: dict) -> SlotTask:
        return SlotTask(
            objective=str(data.get("objective", "")),
            context_files=list(data.get("context_files", []) or []),
            deliverables=list(data.get("deliverables", []) or []),
            constraints=list(data.get("constraints", []) or []),
            kpis=list(data.get("kpis", []) or []),
        )

    @staticmethod
    def _hydrate_execution_config(data: dict) -> ExecutionConfig:
        return ExecutionConfig(
            timeout_hours=float(data.get("timeout_hours", 4.0)),
            retry_on_fail=bool(data.get("retry_on_fail", True)),
            max_retries=int(data.get("max_retries", 2)),
            parallel_group=data.get("parallel_group"),
        )

    @staticmethod
    def _hydrate_data_flow(data: dict) -> DataFlowEdge:
        return DataFlowEdge(
            from_slot=str(data["from_slot"]),
            to_slot=str(data["to_slot"]),
            artifact=str(data["artifact"]),
            required=bool(data.get("required", True)),
        )

    def _resolve_params(
        self, defined_params: list[Parameter], provided: dict[str, Any]
    ) -> dict[str, Any]:
        """Build final param map: provided values + defaults.

        Raises PipelineParameterError for missing required params.
        """
        resolved: dict[str, Any] = {}
        for param in defined_params:
            if param.name in provided:
                resolved[param.name] = self._coerce_param(
                    param.name, param.type, provided[param.name]
                )
            elif param.default is not None:
                resolved[param.name] = param.default
            elif param.required:
                raise PipelineParameterError(
                    f"Required parameter '{param.name}' not provided and has no default"
                )
        # Also include any extra params not in the schema (pass-through)
        for key, val in provided.items():
            if key not in resolved:
                resolved[key] = val
        return resolved

    @staticmethod
    def _coerce_param(name: str, param_type: str, value: Any) -> Any:
        """Coerce a parameter value to the declared type."""
        if param_type == "int":
            try:
                return int(value)
            except (ValueError, TypeError) as exc:
                raise PipelineParameterError(
                    f"Parameter '{name}' expects int, got {value!r}"
                ) from exc
        if param_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                if value.lower() in ("true", "1", "yes"):
                    return True
                if value.lower() in ("false", "0", "no"):
                    return False
            raise PipelineParameterError(
                f"Parameter '{name}' expects bool, got {value!r}"
            )
        if param_type == "list":
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [v.strip() for v in value.split(",") if v.strip()]
            raise PipelineParameterError(
                f"Parameter '{name}' expects list, got {value!r}"
            )
        # Default: string
        return str(value)

    def _apply_params(self, pipeline: Pipeline, params: dict[str, Any]) -> Pipeline:
        """Walk all string fields and replace {param} placeholders."""
        pattern = re.compile(r"\{(\w+)\}")

        def _replace_str(s: str) -> str:
            def replacer(m: re.Match) -> str:
                key = m.group(1)
                if key in params:
                    return str(params[key])
                return m.group(0)  # Leave unresolved placeholders as-is
            return pattern.sub(replacer, s)

        new_slots = []
        for slot in pipeline.slots:
            new_task = None
            if slot.task:
                new_task = SlotTask(
                    objective=_replace_str(slot.task.objective),
                    context_files=[_replace_str(f) for f in slot.task.context_files],
                    deliverables=[_replace_str(d) for d in slot.task.deliverables],
                    constraints=[_replace_str(c) for c in slot.task.constraints],
                    kpis=[_replace_str(k) for k in slot.task.kpis],
                )
            new_outputs = [
                ArtifactOutput(
                    name=o.name,
                    type=o.type,
                    path=_replace_str(o.path) if o.path else None,
                    validation=o.validation,
                )
                for o in slot.outputs
            ]
            new_slot = Slot(
                id=slot.id,
                slot_type=slot.slot_type,
                name=_replace_str(slot.name),
                inputs=list(slot.inputs),
                outputs=new_outputs,
                pre_conditions=list(slot.pre_conditions),
                post_conditions=list(slot.post_conditions),
                depends_on=list(slot.depends_on),
                task=new_task,
                execution=slot.execution,
            )
            new_slots.append(new_slot)

        return Pipeline(
            id=pipeline.id,
            name=_replace_str(pipeline.name),
            version=pipeline.version,
            description=_replace_str(pipeline.description),
            created_by=pipeline.created_by,
            created_at=pipeline.created_at,
            parameters=list(pipeline.parameters),
            slots=new_slots,
            data_flow=list(pipeline.data_flow),
        )
