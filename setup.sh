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
  uninstall  Remove virtualenv and build artifacts
EOF
}

function uninstall() {
  VENV_DIR="${VENV_DIR:-$ROOT/.venv}"

  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Stopping running backend..."
    stop || true
  fi

  echo "This will remove the virtualenv at $VENV_DIR and temporary build files."
  read -p "Proceed and remove $VENV_DIR? [y/N] " ans || ans="n"
  case "$ans" in
    [Yy]* )
      rm -rf "$VENV_DIR"
      rm -f "$ROOT/.requirements_core.txt" "$PID_FILE" "$LOG_FILE"
      echo "Removed virtualenv and temp files."

      read -p "Also remove downloaded model caches (huggingface, ctranslate2, whisper.cpp, local models/) ? [y/N] " rmcache || rmcache="n"
      case "$rmcache" in
        [Yy]* )
          echo "Removing common model/cache directories..."
          rm -rf "$HOME/.cache/huggingface" \
                 "$HOME/.cache/ctranslate2" \
                 "$HOME/.ctranslate2" \
                 "$HOME/.cache/whisper.cpp" \
                 "$ROOT/models" \
                 "$ROOT/model" || true
          echo "Model caches removed (where present)."
          ;;
        *)
          echo "Skipped removing model caches."
          ;;
      esac
      echo "Uninstall complete."
      ;;
    *)
      echo "Aborted uninstall."
      ;;
  esac
}

function build() {
  echo "Installing dependencies..."
  VENV_DIR="${VENV_DIR:-$ROOT/.venv}"
  if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtualenv at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
  fi
  VENV_PYTHON="$VENV_DIR/bin/python"
  PYTHON="$VENV_PYTHON"
  echo "Using Python: $PYTHON"
  "$PYTHON" -m pip install --upgrade pip
  # Install core requirements first, treat whispercpp as optional because it
  # may not have wheels for all platforms.
  if grep -q '^whispercpp' "$ROOT/requirements.txt" 2>/dev/null; then
    CORE_REQS="$ROOT/.requirements_core.txt"
    grep -v '^whispercpp' "$ROOT/requirements.txt" > "$CORE_REQS"
    "$PYTHON" -m pip install -r "$CORE_REQS"
    echo "Attempting optional install of whispercpp (may fail on some platforms)..."
    "$PYTHON" -m pip install whispercpp || echo "Optional whispercpp install failed; continuing without it."
    rm -f "$CORE_REQS"
  else
    "$PYTHON" -m pip install -r "$ROOT/requirements.txt"
  fi
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
  uninstall) uninstall ;;
  checkout) checkout "$@" ;;
  help|*) usage ;;
esac
