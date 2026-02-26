"""Pipeline Engine CLI — lets Claude Code drive the engine across Bash calls.

State persists on disk between invocations.  A session file tracks the
active pipeline so subsequent commands don't need to re-specify it.

Usage:
    # Set the alias (or put in CLAUDE.md / .bashrc)
    alias pipeline="PYTHONPATH=/path/to/engineer/src python3 -m pipeline.cli"

    # Workflow
    pipeline --project /path/to/project templates
    pipeline --project /path/to/project prepare standard-feature.yaml -p feature_name=login
    pipeline status
    pipeline next
    pipeline begin slot-design
    # ... Claude does the work ...
    pipeline complete slot-design
    pipeline next
    pipeline begin slot-implement
    # ... Claude does the work ...
    pipeline complete slot-implement
    pipeline summary
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from pipeline.runner import PipelineRunner
from pipeline.nl_matcher import NLMatcher
from pipeline.slot_registry import SlotRegistry

# Session file — tracks active pipeline so subsequent calls find it
_SESSION_FILENAME = ".pipeline-session.json"

# Default directory layout
_DEFAULTS = {
    "templates_dir": "specs/pipelines/templates",
    "state_dir": "state/active",
    "slot_types_dir": "specs/pipelines/slot-types",
    "agents_dir": "agents",
}


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

def _session_path(state_dir: str) -> Path:
    return Path(state_dir) / _SESSION_FILENAME


def _global_session_path() -> Path:
    """Session file in the engine's own directory — always findable."""
    return Path(__file__).parent / _SESSION_FILENAME


def _save_session(state_dir: str, state_file: str, project_root: str) -> None:
    data = {"state_file": state_file, "project_root": project_root}
    content = json.dumps(data)
    # Save in project's state dir
    path = _session_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    # Also save in engine dir (so commands without --project can find it)
    _global_session_path().write_text(content)


def _load_session(state_dir: str | None = None) -> dict:
    """Load session from state_dir, engine dir, or cwd."""
    candidates = []
    if state_dir:
        candidates.append(_session_path(state_dir))
    candidates.append(_global_session_path())
    candidates.append(Path(_DEFAULTS["state_dir"]) / _SESSION_FILENAME)

    for p in candidates:
        if p.exists():
            return json.loads(p.read_text())

    return {}


# ---------------------------------------------------------------------------
# Runner factory
# ---------------------------------------------------------------------------

def _make_runner(project_root: str) -> PipelineRunner:
    root = Path(project_root).resolve()
    return PipelineRunner(
        project_root=str(root),
        templates_dir=str(root / _DEFAULTS["templates_dir"]),
        state_dir=str(root / _DEFAULTS["state_dir"]),
        slot_types_dir=str(root / _DEFAULTS["slot_types_dir"]),
        agents_dir=str(root / _DEFAULTS["agents_dir"]),
    )


def _resolve_project(args) -> str:
    """Get project_root from args or session."""
    if args.project:
        return str(Path(args.project).resolve())

    session = _load_session()
    if session.get("project_root"):
        return session["project_root"]

    # Fallback: cwd
    return str(Path.cwd())


def _resume(runner: PipelineRunner, state_file: str):
    """Resume pipeline + state from a state file."""
    return runner.resume(state_file)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_templates(args):
    """List available pipeline templates."""
    project_root = _resolve_project(args)
    root = Path(project_root)
    t_dir = root / _DEFAULTS["templates_dir"]

    if not t_dir.exists():
        print(f"No templates directory: {t_dir}")
        return 1

    templates = sorted(t_dir.glob("*.yaml"))
    if not templates:
        print(f"No templates found in {t_dir}")
        return 1

    print(f"Available templates ({len(templates)}):\n")
    for t in templates:
        # Quick parse to get id + description
        import yaml
        try:
            data = yaml.safe_load(t.read_text())
            p = data.get("pipeline", {})
            pid = p.get("id", t.stem)
            name = p.get("name", "")
            desc = p.get("description", "")
            slots = p.get("slots", [])
            print(f"  {t.name}")
            print(f"    ID: {pid}  |  {name}")
            if desc:
                print(f"    {desc}")
            print(f"    Slots: {len(slots)}")
            print()
        except Exception:
            print(f"  {t.name}  (parse error)")
    return 0


def cmd_match(args):
    """Match natural language to a template."""
    project_root = _resolve_project(args)
    root = Path(project_root)
    t_dir = str(root / _DEFAULTS["templates_dir"])

    text = " ".join(args.text)
    matcher = NLMatcher(t_dir)
    matches = matcher.match(text)

    if not matches:
        print(f"No template matched: {text!r}")
        return 1

    print(f"Matches for: {text!r}\n")
    for m in matches:
        print(f"  Template: {m.template_id}")
        print(f"  Confidence: {m.confidence:.2f}")
        print(f"  Path: {m.template_path}")
        if m.suggested_params:
            print(f"  Params: {m.suggested_params}")
        print()
    return 0


