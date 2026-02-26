> **Note**: This is a project-specific command. See also `/speckit.specify` for the canonical Spec Kit version.

# /specify — Create a Feature Specification

Create a feature spec following the Spec-Driven Development methodology.

## Steps

1. **Read the constitution** at `docs/constitution.md`. All specs must comply with it.

2. **Capture the user's original words** verbatim. Paste them into the "User's Original Words" section unchanged. Never paraphrase or compress the user's request.

3. **Copy the template** from `specs/features/_template.spec.md` to `specs/features/{feature-name}.spec.md`. Use kebab-case for the filename.

4. **Fill in every section** of the template:
   - **Objective**: One paragraph summarizing the problem and desired outcome.
   - **User Stories**: At least one "As a [role], I want [action], so that [benefit]".
   - **Functional Requirements**: Numbered FR-1, FR-2, etc. Each must be testable.
   - **Non-Functional Requirements**: Performance, security, or scalability constraints.
   - **In Scope / Out of Scope**: Be explicit to prevent scope creep.
   - **Acceptance Criteria**: Checkboxes. These become the definition of done.
   - **Dependencies**: Other specs, modules, or services required.
   - **Open Questions**: Flag anything ambiguous; do not guess.

5. **Validate** that the spec does not violate any principle in `docs/constitution.md`.

6. **Present the spec** to the user for review before proceeding to `/plan`.

## Arguments

- `$ARGUMENTS` — The feature name or user's description of the feature.
