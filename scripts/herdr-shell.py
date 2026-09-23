"""Preserve custom Herdr config; only retarget the exact dotfiles seed."""
import os
from pathlib import Path
import sys
import tempfile
import tomllib


def legacy_seed(prefix, shell):
    return ('# Create-once seed. Herdr and the user own subsequent configuration changes.\n'
            '[terminal]\ndefault_shell = "' + prefix + '/bin/' + shell + '"\n')


def seed(prefix, shell):
    return legacy_seed(prefix, shell) + '''shell_mode = "auto"
new_cwd = "follow"

# Herdr 0.9.1+; no desktop helpers or plugins are required.
[theme]
name = "catppuccin"
auto_switch = false

[ui]
confirm_close = true
status_indicators = "symbols"
agent_panel_sort = "priority"

[ui.sidebar.agents]
rows = [
  ["state_icon", "workspace", "tab"],
  ["machine", "agent"],
  ["terminal_title_stripped"],
]

[keys]
split_vertical = ["prefix+|", "prefix+%"]
split_horizontal = ["prefix+minus", 'prefix+"']
reload_config = "prefix+shift+r"
rename_tab = "prefix+,"
new_worktree = "prefix+shift+b"
switch_workspace = "prefix+ctrl+1..9"
focus_agent = "prefix+alt+1..9"
navigate_workspace_down = ["j", "down"]
navigate_workspace_up = ["k", "up"]

# Both tools are included in Termux's base package set.
[[keys.command]]
key = "prefix+G"
type = "pane"
command = "lazygit"
description = "lazygit (temporary pane)"

[[keys.command]]
key = "alt+g"
type = "pane"
command = "lazygit"
description = "lazygit (temporary pane)"

[[keys.command]]
key = "prefix+Y"
type = "popup"
command = "yazi"
width = "90%"
height = "85%"
description = "yazi file manager (popup)"
'''


def main():
    action, target, state, prefix, shell = sys.argv[1:]
    if shell not in ('bash', 'zsh'):
        raise ValueError('unsupported interactive shell')
    target = Path(target)
    if target.is_symlink():
        raise ValueError('Herdr config symlink preserved')
    before = sys.stdin.read() if action == 'render' else (target.read_text() if target.is_file() else '')
    known = before in tuple(make(prefix, value)
                            for make in (legacy_seed, seed) for value in ('bash', 'zsh'))
    after = seed(prefix, shell)
    if action == 'render':
        # An existing empty/custom file is still user-owned.
        sys.stdout.write(after if known or not target.exists() else before)
    elif action == 'backup':
        if known and before != after:
            descriptor, _ = tempfile.mkstemp(prefix='herdr-shell.before.', dir=state)
            with os.fdopen(descriptor, 'w') as output:
                output.write(before)
    elif action == 'doctor':
        if before and not known:
            try:
                selected = tomllib.loads(before).get('terminal', {}).get('default_shell')
            except tomllib.TOMLDecodeError:
                selected = None
            if selected != prefix + '/bin/' + shell:
                print('Herdr custom configuration preserved; set terminal.default_shell explicitly for new sessions.', file=sys.stderr)
    else:
        raise ValueError('unknown Herdr shell operation')


if __name__ == '__main__':
    main()
