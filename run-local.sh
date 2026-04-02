#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXE="$ROOT_DIR/.venv/Scripts/python.exe"

if [[ ! -x "$PYTHON_EXE" ]]; then
  echo "Missing virtualenv Python at .venv/Scripts/python.exe"
  echo "Run this from the project root after creating the local venv."
  exit 1
fi

if [[ -f "$ROOT_DIR/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.local"
  set +a
fi

export HTTP_PROXY=
export HTTPS_PROXY=
export ALL_PROXY=
export GIT_HTTP_PROXY=
export GIT_HTTPS_PROXY=

"$PYTHON_EXE" -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('model ready')"
"$PYTHON_EXE" -m uvicorn app.main:app --reload
