> **Note**: This is a project-specific command. See also `/speckit.tasks` for the canonical Spec Kit version.

# /tasks — Split Plan into Trackable Tasks

Convert an implementation plan into a structured task list with dependencies.

## Steps

1. **Read the plan** at the path provided in `$ARGUMENTS` (e.g., `specs/features/{name}.plan.md`). If no path is given, ask the user which plan to split.

2. **For each phase** in the plan, create one or more tasks using `TaskCreate`:
   - **subject**: Imperative, concise (e.g., "Add NL matcher module").
   - **description**: Include the phase goal, specific files to change, and acceptance criteria that this task satisfies.
   - **activeForm**: Present continuous (e.g., "Adding NL matcher module").

3. **Set dependencies** using `TaskUpdate` with `addBlockedBy`:
   - Tasks in Phase N+1 should be blocked by the final task of Phase N.
   - Tasks within the same phase that have internal ordering should also have dependencies set.

4. **Add a final verification task** that is blocked by all implementation tasks. Its description should list all Acceptance Criteria from the spec as a checklist.

5. **Show the task list** to the user using `TaskList` so they can review the breakdown.

## Arguments

- `$ARGUMENTS` — Path to the plan file, or the feature name to look up in `specs/features/`.
