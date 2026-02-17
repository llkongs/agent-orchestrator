# Teammate Resume Mechanism - Deep Technical Investigation

**Researcher**: researcher-opus (Opus 4.6)
**Date**: 2026-02-17
**Claude Code Version**: 2.1.44
**Verdict**: **TEAMMATES CANNOT BE RESUMED. This is by design, not a bug.**

---

## Executive Summary

After analyzing the Claude Code source code (`cli.js`, 11.5MB minified), file system structure, official documentation, and the actual runtime behavior, the conclusion is **definitive and unambiguous**:

**The `resume` parameter in the Task tool ONLY works for subagents. It is architecturally impossible for it to work for teammates.**

This is not a missing feature or an oversight. The teammate spawn path and the subagent resume path are completely separate code branches that never intersect. The `resume` parameter is checked at byte position 8,224,855 in the source code; the teammate return statement is at byte position 8,223,634 -- the resume check is literally unreachable when spawning teammates.

---

## 1. Source Code Analysis (Primary Evidence)

Source file: `/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js` (v2.1.44)

### 1.1 The Task Tool's `call()` Method

The Task tool (`$P1`) has a single `call()` method. The code branches early based on whether `team_name` and `name` are provided:

```javascript
// Deminified from cli.js with original variable names added:
async call({ prompt, subagent_type, description, model,
             resume,          // <-- z in minified code
             run_in_background, max_turns,
             name,            // <-- $ in minified code
             team_name, mode }, toolUseContext, ...) {

  let teamName = team_name || appState.teamContext?.teamName;  // G

  // === BRANCH 1: TEAMMATE PATH ===
  // If team_name AND name are provided, spawn teammate and return immediately
  if (teamName && name) {                             // if(G&&$)
    let result = await JU4({name, prompt, ...});      // spawnTeammate()
    return { data: { status: "teammate_spawned", prompt, ...result.data } };
    // ^^^ RETURNS HERE.
    // The 'resume' variable is NEVER checked in this path.
  }

  // === BRANCH 2: SUBAGENT PATH ===
  // Only reached when spawning subagents (no name/team_name)
  // ... (1,221 bytes later in the source code)

  let transcriptMessages;
  if (resume) {                   // <-- Only checked HERE, in subagent path
    let task = appState.tasks[resume];
    if (task && task.status === "running")
      throw Error(`Cannot resume agent ${resume}: it is still running.`);
    let transcript = await WG1(pZ(resume));
    if (!transcript)
      throw Error(`No transcript found for agent ID: ${resume}`);
    transcriptMessages = WU1(GU1(fG6(transcript)));
  }
  // ... proceed with subagent execution using loaded transcript
}
```

**Proof**: The `teammate_spawned` return is at file position 8,223,634. The `if(resume)` check is at position 8,224,855. **The resume check comes 1,221 bytes AFTER the teammate return.** It is unreachable code when spawning teammates.

### 1.2 Transcript File Path Construction

When the Task tool resumes a subagent, it calls:
```javascript
let transcript = await WG1(pZ(agentId));
```

Where:
- `pZ(A)` is an identity function: `function pZ(A) { return A }` -- passes agentId through unchanged
- `WG1(agentId)` reads the transcript by building a file path via `ah(agentId)`:

```javascript
function ah(agentId) {
  let projectDir = vJ(wV1);    // → ~/.claude/projects/-root/
  let sessionId = g6();          // → CURRENT session's UUID (e.g., "75d445c4-...")
  return BF(projectDir, sessionId, "subagents", `agent-${agentId}.jsonl`);
}
// Result: ~/.claude/projects/-root/<currentSessionId>/subagents/agent-<agentId>.jsonl
```

**Critical constraint**: `g6()` returns the CURRENT session ID. Resume can only find transcripts in the CURRENT session's subagents directory. If you start a new session, it looks in a different directory.

### 1.3 Agent ID Formats Are Incompatible

| Entity | ID Format | Example | Where Created | Where Stored |
|--------|-----------|---------|---------------|-------------|
| Teammate | `name@team` | `hr@agent-orchestrator` | `WE(name, team)` | `~/.claude/teams/<team>/config.json` |
| Subagent transcript | `a` + 7 hex chars | `a7186dc` | `Dd("in_process_teammate")` | `~/.claude/projects/-root/<session>/subagents/agent-a7186dc.jsonl` |

The `WG1` function searches for `agent-<agentId>.jsonl`. If you passed `hr@agent-orchestrator`, it would look for `agent-hr@agent-orchestrator.jsonl` which does not exist and never will.

### 1.4 In-Process Teammates DO Write Transcripts, But With Different IDs

