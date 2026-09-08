"""Exercise optional asset failures in a private native-environment fixture."""
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="termux-tool-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.prefix = self.root / "prefix"
        self.repo = self.root / "repo"
        for directory in (self.home, self.prefix / "bin", self.prefix / "tmp",
                          self.repo / "scripts", self.repo / "config"):
            directory.mkdir(parents=True, exist_ok=True)
        (self.root / ".fixture").touch()
        for name in ("tools.sh", "pair.sh"):
            shutil.copy2(SOURCE / "scripts" / name, self.repo / "scripts" / name)
        (self.prefix / "bin/bash").symlink_to(shutil.which("bash"))
        self.env = dict(os.environ, HOME=str(self.home), PREFIX=str(self.prefix),
                        DOTFILES_TEST_ROOT=str(self.root), DOTFILES_TEST_MODE="fixture-only-v1",
                        PATH=str(self.prefix / "bin") + ":/usr/bin:/bin", FIXTURE_ARCH="aarch64")
        self.script("uname", 'printf "%s\\n" "$FIXTURE_ARCH"\n')
        self.script("timeout", 'case "$1" in --kill-after=*) shift;; esac\nshift\nexec "$@"\n')
        # Termux ships GNU ln -T; use the OS atomic-link API on macOS fixtures.
        self.script("ln", f"exec {shlex.quote(sys.executable)} -c 'import os,sys; os.link(sys.argv[-2],sys.argv[-1])' \"$@\"\n")
        self.script("sha256sum", f"exec {shlex.quote(sys.executable)} {shlex.quote(str(self.root / 'checksum.py'))} \"$@\"\n")
        (self.root / "checksum.py").write_text(
            "import hashlib,sys\n"
            "for line in sys.stdin:\n"
            " digest,path=line.rstrip().split('  ',1)\n"
            " if hashlib.sha256(open(path,'rb').read()).hexdigest()!=digest: sys.exit(1)\n")
        self.payload = self.root / "payload"
        self.payload.write_text("#!/bin/sh\nprintf 'fixture herdr v1\\n'\n")
        self.script("curl", f"while [ \"$1\" != --output ]; do shift; done\ncp {shlex.quote(str(self.payload))} \"$2\"\n")
        self.lock()

    def script(self, name, content):
        path = self.prefix / "bin" / name
        path.write_text("#!/bin/sh\nset -eu\n" + content)
        path.chmod(0o755)
        return path

    def lock(self, digest=None, size=None):
        data = self.payload.read_bytes()
        digest = digest or hashlib.sha256(data).hexdigest()
        size = size if size is not None else len(data)
        (self.repo / "config/assets.lock").write_text(
            f"herdr|aarch64|v1|https://example.invalid/herdr|{digest}|raw|-|{size}\n")

    def run_tool(self, *args, env=None):
        return subprocess.run([str(self.prefix / "bin/bash"), str(self.repo / "scripts/tools.sh"), *args],
                              env=env or self.env, text=True, capture_output=True, timeout=10)

    def test_real_desktop_environment_is_rejected(self):
        env = dict(self.env)
        env.pop("DOTFILES_TEST_ROOT")
        result = self.run_tool("install", "herdr", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / ".local/bin/herdr").exists())

    def test_verified_candidate_installs_and_rerun_preserves_it(self):
        result = self.run_tool("install", "herdr")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        binary = self.home / ".local/bin/herdr"
        original = binary.read_bytes()
        self.payload.write_text("bad replacement")
        result = self.run_tool("install", "herdr")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(binary.read_bytes(), original)
        self.assertIn("launch-only", (self.home / ".local/state/dotfiles-termux/tools/herdr.status").read_text())

    def test_checksum_and_size_fail_before_execution(self):
        for digest, size in (("0" * 64, None), (None, 1)):
            with self.subTest(digest=digest, size=size):
                self.lock(digest, size)
                result = self.run_tool("install", "herdr")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.home / ".local/bin/herdr").exists())

    def test_failed_launch_does_not_install_binary(self):
        self.payload.write_text("#!/bin/sh\nexit 7\n")
        self.lock()
        result = self.run_tool("install", "herdr")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / ".local/bin/herdr").exists())
        self.assertIn("native-launch-failed", (self.home / ".local/state/dotfiles-termux/tools/herdr.status").read_text())

    def test_unsupported_architecture_has_explicit_status(self):
        result = self.run_tool("install", "herdr", env=dict(self.env, FIXTURE_ARCH="armv7l"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no locked native candidate", result.stderr)

    def test_invalid_option_preflight_installs_nothing(self):
        result = self.run_tool("install", "herdr,unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / ".local").exists())

    def test_existing_external_binary_and_symlink_are_preserved(self):
        external = self.script("herdr", "exit 0\n")
        result = self.run_tool("install", "herdr")
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.home / ".local/bin/herdr").exists())
        self.assertTrue(external.exists())

    def test_broken_destination_symlink_is_preserved(self):
        directory = self.home / ".local/bin"
        directory.mkdir(parents=True)
        (directory / "herdr").symlink_to(self.root / "missing")
        result = self.run_tool("install", "herdr")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((directory / "herdr").is_symlink())

    def test_doctor_does_not_create_runtime_state(self):
        result = self.run_tool("doctor")
        self.assertEqual(result.returncode, 0)
        self.assertIn("missing (optional)", result.stdout)
        self.assertFalse((self.home / ".local").exists())

    def test_codex_probe_rejects_sandbox_start_failure(self):
        self.script("codex", "printf 'sandbox unavailable\\n' >&2\nexit 1\n")
        result = self.run_tool("probe", "codex")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not execute", result.stderr)
        self.assertEqual(list((self.prefix / "tmp").iterdir()), [])

    def test_codex_probe_rejects_command_runner_without_write_enforcement(self):
        # The fake runner deliberately provides no sandbox. The negative gate
        # must catch that, even after its positive command succeeds.
        self.script("codex", 'test "$1" = sandbox\nshift\ntest "$1" = --\nshift\nexec "$@"\n')
        result = self.run_tool("probe", "codex")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("write-denial check failed", result.stderr)
        self.assertEqual(list((self.prefix / "tmp").iterdir()), [])
