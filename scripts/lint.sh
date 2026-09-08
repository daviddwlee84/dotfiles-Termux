#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
shellcheck bootstrap.sh scripts/*.sh
uv run --no-project --with ruff ruff check scripts/host.py tests --select E9,F63,F7,F82
uv run --no-project python - <<'PY'
import json
from pathlib import Path
for path in Path('config').glob('*.json'):
    json.loads(path.read_text())
PY