In-process teammates produce transcript files in the leader's `subagents/` directory, but with randomly generated `a`+hex IDs:

```
# My (researcher-opus) actual transcript file:
~/.claude/projects/-root/75d445c4-.../subagents/agent-a7186dc.jsonl
# agentId in file: "a7186dc"

# But my teammate ID in config.json:
"agentId": "researcher-opus@agent-orchestrator"
```

**The mapping from teammate ID to transcript ID is NOT stored anywhere persistent.** It only exists transiently in `AppState.tasks` during the session. When the session ends, this mapping is lost forever.

### 1.5 Teammate Spawn Functions Never Accept Resume

The spawn chain: `JU4` → `bCY` (in-process) → `lW1`:

```javascript
async function lW1(A, q) {
  // A = {name, teamName, prompt, color, planModeRequired, model}
  // ^^^ NO resume parameter
  let agentId = WE(name, teamName);   // Always creates "name@team" format
  let taskId = Dd("in_process_teammate");  // Always generates NEW random ID
  // ... creates fresh AbortController, fresh task, fresh context every time
}
```

There is no code path that loads previous teammate state during spawn.

---

## 2. File System Evidence

### 2.1 Verified Directory Structure

```
~/.claude/
  projects/-root/
    75d445c4-2bcf-4055-95ad-d7df65d8923b/         # agent-orchestrator leader session
      subagents/                                     # 232 transcript files
        agent-a7186dc.jsonl   (this agent, researcher-opus)
        agent-aa36991.jsonl   (hr-opus teammate)
        agent-a32fccc.jsonl   (hr-writer teammate)
        agent-ad80ab0.jsonl   (researcher teammate)
        ...
      tool-results/
    24486be4-dcd9-4e48-9a85-6219b050e1ea/         # crypto-trading leader session
      subagents/                                     # 626 transcript files
  teams/
    agent-orchestrator/
      config.json              # Team config with name@team IDs
      inboxes/
    crypto-trading/
      config.json
      inboxes/
  tasks/                       # Persists across sessions
```

### 2.2 Transcript File Format (NDJSON)

Each line is a timestamped JSON message:
```json
{
  "parentUuid": "218134ba-...",
  "isSidechain": true,
  "agentId": "a02daf5",
  "sessionId": "75d445c4-...",
  "slug": "greedy-stirring-liskov",
  "type": "user",
  "message": {"role": "user", "content": "..."},
  "uuid": "d3d052da-...",
  "timestamp": "2026-02-16T18:07:23.453Z"
}
```

Note: `agentId` is `"a02daf5"` (subagent-style), NOT `"hr@agent-orchestrator"` (teammate-style).

### 2.3 Team Config Has No Transcript ID Mapping

```json
{
  "name": "agent-orchestrator",
  "leadSessionId": "75d445c4-2bcf-4055-95ad-d7df65d8923b",
  "members": [
    {
      "agentId": "hr@agent-orchestrator",
      "name": "hr",
      "backendType": "in-process",
      "tmuxPaneId": "in-process"
      // NO field for transcript file ID (a+hex)
    }
  ]
}
```

---

## 3. Official Documentation Confirmation