def cmd_prepare(args):
    """Create a new pipeline instance from a template."""
    project_root = _resolve_project(args)
    root = Path(project_root)
    runner = _make_runner(project_root)

    # Resolve template path
    template = args.template
    template_path = Path(template)
    if not template_path.is_absolute():
        # Try relative to templates dir
        candidate = root / _DEFAULTS["templates_dir"] / template
        if candidate.exists():
            template_path = candidate
        elif (root / template).exists():
            template_path = root / template
        else:
            print(f"Template not found: {template}")
            print(f"  Tried: {candidate}")
            print(f"  Tried: {root / template}")
            return 1

    # Parse -p key=value params
    params = {}
    if args.param:
        for p in args.param:
            if "=" not in p:
                print(f"Invalid param format (expected key=value): {p}")
                return 1
            k, v = p.split("=", 1)
            params[k] = v

    pipeline, state = runner.prepare(str(template_path), params)

    # Find the state file (most recent in state_dir)
    state_dir = str(root / _DEFAULTS["state_dir"])
    state_files = sorted(
        Path(state_dir).glob(f"{pipeline.id}*.state.yaml"),
        key=lambda f: f.stat().st_mtime,
    )
    state_file = str(state_files[-1]) if state_files else ""

    # Save session
    _save_session(state_dir, state_file, project_root)

    print(f"Pipeline created: {pipeline.id} v{pipeline.version}")
    print(f"  Name: {pipeline.name}")
    print(f"  Slots: {len(pipeline.slots)}")
    print(f"  State: {state_file}")
    print(f"\nSlots:")
    for slot in pipeline.slots:
        deps = f" (depends: {', '.join(slot.depends_on)})" if slot.depends_on else ""
        task_obj = slot.task.objective if slot.task else ""
        print(f"  [{slot.id}] {slot.name} ({slot.slot_type}){deps}")
        if task_obj:
            print(f"    Task: {task_obj}")
    print(f"\nRun 'pipeline next' to see ready slots.")
    return 0


def _get_active(args):
    """Load the active pipeline and state from session."""
    project_root = _resolve_project(args)
    state_dir = str(Path(project_root) / _DEFAULTS["state_dir"])
    session = _load_session(state_dir)

    state_file = args.state_file if hasattr(args, "state_file") and args.state_file else None
    if not state_file:
        state_file = session.get("state_file")

    if not state_file:
        print("No active pipeline. Run 'pipeline prepare <template>' first.")
        sys.exit(1)

    if not Path(state_file).exists():
        print(f"State file not found: {state_file}")
        sys.exit(1)

    runner = _make_runner(project_root)
    pipeline, state = _resume(runner, state_file)
    return runner, pipeline, state, state_file, state_dir


def cmd_status(args):
    """Show current pipeline status."""
    runner, pipeline, state, state_file, _ = _get_active(args)

    print(f"Pipeline: {pipeline.id} v{pipeline.version}")
    print(f"Status: {state.status.value}")
    print(f"State file: {state_file}")
    print()

    # Count by status
    status_counts = {}
    for ss in state.slots.values():
        status_counts[ss.status.value] = status_counts.get(ss.status.value, 0) + 1

    for s, c in sorted(status_counts.items()):
        print(f"  {s}: {c}")

    print(f"\n  Total: {len(state.slots)} slots")
    return 0


def cmd_next(args):
    """Show slots ready for execution."""
    runner, pipeline, state, _, _ = _get_active(args)
    ready = runner.get_next_slots(pipeline, state)

    if not ready:
        # Check if pipeline is done
        from pipeline.models import PipelineStatus
        if state.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED):
            print(f"Pipeline {state.status.value}. No more slots to execute.")
        else:
            print("No slots ready. Check 'pipeline status' for details.")
        return 0

    print(f"Ready slots ({len(ready)}):\n")
    for slot in ready:
        task_obj = slot.task.objective if slot.task else "N/A"
        print(f"  [{slot.id}] {slot.name}")
        print(f"    Type: {slot.slot_type}")
        print(f"    Task: {task_obj}")
        if slot.task and slot.task.deliverables:
            print(f"    Deliverables:")
            for d in slot.task.deliverables:
                print(f"      - {d}")
        print()

    print("Run 'pipeline begin <slot_id>' to start working on a slot.")
    return 0


def cmd_begin(args):
    """Begin working on a slot."""
    runner, pipeline, state, state_file, state_dir = _get_active(args)
    slot_id = args.slot_id

    # Find the slot object
    slot = None
    for s in pipeline.slots:
        if s.id == slot_id:
            slot = s
            break

    if slot is None:
        print(f"Slot not found: {slot_id}")
        print(f"Available: {[s.id for s in pipeline.slots]}")
        return 1

    state = runner.begin_slot(slot, pipeline, state)
    slot_state = state.slots[slot_id]

    if slot_state.status.value == "failed":
        print(f"Slot {slot_id} FAILED to start: {slot_state.error}")
        return 1

    print(f"Slot started: {slot_id}")
    print(f"  Status: {slot_state.status.value}")
    if slot.task:
        print(f"  Objective: {slot.task.objective}")
        if slot.task.deliverables:
            print(f"  Deliverables:")
            for d in slot.task.deliverables:
                print(f"    - {d}")
    if slot.inputs:
        print(f"  Inputs:")
        for inp in slot.inputs:
            print(f"    - {inp.artifact_id} ({inp.artifact_type})")
    if slot.outputs:
        print(f"  Expected outputs:")
        for out in slot.outputs:
            print(f"    - {out.artifact_id} ({out.artifact_type}): {out.path}")

    print(f"\nDo the work, then run 'pipeline complete {slot_id}'.")
    return 0


