#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
shellcheck bootstrap.sh scripts/*.sh
shellcheck -s bash home/dot_config/dotfiles-termux/*.sh home/dot_config/dotfiles-termux/shell.bash
zsh -n home/dot_config/dotfiles-termux/shell.zsh
uv run --no-project --with ruff ruff check scripts/host.py scripts/benchmark-shell.py scripts/herdr-shell.py tests --select E9,F63,F7,F82
uv run --no-project python - <<'PY'
import json
from pathlib import Path
for path in Path('config').glob('*.json'):
    json.loads(path.read_text())
PY
