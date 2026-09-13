"""Target behavior with real chezmoi and isolated native-command fixtures."""

import os
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
CHEZMOI = shutil.which("chezmoi")

# The native target has coreutils. Host fixtures must not depend on a macOS
# runner also having GNU timeout installed. This wrapper runs the actual child
# command, preserves argv/status, and kills its isolated process group on expiry.
TIMEOUT_FIXTURE = r'''
import os
import signal
import subprocess
import sys

args = sys.argv[1:]
grace = 0.2
try:
    if args and args[0].startswith("--kill-after="):
        grace = float(args.pop(0).split("=", 1)[1])
    deadline = float(args.pop(0))
    if deadline <= 0 or grace < 0 or not args:
        raise ValueError("invalid timeout arguments")
except (IndexError, ValueError):
    sys.exit(125)
try:
    child = subprocess.Popen(args, start_new_session=True)
except FileNotFoundError:
    sys.exit(127)
except PermissionError:
    sys.exit(126)
try:
    result = child.wait(timeout=deadline)
except subprocess.TimeoutExpired:
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    # Also clean up a surviving grandchild after its parent exits on TERM.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()
    sys.exit(124)
sys.exit(128 - result if result < 0 else result)
'''


@unittest.skipUnless(BASH and CHEZMOI, "Bash and chezmoi are required")
class TargetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="termux-target-")
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.repo = REPO
        self.prefix = self.root / "prefix"
        self.bin = self.prefix / "bin"
        self.home.mkdir()
        self.bin.mkdir(parents=True)
        (self.prefix / "tmp").mkdir()
        (self.root / ".fixture").touch()
        (self.bin / "bash").symlink_to(BASH)
        (self.bin / "chezmoi").symlink_to(CHEZMOI)
        timeout = self.bin / "timeout"
        timeout.write_text(f"#!{sys.executable}\n" + TIMEOUT_FIXTURE)
        timeout.chmod(0o755)
        self.env = os.environ.copy()
        for name in list(self.env):
            if name.startswith(("CHEZMOI_", "DOTFILES_INIT_", "GIT_", "XDG_")):
                self.env.pop(name)
        self.env.update(
            HOME=str(self.home), PREFIX=str(self.prefix),
            DOTFILES_TEST_ROOT=str(self.root), DOTFILES_TEST_MODE="fixture-only-v1",
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_CACHE_HOME=str(self.home / ".cache"),
            XDG_DATA_HOME=str(self.home / ".local/share"),
            XDG_STATE_HOME=str(self.home / ".local/state"),
            TMPDIR=str(self.prefix / "tmp"),
            GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(self.root / "gitconfig"),
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            REAL_SSH_KEYGEN=shutil.which("ssh-keygen"),
        )
        (self.root / "gitconfig").write_text(
            '[core]\n hooksPath = /dev/null\n[user]\n name = Fixture\n email = fixture@example.invalid\n'
            '[url "file:///nonexistent-fixture-network/"]\n insteadOf = https://\n'
        )
        self.write_command("pkg", 'printf "%s\\n" "$*" >>"$DOTFILES_TEST_ROOT/packages"\n'
                           '[[ ${FAIL_PKG_STAGE:-} != "$1" ]]\n')
        self.write_command("sshd", 'printf "%s\\n" "$*" >>"$DOTFILES_TEST_ROOT/sshd-calls"\n'
                           '[[ $1 == -t ]]\n')
        self.write_command("ssh-keygen", '[[ $1 != -A ]] || exit 0\nexec "$REAL_SSH_KEYGEN" "$@"\n')
        for name in ("curl", "wget"):
            self.write_command(name, 'echo "Network forbidden in target fixtures" >&2\nexit 91\n')

    def tearDown(self):
        self.temporary.cleanup()

    def write_command(self, name, body):
        path = self.bin / name
        path.write_text(f"#!{BASH}\nset -euo pipefail\n" + body)
        path.chmod(0o755)

    def run_command(self, args, *, expected=0, env=None):
        result = subprocess.run(args, env=env or self.env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout)
        return result.stdout

    def bootstrap(self, *args, expected=0):
        return self.run_command([BASH, str(self.repo / "bootstrap.sh"), *args], expected=expected)

    def configure(self, *args):
        return self.bootstrap("setup", "--non-interactive", "--install-coding-agents", "false", *args)

    @property
    def config(self):
        return self.home / ".config/chezmoi/chezmoi.toml"

    def test_native_guard_rejects_host_and_unsafe_fixture(self):
        env = self.env.copy()
        env.pop("DOTFILES_TEST_ROOT")
        result = subprocess.run([BASH, str(REPO / "scripts/guard.sh")], env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        env = self.env.copy()
        env["HOME"] = str(self.root)
        result = subprocess.run([BASH, str(REPO / "scripts/guard.sh")], env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        alternate = self.root / "other-home"
        self.home.rename(alternate)
        self.home.symlink_to(alternate, target_is_directory=True)
        result = subprocess.run([BASH, str(REPO / "scripts/guard.sh")], env=self.env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "packages").exists())

    def test_help_is_available_off_target_without_writes(self):
        env = self.env.copy()
        env.pop("DOTFILES_TEST_ROOT")
        output = self.run_command([BASH, str(REPO / "bootstrap.sh"), "--help"], env=env)
        self.assertIn("--ssh-mode", output)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_dry_run_and_invalid_options_do_not_write(self):
        self.bootstrap("--dry-run")
        self.assertEqual(list(self.home.iterdir()), [])
        self.bootstrap("--ssh-port", "22", expected=1)
        self.bootstrap("--with", "unknown", expected=1)
        self.assertFalse((self.root / "packages").exists())

    def test_fixture_timeout_preserves_argv_status_and_enforces_deadline(self):
        timeout = str(self.bin / "timeout")
        output = self.run_command([timeout, "2", sys.executable, "-c",
                                   "import sys; print(sys.argv[1])", "two words; literal"])
        self.assertEqual(output.strip(), "two words; literal")
        self.run_command([timeout, "2", sys.executable, "-c", "raise SystemExit(37)"], expected=37)
        self.run_command([timeout, "invalid", sys.executable], expected=125)
        started = time.monotonic()
        self.run_command([timeout, "--kill-after=0.1", "0.1", sys.executable, "-c",
                          "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"],
                         expected=124)
        self.assertLess(time.monotonic() - started, 3)

    def test_full_package_sync_precedes_install_and_missing_key_is_pending(self):
        output = self.configure()
        calls = (self.root / "packages").read_text().splitlines()
        self.assertEqual(calls[:2], ["update -y", "upgrade -y"])
        self.assertTrue(calls[2].startswith("install -y "))
        self.assertIn("pending-key", output)
        config = (self.home / ".config/dotfiles-termux/sshd_config").read_text()
        self.assertIn("ListenAddress 0.0.0.0", config)
        self.assertIn("PasswordAuthentication no", config)
        self.assertFalse((self.home / ".local/state/dotfiles-termux/sshd.pid").exists())

    def test_baseline_failure_stops_before_configuration(self):
        self.env["FAIL_PKG_STAGE"] = "upgrade"
        self.bootstrap("setup", "--install-coding-agents", "false", expected=1)
        self.assertFalse(self.config.exists())
        self.assertFalse((self.home / ".bashrc").exists())
        self.assertEqual((self.root / "packages").read_text().splitlines(), ["update -y", "upgrade -y"])

    def test_dev_selection_persists_and_apply_never_installs(self):
        self.write_command("herdr", 'printf "herdr 0.9.0\\n"\n')
        self.write_command("dev", 'printf "dev version v0.2.33\\n"\n')
        self.configure("--with", "herdr,dev")
        self.assertIn("optionalTools=herdr,dev", self.bootstrap("doctor"))
        (self.root / "packages").unlink()
        self.bootstrap("apply")
        self.assertFalse((self.root / "packages").exists())
        self.bootstrap("packages")
        self.assertIn("optionalTools=herdr,dev", self.bootstrap("doctor"))

    def test_dev_shell_integration_is_interactive_only_and_loaded_once(self):
        self.env["TERM"] = "dumb"
        self.env.pop("DOTFILES_TERMUX_SHELL_LOADED", None)
        self.write_command("dev", '''printf '%s\\n' "$*" >> "$DOTFILES_TEST_ROOT/dev-calls"
case "$*" in
    'shell-init bash') printf '%s\\n' 'dev() { builtin cd -- "$HOME/project with spaces"; }' ;;
    'completion bash') printf '%s\\n' 'complete -W "status repo" dev' ;;
    *) exit 1 ;;
esac
''')
        (self.home / "project with spaces").mkdir()
        shell = str(REPO / "home/dot_config/dotfiles-termux/shell.bash")
        self.run_command([BASH, "--noprofile", "--norc", "-c", 'source "$1"', "_", shell])
        self.assertFalse((self.root / "dev-calls").exists())
        output = self.run_command([BASH, "--noprofile", "--norc", "-ic",
                                   'source "$1"; source "$1"; dev; pwd; complete -p dev', "_", shell])
        self.assertIn(str(self.home / "project with spaces"), output)
        self.assertIn('complete -W', output)
        self.assertEqual((self.root / "dev-calls").read_text().splitlines(),
                         ["shell-init bash", "completion bash"])

    def test_reapply_preserves_shell_seeds_local_overrides_and_boot_scripts(self):
        (self.home / ".bashrc").write_text("export PERSONAL=yes\n")
        (self.home / ".bash_profile").write_text("# existing login\n")
        (self.home / ".vimrc").write_text("set nonumber\n")
        (self.home / ".tmux.conf").write_text("# personal tmux\n")
        local = self.home / ".config/dotfiles-termux/local.sh"
        local.parent.mkdir(parents=True)
        local.write_text("export PERSONAL_OVERRIDE=yes\n")
        boot = self.home / ".termux/boot/10-personal"
        boot.parent.mkdir(parents=True)
        boot.write_text("# personal boot\n")
        self.configure("--install-ssh-server", "false")
        first = (self.home / ".bashrc").read_bytes()
        (self.root / "packages").unlink()
        self.bootstrap("apply")
        self.bootstrap("apply")
        self.assertEqual((self.home / ".bashrc").read_bytes(), first)
        self.assertEqual(first.count(b"# >>> dotfiles-termux >>>"), 1)
        self.assertEqual((self.home / ".vimrc").read_text(), "set nonumber\n")
        self.assertEqual(boot.read_text(), "# personal boot\n")
        self.assertEqual(local.read_text(), "export PERSONAL_OVERRIDE=yes\n")
        self.assertFalse((self.root / "packages").exists())

    def test_chezmoi_reinit_choices_override_pairing_mirror_without_packages(self):
        self.configure("--ssh-mode", "lan")
        # Native --prompt re-init intentionally changes saved init choices.
        args = [CHEZMOI, "--config", str(self.config), "--source", str(REPO), "init", "--prompt",
                "--promptBool", "Install SSH server=false",
                "--promptChoice", "SSH access mode=adb", "--promptString", "SSH port=9022",
                "--promptBool", "Start SSH with Termux Boot=false",
                "--promptBool", "Acquire wake lock at boot=false",
                "--promptBool", "Install coding agents (Pi)=false",
                "--promptString", "Optional tools (herdr,codex,dev or empty)="]
        self.run_command(args)
        (self.root / "packages").unlink()
        self.bootstrap("apply")
        settings = (self.home / ".config/dotfiles-termux/settings").read_text()
        self.assertIn("installSshServer=false", settings)
        self.assertIn("sshMode=adb", settings)
        self.assertIn("sshPort=9022", settings)
        self.assertFalse((self.root / "packages").exists())

    def test_foreign_chezmoi_source_is_preserved_before_packages(self):
        foreign = self.home / "foreign"
        foreign.mkdir()
        self.config.parent.mkdir(parents=True)
        self.config.write_text(f'sourceDir = "{foreign}"\n')
        original = self.config.read_bytes()
        self.bootstrap("setup", expected=1)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.root / "packages").exists())

    def test_public_key_deduplication_preserves_restricted_existing_key(self):
        key = self.root / "host-key"
        subprocess.run([self.env["REAL_SSH_KEYGEN"], "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        public = Path(str(key) + ".pub")
        ssh = self.home / ".ssh"
        ssh.mkdir()
        authorized = ssh / "authorized_keys"
        authorized.write_text('restrict ' + public.read_text())
        before = authorized.read_bytes()
        command = f'source "{REPO}/scripts/pair.sh"; termux_context; termux_authorize_key "$1"'
        self.run_command([BASH, "-c", command, "_", str(public)])
        self.assertEqual(authorized.read_bytes(), before)
        self.run_command([BASH, "-c", command, "_", str(key)], expected=1)

    def test_owned_ssh_config_local_edits_are_preserved(self):
        self.configure()
        config = self.home / ".config/dotfiles-termux/sshd_config"
        config.write_text(config.read_text() + "# user edit\n")
        before = config.read_bytes()
        self.bootstrap("setup", "--install-coding-agents", "false", "--ssh-port", "9022", expected=1)
        self.assertEqual(config.read_bytes(), before)

    def test_existing_config_custom_values_survive_bootstrap_reinit(self):
        self.configure("--install-ssh-server", "false")
        self.config.write_text(self.config.read_text() + '\n[edit]\ncommand = "vim"\n')
        self.configure("--install-termux-boot", "false")
        self.assertIn('command = "vim"', self.config.read_text())

    def test_explicit_apply_flags_change_saved_choices_without_package_sync(self):
        self.configure()
        (self.root / "packages").unlink()
        self.bootstrap("apply", "--ssh-mode", "adb", "--ssh-port", "9022")
        settings = (self.home / ".config/dotfiles-termux/settings").read_text()
        self.assertIn("sshMode=adb", settings)
        self.assertIn("sshPort=9022", settings)
        self.assertIn("ListenAddress 127.0.0.1", (self.home / ".config/dotfiles-termux/sshd_config").read_text())
        self.assertFalse((self.root / "packages").exists())

    def test_plain_chezmoi_update_is_ff_only_and_configuration_only(self):
        upstream = self.root / "upstream"
        shutil.copytree(REPO, upstream, ignore=shutil.ignore_patterns(".git", "__pycache__", "site"))
        self.run_command(["git", "-C", str(upstream), "init", "-b", "main"])
        self.run_command(["git", "-C", str(upstream), "add", "."])
        self.run_command(["git", "-C", str(upstream), "commit", "-m", "fixture"])
        self.repo = self.root / "source with 'quotes'"
        self.run_command(["git", "clone", str(upstream), str(self.repo)])
        self.configure("--install-ssh-server", "false")
        shell = upstream / "home/dot_config/dotfiles-termux/shell.bash"
        shell.write_text(shell.read_text() + "\n# upstream fixture update\n")
        self.run_command(["git", "-C", str(upstream), "add", "."])
        self.run_command(["git", "-C", str(upstream), "commit", "-m", "update"])
        (self.root / "packages").unlink()
        self.run_command([CHEZMOI, "--config", str(self.config), "update"])
        self.assertIn("upstream fixture update", (self.home / ".config/dotfiles-termux/shell.bash").read_text())
        self.assertFalse((self.root / "packages").exists())
        (self.repo / "personal-change").write_text("preserve\n")
        self.run_command([CHEZMOI, "--config", str(self.config), "update"], expected=1)
        self.assertEqual((self.repo / "personal-change").read_text(), "preserve\n")

    def test_pairing_callback_reports_public_host_identity_only(self):
        hostkey = self.prefix / "etc/ssh/ssh_host_ed25519_key.pub"
        hostkey.parent.mkdir(parents=True)
        hostkey.write_text("ssh-ed25519 AAAAC3NzaFakeFixture= comment\n")
        self.write_command("curl", 'while (($#)); do\n'
                           ' if [[ $1 == --data-binary ]]; then printf "%s" "$2" >"$DOTFILES_TEST_ROOT/callback.json"; exit 0; fi\n'
                           ' shift\ndone\nexit 1\n')
        command = (f'source "{REPO}/scripts/pair.sh"; termux_context; termux_defaults; '
                   'PAIR_CALLBACK=http://127.0.0.1:12345/callback/nonce; termux_pair_callback ready')
        self.run_command([BASH, "-c", command])
        payload = json.loads((self.root / "callback.json").read_text())
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["ssh_port"], 8022)
        self.assertEqual(payload["host_key"], "ssh-ed25519 AAAAC3NzaFakeFixture=")
        self.assertEqual(set(payload), {"status", "user", "ssh_port", "host_key"})

    def test_foreign_listener_is_preserved_when_authorizing_a_key(self):
        # Match a macOS runner without Homebrew coreutils in PATH; the fixture
        # timeout must perform the real connection probe itself.
        self.env["PATH"] = str(self.bin) + os.pathsep + os.defpath
        key = self.root / "host-key"
        subprocess.run([self.env["REAL_SSH_KEYGEN"], "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.configure("--ssh-port", str(port))
            output = self.run_command([BASH, str(REPO / "scripts/ssh.sh"), "authorize", str(key) + ".pub"], expected=1)
            self.assertIn("already occupied", output)
            self.assertTrue(all(line.startswith("-t ") for line in (self.root / "sshd-calls").read_text().splitlines()))
            self.assertEqual(listener.getsockname()[1], port)

    def test_foreign_pid_is_never_signaled(self):
        state = self.home / ".local/state/dotfiles-termux"
        state.mkdir(parents=True)
        (state / "sshd.pid").write_text(str(os.getpid()) + "\n")
        proc = self.root / "proc" / str(os.getpid())
        proc.mkdir(parents=True)
        (proc / "cmdline").write_bytes(b"unrelated-process\0")
        (proc / "exe").symlink_to("/unrelated/process")
        output = self.run_command([BASH, str(REPO / "scripts/ssh.sh"), "stop"])
        self.assertIn("no process was stopped", output)
        self.assertEqual((state / "sshd.pid").read_text(), str(os.getpid()) + "\n")

    def test_fresh_login_profile_preserves_fallback_rc_and_prevents_recursion(self):
        (self.home / ".profile").write_text(
            'PROFILE_RUNS=$(( ${PROFILE_RUNS:-0} + 1 ))\n'
            'export FROM_PROFILE=profile-value\n'
            'source "$HOME/.bashrc"\n'
            'source "$HOME/.bash_profile"\n'
        )
        (self.home / ".bashrc").write_text(
            'RC_RUNS=$(( ${RC_RUNS:-0} + 1 ))\n'
            'export FROM_RC=rc-value\n'
            'alias fixture_login_alias=\'printf "alias-retained\\n"\'\n'
        )
        local = self.home / ".config/dotfiles-termux/local.sh"
        local.parent.mkdir(parents=True)
        local.write_text('MANAGED_RUNS=$(( ${MANAGED_RUNS:-0} + 1 ))\n')
        self.configure("--install-ssh-server", "false")
        env = self.env.copy()
        env["TERM"] = "dumb"
        command = ('fixture_login_alias; '
                   'printf "values:%s:%s:%s:%s:%s\\n" "$FROM_PROFILE" "$FROM_RC" '
                   '"$PROFILE_RUNS" "$RC_RUNS" "$MANAGED_RUNS"; '
                   'source "$HOME/.bashrc"; fixture_login_alias; '
                   'printf "resourced:%s:%s:%s:%s\\n" "$RC_RUNS" "$MANAGED_RUNS" '
                   '"${DOTFILES_TERMUX_LOGIN_FORWARDING:-unset}" "${DOTFILES_TERMUX_LOGIN_BASHRC_SEEN:-unset}"; '
                   'export -p | grep -q DOTFILES_TERMUX_ && exit 9; :')
        output = self.run_command([BASH, "--login", "-i", "-c", command], env=env)
        self.assertIn("alias-retained", output)
        self.assertIn("values:profile-value:rc-value:1:1:1", output)
        self.assertIn("resourced:2:1:unset:unset", output)
        # Bash's .bash_login precedence still applies on later fresh logins.
        (self.home / ".bash_login").write_text('FROM_LOGIN=login-value\n')
        command = ('fixture_login_alias; printf "precedence:%s:%s:%s:%s\\n" '
                   '"$FROM_LOGIN" "${PROFILE_RUNS:-0}" "$RC_RUNS" "$MANAGED_RUNS"')
        output = self.run_command([BASH, "--login", "-i", "-c", command], env=env)
        self.assertIn("precedence:login-value:0:1:1", output)

    def test_nonempty_login_profile_keeps_existing_startup_semantics(self):
        existing = 'export USER_LOGIN=preserved\n'
        (self.home / ".bash_profile").write_text(existing)
        (self.home / ".profile").write_text('export FALLBACK_WAS_RUN=yes\n')
        (self.home / ".bashrc").write_text('export RC_WAS_RUN=yes\n')
        self.configure("--install-ssh-server", "false")
        self.assertTrue((self.home / ".bash_profile").read_text().startswith(existing))
        env = self.env.copy()
        env["TERM"] = "dumb"
        output = self.run_command([BASH, "--login", "-i", "-c",
                                   'printf "startup:%s:%s:%s\\n" "$USER_LOGIN" '
                                   '"${FALLBACK_WAS_RUN:-no}" "${RC_WAS_RUN:-no}"'], env=env)
        self.assertIn("startup:preserved:no:no", output)


if __name__ == "__main__":
    unittest.main()
