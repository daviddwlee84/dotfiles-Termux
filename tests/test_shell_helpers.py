"""Exercise the shared helpers under real Bash and zsh, with private state."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

CONFIG = Path(__file__).resolve().parents[1] / 'home/dot_config/dotfiles-termux'


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='termux-helpers-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        (self.bin / 'python3').symlink_to(sys.executable)
        self.env = dict(os.environ, HOME=str(self.home), PREFIX=str(self.home),
                        PATH=str(self.bin) + ':/usr/bin:/bin', TERM='dumb',
                        DOTFILES_TERMUX_CONFIG_DIR=str(CONFIG),
                        XDG_CACHE_HOME=str(self.home / '.cache'))
        for name in ('ZDOTDIR', 'BASH_ENV', 'ENV', 'DOTFILES_TERMUX_CACHE_DIR'):
            self.env.pop(name, None)

    def run_shell(self, kind, code, interactive=False):
        binary = shutil.which(kind)
        if not binary:
            self.skipTest(f'{kind} is required')
        options = ['--noprofile', '--norc'] if kind == 'bash' else ['-f']
        return subprocess.run([binary, *options, '-ic' if interactive else '-c', code],
                              cwd=self.home, env=self.env, text=True, capture_output=True, timeout=20)

    def test_paths_preserve_logical_cwd_and_support_resolve_tilde_and_spaces(self):
        (self.home / 'real directory').mkdir()
        (self.home / 'logical').symlink_to(self.home / 'real directory')
        (self.home / 'real directory/file name').touch()
        code = '''source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"
cd "$HOME/logical"
abspath
abspath -t 'file name' missing
abspath -r 'file name'
abspath -- -filename
'''
        expected = [str(self.home / 'logical'), '~/logical/file name', '~/logical/missing',
                    str(self.home / 'real directory/file name'), str(self.home / 'logical/-filename')]
        for kind in ('bash', 'zsh'):
            with self.subTest(shell=kind):
                result = self.run_shell(kind, code)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), expected)

    def test_resolve_errors_keep_successful_paths_and_reject_unknown_options(self):
        for kind in ('bash', 'zsh'):
            result = self.run_shell(kind, 'source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"; abspath -r . missing')
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stdout.strip(), str(self.home))
            self.assertIn('no such file', result.stderr)
            result = self.run_shell(kind, 'source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"; abspath --unknown')
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')

    def test_chezmoi_cd_preserves_cwd_on_failure(self):
        program = self.bin / 'chezmoi'
        program.write_text('#!/bin/sh\nexit 7\n')
        program.chmod(0o755)
        for kind in ('bash', 'zsh'):
            result = self.run_shell(kind, 'source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"; chezmoi-cd; code=$?; pwd; exit "$code"')
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout.strip(), str(self.home))
        destination = self.home / 'source with spaces'
        destination.mkdir()
        program.write_text('#!/bin/sh\nprintf "%s\\n" ' + shlex.quote(str(destination)) + '\n')
        for kind in ('bash', 'zsh'):
            result = self.run_shell(kind, 'source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"; chezmoi-cd; pwd')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(destination))

    def test_reload_uses_actual_interpreter_and_redefines_helpers(self):
        for kind in ('bash', 'zsh'):
            rc = self.home / ('.bashrc' if kind == 'bash' else '.zshrc')
            rc.write_text('source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"\nRELOAD_COUNT=$(( ${RELOAD_COUNT:-0} + 1 ))\n')
            self.env['SHELL'] = '/wrong/login/shell'
            result = self.run_shell(kind, '''source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"
source-rc
source-rc
printf '%s\n' "$RELOAD_COUNT"
''')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), '2')

    def test_zsh_reload_keeps_plugins_single_and_dev_generation_cached(self):
        assets = self.home / '.local/share/dotfiles-termux/zsh'
        (assets / 'omz').mkdir(parents=True)
        (assets / 'suggest').mkdir()
        (assets / 'highlight').mkdir()
        (assets / 'assets.sh').write_text(f'DOTFILES_TERMUX_OMZ={shlex.quote(str(assets / "omz"))}\n'
                                        f'DOTFILES_TERMUX_AUTOSUGGEST={shlex.quote(str(assets / "suggest"))}\n'
                                        f'DOTFILES_TERMUX_HIGHLIGHT={shlex.quote(str(assets / "highlight"))}\n')
        (assets / 'omz/oh-my-zsh.sh').write_text('OMZ_LOADS=$(( ${OMZ_LOADS:-0} + 1 ))\nautoload -Uz compinit\ncompinit -d "$ZSH_COMPDUMP"\n')
        (assets / 'suggest/zsh-autosuggestions.zsh').write_text('SUGGEST_LOADS=$(( ${SUGGEST_LOADS:-0} + 1 ))\n')
        (assets / 'highlight/zsh-syntax-highlighting.zsh').write_text('HIGHLIGHT_LOADS=$(( ${HIGHLIGHT_LOADS:-0} + 1 ))\n_zsh_highlight() { :; }\n')
        dev = self.bin / 'dev'
        dev.write_text('''#!/bin/sh
printf '%s\n' "$*" >> "$HOME/dev-calls"
case "$*" in
 'shell-init zsh') printf '%s\n' 'export DEV_SHELL_INIT=1' 'dev() { command dev "$@"; }';;
 'completion zsh') printf '%s\n' '_dev() { :; }' 'compdef _dev dev';;
 *) exit 2;;
esac
''')
        dev.chmod(0o755)
        result = self.run_shell('zsh', '''source "$DOTFILES_TERMUX_CONFIG_DIR/shell.zsh"
source "$DOTFILES_TERMUX_CONFIG_DIR/shell.zsh"
print -r -- "$OMZ_LOADS:$SUGGEST_LOADS:$HIGHLIGHT_LOADS:$DEV_SHELL_INIT:${_comps[dev]}"
''', interactive=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '1:1:1:1:_dev', result.stderr + '\n' + (self.home / 'dev-calls').read_text())
        self.assertEqual((self.home / 'dev-calls').read_text().splitlines(), ['shell-init zsh', 'completion zsh'])
