# Shell and configuration

Fresh setup uses native Termux zsh. Existing installations retain their saved
shell; older configurations without `primaryShell` inherit the current login
shell. Bash stays installed and executes bootstrap, package, SSH and Boot scripts.
Both shells provide the shared helpers below.

## Select a shell

```sh
# Inside the updated Termux clone:
bash bootstrap.sh packages --primary-shell zsh
# Return to Bash without uninstalling anything:
bash bootstrap.sh apply --primary-shell bash
# Computer-side equivalent for setup:
uv run --script scripts/host.py setup --primary-shell zsh
```

The `primaryShell` chezmoi value persists. Configuration-only apply does not
install a missing zsh or its plugins: it reports the missing dependency and
leaves the login shell unchanged. `packages` synchronizes native packages and
installs the locked assets before switching. The native environment guard and
all executable management shebangs still require Termux Bash.

New Termux and SSH logins use the selection. Existing panes and multiplexer
servers keep running. The unchanged Herdr seed follows the selection for new sessions; custom Herdr configuration
is preserved with an instruction to set `terminal.default_shell` explicitly.

The Herdr 0.9.1 seed aligns with desktop defaults: fixed Catppuccin Mocha, distinct symbols, priority ordering, and three sidebar rows for workspace, machine/agent, and task title. Shared keys are `prefix+|` / `prefix+%` for side-by-side splits, `prefix+-` / `prefix+"` for stacked splits, `prefix+R` reload, `prefix+,` rename tab, `prefix+B` new worktree, `prefix+Ctrl+1..9` workspace selection, `prefix+Alt+1..9` agent focus, and j/k workspace navigation. `prefix+G` / `Alt+g` open a temporary LazyGit pane; `prefix+Y` opens a Yazi popup. Only fresh configurations and byte-identical old seeds update; customized files, including Herdr runtime writes, remain unchanged.

## Interactive features and helpers

The zsh configuration enables a small Oh My Zsh setup with its `git` plugin,
zsh-autosuggestions, zsh-syntax-highlighting, official zsh-completions, cached
dev completion and the existing small Starship prompt. It uses Emacs keybindings:
Tab completes, Ctrl+R searches history, and Right accepts the suggested history
suffix at the end of the command. Zsh history stays in its own `.zsh_history`;
Bash history is not converted. Zsh glob and word-splitting rules differ from Bash;
run Bash scripts with `bash script.sh`.

```sh
lg                              # open lazygit in the current repository
y                               # browse files; q returns to the selected directory
y "$HOME"                       # start Yazi at a chosen directory
yazi                            # direct launch; does not change the parent shell
abspath                         # logical current directory, like pwd
abspath 'file with spaces' ../x  # absolute paths; existence is not required
abspath -r link                  # resolve symlinks; target must exist
abspath -t "$HOME/src"           # ~/src
abspath -- -filename             # a name starting with a dash
source-rc                        # reload the current shell's rc and helpers
reload                           # alias for source-rc
chezmoi-cd                       # enter the effective chezmoi source (home/)
```

Existing `lg` or `y` commands, aliases and functions are preserved. Otherwise,
`lg` is an alias for `lazygit`. The `y` wrapper forwards arguments to Yazi and
changes directory only after a successful exit with a returned directory. `Q`
leaves the shell directory unchanged. Temporary cwd files are removed after exit;
failed launches preserve the current directory and return the failure status.
Both tools are native `pkg` baseline packages; no downloads run on shell startup.
See the [official Yazi wrapper](https://yazi-rs.github.io/docs/quick-start/#shell-wrapper).

The rc files retain existing content and append a managed block. Bash's existing
login forwarding remains intact; zsh login configuration supplies the shared
PATH/helpers without loading interactive plugins. Repeated sourcing does not
wrap plugins or register prompt hooks repeatedly. `reload` explicitly re-runs
the current rc, including user content. Persistent overrides belong in
`~/.config/dotfiles-termux/local.sh` for Bash or `local.zsh` for zsh.

Oh My Zsh and plugins live in namespaced version directories under
`~/.local/share/dotfiles-termux/zsh`. Downloads are pinned by commit, SHA-256 and
size in the lockfile. Explicit package operations install new locked versions;
normal chezmoi apply and shell startup never download or auto-update them.
Completion auditing remains enabled; completion dumps and generated dev scripts
use a separate cache. The dev cache regenerates when its binary path or mtime changes.

## Startup measurements

On the ARM64 Android 15 tablet, the final candidate passed 30 interleaved warm
samples per shell and location on 2026-09-13. These measure native interactive
rc-to-first-prompt latency, excluding SSH transport and login profiles. Cold
means empty private completion/dev/prompt caches, not an OS cache flush.

| Location | Managed Bash median / P95 | zsh median / P95 | zsh cold cache |
| --- | --- | --- | --- |
| HOME | 116 / 133 ms | 186 / 204 ms | 694 ms |
| Git repository | 119 / 139 ms | 190 / 208 ms | 692 ms |

The gate is at most +100 ms median, +200 ms P95, and a cold first prompt within
one second. Removing redundant external cache checks brought Oh My Zsh under
that gate, so the native-zsh-only fallback was not needed. Reproduce in Termux:

```sh
python scripts/benchmark-shell.py --managed-bash --candidate-config home/dot_config/dotfiles-termux --repo .
```

## Python and uv

Python, `uv` and `uvx` come from official `pkg` packages. The create-once
`~/.config/uv/uv.toml` selects `python-preference = "only-system"`,
`python-downloads = "never"`, and `link-mode = "copy"`. This keeps the native
Termux interpreter and avoids the hardlink failure observed in Android app storage.
Later local changes to this config survive chezmoi apply.

```sh
uv --version
uv venv .venv
uv pip install --python .venv/bin/python packaging==25.0
uv run --no-project --with packaging==25.0 python -c 'import packaging; print(packaging.__version__)'
```

The device passed venv creation and a PyPI install using Python 3.14.6 and uv
0.12.13. Packages requiring native extensions still need Android-compatible
sources/dependencies; this check does not establish support for every PyPI wheel.
Use `pkg` for system dependencies and Python/uv upgrades.

## Native paths

| Purpose | Location |
| --- | --- |
| Home and repositories | `$HOME` (normally `/data/data/com.termux/files/home`) |
| Termux programs | `$PREFIX/bin` |
| Termux package configuration | `$PREFIX/etc` |
| Temporary files | `$TMPDIR` |
| Dotfile source root | The clone's `home/` |
| This repository's saved choices | `~/.config/dotfiles-termux/settings` |

Keep project checkouts in app-private storage. Shared Android storage can be
`noexec`, cannot preserve all Unix file semantics, and is a poor location for
Git repositories or binaries. `termux-setup-storage` is an optional separate
step for exchanging files; bootstrap does not request broad storage access.
[Official filesystem/execution notes](https://github.com/termux/termux-packages/wiki/Termux-execution-environment#file-execution-and-special-file-features-not-allowed-in-external-storage).

## Daily workflow

```sh
# In the Termux repository clone:
chezmoi diff
just apply
bash bootstrap.sh update
```

These operations do not upgrade packages. Use `just packages` or `just upgrade`
for explicit full package synchronization. If a new configuration needs a new
dependency, run that synchronization separately.

Termux uses Bionic libc. A Linux ARM64 download is not automatically a native
Termux package: a matching CPU architecture does not prove loader, paths,
DNS, PTY or sandbox compatibility. Prefer `pkg` for packaged tools and follow
the [agent compatibility guide](tools.md) for experiments.
