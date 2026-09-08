set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
root := justfile_directory()

default:
    @just --list

# Host commands (macOS/Linux); no Android mutation until explicit setup.
[positional-arguments]
host-deps *ARGS:
    bash "{{root}}/scripts/host-deps.sh" "$@"

[positional-arguments]
devices *ARGS:
    uv run --script "{{root}}/scripts/host.py" devices "$@"

[positional-arguments]
setup *ARGS:
    uv run --script "{{root}}/scripts/host.py" setup "$@"

[positional-arguments]
ssh *ARGS:
    uv run --script "{{root}}/scripts/host.py" ssh "$@"

[positional-arguments]
doctor *ARGS:
    uv run --script "{{root}}/scripts/host.py" doctor "$@"

# Target commands: validated native Termux environment required.
[positional-arguments]
apply *ARGS:
    bash "{{root}}/bootstrap.sh" --config-only "$@"

diff:
    bash "{{root}}/bootstrap.sh" --dry-run --config-only

[positional-arguments]
packages *ARGS:
    bash "{{root}}/bootstrap.sh" --packages "$@"

[positional-arguments]
upgrade *ARGS:
    bash "{{root}}/bootstrap.sh" --upgrade "$@"

target-doctor:
    bash "{{root}}/bootstrap.sh" --doctor

lint:
    bash scripts/lint.sh

test:
    uv run --no-project python -m unittest discover -s tests -v

docs-build:
    uv run --no-project --with 'mkdocs<2' --with mkdocs-material --with mkdocs-static-i18n mkdocs build --strict

check: lint test docs-build
