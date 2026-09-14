#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
VENV_PYTHON="$(pwd)/.venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
  exec "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

echo "Could not find AI service virtual environment at $VENV_PYTHON"
echo "Falling back to system Python."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
