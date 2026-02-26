#!/usr/bin/env bash
# OpenViking Resource Bootstrap for Agent Orchestrator
# Idempotent - safe to re-run

set -euo pipefail
OV_BIN="${OV_BIN:-ov}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Checking OpenViking server ==="
if ! "$OV_BIN" health >/dev/null 2>&1; then
  echo "OpenViking server not running. Starting..."
  bash scripts/ov-serve.sh start
fi

echo "=== Registering project resources ==="

# Create root namespace
"$OV_BIN" mkdir viking://agent-orchestrator 2>/dev/null || true

# Register directories
echo "Registering pipeline engine..."
"$OV_BIN" add-resource "$PROJECT_ROOT/engineer/src/pipeline/" \
  --to viking://agent-orchestrator/pipeline \
  --reason "Pipeline engine - 12 modules, core context" --wait 2>/dev/null || true

echo "Registering specs..."
"$OV_BIN" add-resource "$PROJECT_ROOT/specs/" \
  --to viking://agent-orchestrator/specs \
  --reason "Specifications - templates, slot-types, protocols" --wait 2>/dev/null || true

echo "Registering agents..."
"$OV_BIN" add-resource "$PROJECT_ROOT/agents/" \
  --to viking://agent-orchestrator/agents \
  --reason "Agent prompts with capability metadata" --wait 2>/dev/null || true

echo "Registering architect..."
"$OV_BIN" add-resource "$PROJECT_ROOT/architect/" \
  --to viking://agent-orchestrator/architect \
  --reason "Architecture documents and design decisions" --wait 2>/dev/null || true

echo "Registering constitution..."
"$OV_BIN" add-resource "$PROJECT_ROOT/constitution.md" \
  --to viking://agent-orchestrator/constitution \
  --reason "Project constitution - inviolable rules" --wait 2>/dev/null || true

echo "Registering CLAUDE.md..."
"$OV_BIN" add-resource "$PROJECT_ROOT/CLAUDE.md" \
  --to viking://agent-orchestrator/claude-md \
  --reason "Project entry point - L0 context" --wait 2>/dev/null || true

echo "=== Establishing relationships ==="

"$OV_BIN" link viking://agent-orchestrator/pipeline \
  viking://agent-orchestrator/specs \
  --reason "Pipeline engine implements spec-defined slot types and templates" 2>/dev/null || true

"$OV_BIN" link viking://agent-orchestrator/agents \
  viking://agent-orchestrator/specs \
  --reason "Agents declare capabilities matching slot type requirements" 2>/dev/null || true

"$OV_BIN" link viking://agent-orchestrator/constitution \
  viking://agent-orchestrator/pipeline \
  viking://agent-orchestrator/specs \
  viking://agent-orchestrator/agents \
  --reason "Constitution governs all project artifacts" 2>/dev/null || true

echo "=== Verifying ==="
"$OV_BIN" ls viking://agent-orchestrator/ 2>/dev/null || echo "WARNING: Could not list resources"

echo "=== Bootstrap complete ==="
