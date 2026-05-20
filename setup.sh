#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT/.live_translator.pid"
LOG_FILE="$ROOT/server.log"
PYTHON="${PYTHON:-python}"

function usage() {
  cat <<EOF
Usage: $0 {build|start|stop|restart|status|update|checkout}

Commands:
  build     Install Python dependencies
  start     Start the LiveTranslator backend in the background
  stop      Stop the running LiveTranslator backend
  restart   Restart the backend
  status    Show running status
  update    Pull repository updates and rebuild dependencies
  checkout  Checkout a git branch on the Linux server, then pull and rebuild
EOF
}

function build() {
  echo "Installing dependencies..."
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -r "$ROOT/requirements.txt"
  echo "Build complete."
}

function start() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "LiveTranslator is already running with PID $(cat "$PID_FILE")."
    exit 0
  fi

  echo "Starting LiveTranslator backend..."
  nohup "$PYTHON" -m backend.server > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 1
  if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "LiveTranslator started with PID $(cat "$PID_FILE")."
    echo "Logs: $LOG_FILE"
  else
    echo "Failed to start LiveTranslator. Check $LOG_FILE for details." >&2
    rm -f "$PID_FILE"
    exit 1
  fi
}

function stop() {
  if [ ! -f "$PID_FILE" ]; then
    echo "No running LiveTranslator instance found."
    exit 0
  fi

  PID="$(cat "$PID_FILE")"
  echo "Stopping LiveTranslator PID $PID..."
  kill "$PID" 2>/dev/null || true
  sleep 1
  if kill -0 "$PID" 2>/dev/null; then
    echo "Force killing LiveTranslator PID $PID..."
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  echo "Stopped."
}

function status() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "LiveTranslator is running with PID $(cat "$PID_FILE")."
  else
    echo "LiveTranslator is not running."
  fi
}

function checkout() {
  local branch="${2:-main}"

  if [ ! -d "$ROOT/.git" ]; then
    echo "Error: $ROOT is not a git repository."
    exit 1
  fi

  echo "Checking out branch '$branch'..."
  git -C "$ROOT" fetch --all --prune

  if git -C "$ROOT" rev-parse --verify "$branch" >/dev/null 2>&1; then
    git -C "$ROOT" checkout "$branch"
  else
    git -C "$ROOT" checkout -B "$branch" "origin/$branch" || git -C "$ROOT" checkout "$branch"
  fi

  git -C "$ROOT" pull --ff-only
  echo "Branch '$branch' is now checked out."

  if [ -f "$ROOT/requirements.txt" ]; then
    build
  fi
}

function update() {
  echo "Updating repository and dependencies..."
  if [ -d "$ROOT/.git" ]; then
    git -C "$ROOT" pull --ff-only || true
  fi
  build
}

COMMAND="${1:-help}"
case "$COMMAND" in
  build) build ;;
  start) start ;;
  stop) stop ;;
  restart) stop && start ;;
  status) status ;;
  update) update ;;
  checkout) checkout "$@" ;;
  help|*) usage ;;
esac  build) build ;;
  start) start ;;
  stop) stop ;;
  restart) stop && start ;;
  status) status ;;
  update) update ;;
  help|*) usage ;;
esac