def cmd_complete(args):
    """Mark a slot as completed."""
    runner, pipeline, state, state_file, _ = _get_active(args)
    slot_id = args.slot_id

    if slot_id not in state.slots:
        print(f"Slot not found: {slot_id}")
        return 1

    state = runner.complete_slot(slot_id, pipeline, state)
    slot_state = state.slots[slot_id]

    if slot_state.status.value == "failed":
        print(f"Slot {slot_id} post-conditions FAILED: {slot_state.error}")
        return 1

    print(f"Slot completed: {slot_id}")
    print(f"  Pipeline status: {state.status.value}")

    # Show what's next
    ready = runner.get_next_slots(pipeline, state)
    if ready:
        print(f"\n  Next ready: {[s.id for s in ready]}")
    else:
        from pipeline.models import PipelineStatus
        if state.status == PipelineStatus.COMPLETED:
            print(f"\n  All slots done! Pipeline COMPLETED.")
        else:
            print(f"\n  No more ready slots.")
    return 0


def cmd_fail(args):
    """Mark a slot as failed."""
    runner, pipeline, state, state_file, _ = _get_active(args)
    slot_id = args.slot_id
    error = " ".join(args.error)

    if slot_id not in state.slots:
        print(f"Slot not found: {slot_id}")
        return 1

    state = runner.fail_slot(slot_id, error, state)
    print(f"Slot failed: {slot_id}")
    print(f"  Error: {error}")
    print(f"  Pipeline status: {state.status.value}")
    return 0


def cmd_skip(args):
    """Skip a slot."""
    runner, pipeline, state, state_file, _ = _get_active(args)
    slot_id = args.slot_id

    if slot_id not in state.slots:
        print(f"Slot not found: {slot_id}")
        return 1

    state = runner.skip_slot(slot_id, state)
    print(f"Slot skipped: {slot_id}")
    print(f"  Pipeline status: {state.status.value}")

    ready = runner.get_next_slots(pipeline, state)
    if ready:
        print(f"  Next ready: {[s.id for s in ready]}")
    return 0


def cmd_summary(args):
    """Human-readable pipeline summary."""
    runner, pipeline, state, _, _ = _get_active(args)
    print(runner.get_summary(state))
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Pipeline Engine CLI — drive the engine from the command line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Workflow:
              pipeline --project ./my-project templates
              pipeline --project ./my-project prepare standard-feature.yaml -p feature_name=login
              pipeline next
              pipeline begin slot-design
              # ... do the work ...
              pipeline complete slot-design
              pipeline summary
        """),
    )
    parser.add_argument(
        "--project", "-P",
        help="Project root directory (saved in session after first use).",
    )

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # templates
    sub.add_parser("templates", help="List available pipeline templates")

    # match
    p_match = sub.add_parser("match", help="Match natural language to a template")
    p_match.add_argument("text", nargs="+", help="Natural language request")

    # prepare
    p_prep = sub.add_parser("prepare", help="Create a pipeline instance from a template")
    p_prep.add_argument("template", help="Template filename or path")
    p_prep.add_argument("-p", "--param", action="append", help="Parameter key=value")

    # status
    sub.add_parser("status", help="Show current pipeline status")

    # next
    sub.add_parser("next", help="Show slots ready for execution")

    # begin
    p_begin = sub.add_parser("begin", help="Begin working on a slot")
    p_begin.add_argument("slot_id", help="Slot ID to begin")

    # complete
    p_comp = sub.add_parser("complete", help="Mark a slot as completed")
    p_comp.add_argument("slot_id", help="Slot ID to complete")

    # fail
    p_fail = sub.add_parser("fail", help="Mark a slot as failed")
    p_fail.add_argument("slot_id", help="Slot ID that failed")
    p_fail.add_argument("error", nargs="+", help="Error message")

    # skip
    p_skip = sub.add_parser("skip", help="Skip a slot")
    p_skip.add_argument("slot_id", help="Slot ID to skip")

    # summary
    sub.add_parser("summary", help="Human-readable pipeline summary")

    return parser


_COMMANDS = {
    "templates": cmd_templates,
    "match": cmd_match,
    "prepare": cmd_prepare,
    "status": cmd_status,
    "next": cmd_next,
    "begin": cmd_begin,
    "complete": cmd_complete,
    "fail": cmd_fail,
    "skip": cmd_skip,
    "summary": cmd_summary,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args) or 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