From [Claude Code Agent Teams Documentation](https://code.claude.com/docs/en/agent-teams), Limitations section:

> **No session resumption with in-process teammates**: `/resume` and `/rewind` do not restore in-process teammates. After resuming a session, the lead may attempt to message teammates that no longer exist. If this happens, tell the lead to spawn new teammates.

This is explicitly documented as a known limitation of the experimental feature.

---

## 4. Why the Task Tool Description is Misleading

The Task tool's system prompt says:

> "Agents can be resumed using the `resume` parameter by passing the agent ID from a previous invocation. When resumed, the agent continues with its full previous context preserved."

This is **technically accurate but contextually misleading**:

1. **"Agents"** means **subagents** (spawned via Task tool WITHOUT `name`/`team_name`).
2. The "agent ID" is the `a`+hex ID returned by subagent completion (e.g., `a7186dc`), NOT the teammate ID (e.g., `hr@agent-orchestrator`).
3. When a **subagent** completes, the leader receives: `agentId: a7186dc (for resuming)`.
4. When a **teammate** is spawned, the leader receives: `agent_id: hr@agent-orchestrator` -- a completely different format that CANNOT be used for resume.
5. The resume code path is physically unreachable when the teammate code path is taken (see Section 1.1).

---

## 5. Could Resume Theoretically Be Hacked to Work?

### What you'd need:
1. Obtain the `a`+hex transcript ID for a specific teammate (not exposed anywhere)
2. Stay in the same leader session (because `ah()` uses current session ID)
3. Pass this ID as `resume` parameter to Task tool WITHOUT `name`/`team_name` (otherwise you hit the teammate branch)

### Why it still won't work:
1. **No team context**: The resumed subagent would NOT have teammate capabilities -- no mailbox, no task list, no team membership. It would be a plain subagent.
2. **Session scoping**: If the leader session changed, transcripts are in the old session's directory.
3. **Context compaction**: Teammates compact their history when it grows large. Transcripts may not contain full uncompacted state.
4. **Teammate-specific message handling**: The `HCY` runner function sets up `tK6` (teammate context), mailbox monitoring, idle notifications, plan mode, etc. A resumed subagent would have none of this.

---

## 6. What Persists Across Sessions

| Component | Persists? | Location | Usable for Resume? |
|-----------|-----------|----------|-------------------|
| Task list | Yes | `~/.claude/tasks/<team>/` | N/A (coordination, not context) |
| Team config | Yes | `~/.claude/teams/<team>/config.json` | Contains prompts for re-spawning |
| Transcripts | Yes (30 days) | `~/.claude/projects/-root/<session>/subagents/` | Audit only, not for resume |
| Message inboxes | Yes | `~/.claude/teams/<team>/inboxes/` | History only |
| MEMORY.md | Yes | `~/.claude/projects/-root/memory/` | Manual context transfer |

---

## 7. Definitive Conclusion

### Can teammates be resumed after shutdown? **NO.**

| # | Reason | Evidence Type |
|---|--------|--------------|
| 1 | `resume` parameter is unreachable in teammate code path | Source code: return at pos 8,223,634 vs resume at pos 8,224,855 |
| 2 | Teammate IDs (`name@team`) don't match transcript files (`agent-a<hex>.jsonl`) | File system inspection |
| 3 | Transcript lookup is scoped to current session ID | Source: `ah()` uses `g6()` |
| 4 | No persistent mapping from teammate ID to transcript ID | Team config inspection |
| 5 | Spawn functions don't accept resume parameter | Source: `bCY()`, `ICY()`, `lW1()` |
| 6 | Official docs explicitly state this | https://code.claude.com/docs/en/agent-teams |

### What the CEO should do instead:

1. **Accept that teammate state is ephemeral** -- this is by design, not a bug.
2. **When rebuilding team**: spawn fresh teammates with detailed context in spawn prompts. Use prompts from `config.json` and add context summaries from MEMORY.md / agent work directories.
3. **Use persistent storage** (files, MEMORY.md, task lists, git) for state that must survive sessions.
4. **Use historian/PMO agents** to maintain organizational memory in files, not in agent context windows.
5. **Task lists auto-reload** from `~/.claude/tasks/<team>/` -- this is the one piece of coordination state that survives.

---

## Appendix: Key Source Code Functions

| Minified Name | Purpose | Key Behavior |
|---------------|---------|-------------|
| `$P1.call()` | Task tool entry point | Branches on `name`+`team_name` presence |
| `JU4` | Spawn teammate (router) | No resume parameter |
| `bCY` | In-process teammate spawn | Creates fresh context |
| `lW1` | In-process teammate launcher | Generates new random `a`+hex ID |
| `$G6` / `HCY` | In-process teammate runner | Sets up team context, mailbox, idle loop |
| `WG1` | Read subagent transcript | Builds path from current session ID |
| `ah` | Build transcript file path | `<project>/<sessionId>/subagents/agent-<id>.jsonl` |
| `pZ` | Identity function | `return A` -- agentId passthrough |
| `WE` | Build teammate ID | `return name@team` |
| `Dd` | Generate task/transcript ID | `a` + 6 random hex chars |
| `g6` | Get current session ID | Session-scoped, changes on new session |

---

## Sources

1. [Orchestrate teams of Claude Code sessions - Official Docs](https://code.claude.com/docs/en/agent-teams)
2. [How to Set Up and Use Claude Code Agent Teams | Medium](https://darasoba.medium.com/how-to-set-up-and-use-claude-code-agent-teams-and-actually-get-great-results-9a34f8648f6d)
3. [Claude Code Agent Teams: Multi-Session Orchestration](https://claudefa.st/blog/guide/agents/agent-teams)
4. [AddyOsmani.com - Claude Code Swarms](https://addyosmani.com/blog/claude-code-agent-teams/)
5. [From Tasks to Swarms: Agent Teams in Claude Code](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/)
6. Source code analysis: `/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js` (v2.1.44, 11.5MB)
7. File system inspection: `~/.claude/projects/-root/`, `~/.claude/teams/`

---

**End of Report**
