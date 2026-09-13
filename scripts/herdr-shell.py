"""Preserve custom Herdr config; only retarget the exact dotfiles seed."""
import os
from pathlib import Path
import sys
import tempfile


def seed(prefix, shell):
    return ('# Create-once seed. Herdr and the user own subsequent configuration changes.\n'
            '[terminal]\ndefault_shell = "' + prefix + '/bin/' + shell + '"\n')


def main():
    action, target, state, prefix, shell = sys.argv[1:]
    if shell not in ('bash', 'zsh'):
        raise ValueError('unsupported interactive shell')
    target = Path(target)
    if target.is_symlink():
        raise ValueError('Herdr config symlink preserved')
    before = sys.stdin.read() if action == 'render' else (target.read_text() if target.is_file() else '')
    known = before in (seed(prefix, 'bash'), seed(prefix, 'zsh'))
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
            print('Herdr custom configuration preserved; set terminal.default_shell explicitly for new sessions.', file=sys.stderr)
    else:
        raise ValueError('unknown Herdr shell operation')


if __name__ == '__main__':
    main()
