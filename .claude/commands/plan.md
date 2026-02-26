> **Note**: This is a project-specific command. See also `/speckit.plan` for the canonical Spec Kit version.

# /plan — Generate Implementation Plan from Spec

Generate a phased implementation plan from an approved feature spec.

## Steps

1. **Read the spec** at the path provided in `$ARGUMENTS` (e.g., `specs/features/{name}.spec.md`). If no path is given, ask the user which spec to plan.

2. **Read the architecture** at `architect/architecture.md` to understand the current system structure, module boundaries, and conventions.

3. **Read the constitution** at `docs/constitution.md` to ensure the plan complies with all principles.

4. **Create the plan** as `specs/features/{name}.plan.md` with these sections:

   - **Overview**: One paragraph linking back to the spec and summarizing the approach.
   - **Phases**: Break the work into sequential phases. For each phase:
     - Phase name and goal
     - Files to create or modify (with paths)
     - Key implementation details
     - Dependencies on previous phases
   - **File Change Summary**: Table listing every file affected, the type of change (create/modify/delete), and which phase.
   - **Risk & Mitigations**: Known risks and how to handle them.
   - **Testing Strategy**: What tests are needed and where they live.

5. **Verify** that every Acceptance Criterion from the spec is covered by at least one phase.

6. **Present the plan** to the user for approval before proceeding to `/tasks`.

## Arguments

- `$ARGUMENTS` — Path to the spec file, or the feature name to look up in `specs/features/`.
