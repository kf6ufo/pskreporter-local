#!/bin/sh

set -eu

project_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
python_path="$project_dir/.venv/bin/python"

if [ ! -x "$python_path" ]; then
    echo "Error: .venv is missing. Follow the setup steps in README.md first." >&2
    exit 1
fi

cd "$project_dir"

exec "$python_path" -m uvicorn \
    pskreporter_local.app:app \
    --host 127.0.0.1 \
    --port 8765 \
    --reload
