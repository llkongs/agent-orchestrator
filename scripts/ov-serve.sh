#!/usr/bin/env bash
# OpenViking Server Management
# Usage: ./scripts/ov-serve.sh start|stop|status

OV_BIN="${OV_BIN:-ov}"
OV_PORT="${OV_PORT:-8686}"
OV_PID_FILE="/tmp/ov-serve.pid"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

case "${1:-start}" in
  start)
    if [ -f "$OV_PID_FILE" ] && kill -0 "$(cat $OV_PID_FILE)" 2>/dev/null; then
      echo "OpenViking server already running (PID $(cat $OV_PID_FILE))"
      exit 0
    fi
    echo "Starting OpenViking server on port $OV_PORT..."
    nohup "$OV_BIN" serve --port "$OV_PORT" > /tmp/ov-serve.log 2>&1 &
    echo $! > "$OV_PID_FILE"
    # Wait for health
    for i in $(seq 1 30); do
      if "$OV_BIN" health >/dev/null 2>&1; then
        echo "OpenViking server started (PID $(cat $OV_PID_FILE))"
        exit 0
      fi
      sleep 1
    done
    echo "ERROR: OpenViking server failed to start within 30s"
    exit 1
    ;;
  stop)
    if [ -f "$OV_PID_FILE" ]; then
      kill "$(cat $OV_PID_FILE)" 2>/dev/null
      rm -f "$OV_PID_FILE"
      echo "OpenViking server stopped"
    else
      echo "No PID file found"
    fi
    ;;
  status)
    "$OV_BIN" health 2>/dev/null && echo "OpenViking: running" || echo "OpenViking: not running"
    ;;
  *)
    echo "Usage: $0 {start|stop|status}"
    exit 1
    ;;
esac
