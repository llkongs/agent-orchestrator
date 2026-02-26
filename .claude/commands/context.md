# /context — Show Current Context Layers

Display the L0/L1/L2 context files relevant to the current task or directory.

> **See also**: `/speckit.plan` for spec-driven planning, `/ov-status` for OpenViking health.

## Steps

1. **Identify scope** from `$ARGUMENTS`. This can be:
   - A directory path (e.g., `engineer/`)
   - A task ID (look up the task and determine which modules it touches)
   - If empty, use the current working directory

2. **Check OpenViking availability**:
   - Run `ov health` to check if the OV server is running.
   - If OV is available, use the **OV-powered path** (Step 2a).
   - If OV is unavailable, fall back to the **file-scan path** (Step 2b).

### 2a. OV-Powered Context (when `ov health` succeeds)

   - **L0**: Run `ov abstract viking://agent-orchestrator/` for the project abstract.
   - **L1**: Run `ov ls viking://agent-orchestrator/ -s` to list sub-resources, then `ov overview <uri>` for each relevant resource.
   - **Semantic search**: Run `ov find "$ARGUMENTS" --uri viking://agent-orchestrator --limit 5 -o json` to find semantically relevant resources.
   - **Relations**: Run `ov relations <uri> -o json` to show how resources connect.
   - Print OV results alongside file-scan results for a complete picture.

### 2b. File-Scan Context (fallback)

3. **List L0 context** (always loaded):
   - `CLAUDE.md` — Project entry point and top-level rules
   - `docs/constitution.md` — Inviolable principles
   - `memory/MEMORY.md` — Cross-session knowledge (if exists)
   - Show file paths and whether each file exists.

4. **List L1 context** (loaded on demand for the current scope):
   - `{directory}/*.abstract.md` — Module abstracts
   - `{directory}/*.overview.md` — Module overviews
   - `architect/architecture.md` — System architecture
   - Relevant spec files from `specs/features/`
   - Show file paths, existence status, and line counts.

5. **List L2 context** (deep-dive, loaded only when needed):
   - Source files within the scoped directory
   - Test files
   - Configuration files
   - Show file paths grouped by type.

6. **Print a summary table** with columns: Layer, File, Status (exists/missing), Lines, Source (OV/file-scan).

## Arguments

- `$ARGUMENTS` — Directory path, task ID, or empty for current directory.
