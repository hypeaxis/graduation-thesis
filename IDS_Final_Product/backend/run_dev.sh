#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
  echo "Missing .venv at $PROJECT_ROOT/.venv"
  exit 1
fi

source "$PROJECT_ROOT/.venv/bin/activate"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
