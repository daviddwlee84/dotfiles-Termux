"""Complete Codex package installation using isolated, non-native fixtures."""
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class CodexPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="termux-codex-package-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.prefix = self.root / "prefix"
        self.repo = self.root / "repo"
        for directory in (self.home, self.prefix / "bin", self.prefix / "tmp", self.repo / "scripts", self.repo / "config"):
            directory.mkdir(parents=True, exist_ok=True)
        (self.root / ".fixture").touch()
        for name in ("pair.sh", "codex-package.sh"):
            shutil.copy2(SOURCE / "scripts" / name, self.repo / "scripts" / name)
        (self.prefix / "bin/bash").symlink_to(shutil.which("bash"))
        self.env = dict(os.environ, HOME=str(self.home), PREFIX=str(self.prefix),
                        DOTFILES_TEST_ROOT=str(self.root), DOTFILES_TEST_MODE="fixture-only-v1",
                        PATH=str(self.prefix / "bin") + ":/usr/bin:/bin",
                        FIXTURE_ARCHIVE=str(self.root / "package.tar.gz"),
                        FIXTURE_CURL_LOG=str(self.root / "curl.log"),
                        FIXTURE_MV_LOG=str(self.root / "mv.log"),
                        FIXTURE_LAUNCH_LOG=str(self.root / "launch.log"))
        self.members = {
            "bin/codex": b'#!/bin/sh\necho launch >> "$FIXTURE_LAUNCH_LOG"\nprintf "codex-cli fixture\\n"\n',
            "bin/codex-code-mode-host": b"#!/bin/sh\nprintf 'fixture code mode\\n'\n",
            "codex-package.json": json.dumps({"layoutVersion": 1, "entrypoint": "bin/codex"}).encode(),
            "codex-path/rg": b"#!/bin/sh\nprintf 'fixture rg\\n'\n",
            "codex-resources/bwrap": b"#!/bin/sh\nprintf 'fixture bwrap\\n'\n",
            "codex-resources/zsh/bin/zsh": b"#!/bin/sh\nprintf 'fixture zsh\\n'\n",
        }
        self.script("uname", "printf 'aarch64\\n'\n")
        self.script("timeout", 'case "$1" in --kill-after=*) shift;; esac\nshift\nexec "$@"\n')
        self.script("curl", 'test "${FIXTURE_FAIL_DOWNLOAD:-0}" != 1\necho download >> "$FIXTURE_CURL_LOG"\n'
                    'while [ "$1" != --output ]; do shift; done\ncp "$FIXTURE_ARCHIVE" "$2"\n')
        self.python_tool("stat", "import os,stat,sys\nassert sys.argv[1:3]==['-c','%a']\nprint(oct(stat.S_IMODE(os.stat(sys.argv[3]).st_mode))[2:])\n")
        self.python_tool("sha256sum", "import hashlib,sys\nassert sys.argv[1:]==['-c','-']\n"
                         "for line in sys.stdin:\n"
                         " digest,path=line.rstrip('\\n').split('  ',1)\n"
                         " if hashlib.sha256(open(path,'rb').read()).hexdigest()!=digest: sys.exit(1)\n")
        # Read real local tar files, with GNU metadata formatting independent of
        # macOS BSD tar. Extraction writes only the explicitly requested member.
        self.python_tool("tar", "import stat,sys,tarfile\n"
                         "with tarfile.open(sys.argv[2]) as archive:\n"
                         " if sys.argv[1]=='-tvzf':\n"
                         "  assert '--numeric-owner' in sys.argv and '--full-time' in sys.argv\n"
                         "  for m in archive:\n"
                         "   kind=stat.S_IFDIR if m.isdir() else stat.S_IFLNK if m.issym() else stat.S_IFREG\n"
                         "   name=m.name+('/' if m.isdir() else '')\n"
                         "   print(stat.filemode(kind|m.mode),'0/0',m.size,'2026-09-09','00:00:00',name)\n"
                         " elif sys.argv[1]=='-xOzf':\n"
                         "  assert sys.argv[3:5]==['--no-wildcards','--']\n"
                         "  sys.stdout.buffer.write(archive.extractfile(sys.argv[5]).read())\n"
                         " else: raise AssertionError(sys.argv)\n")
        self.python_tool("mv", "import os,pathlib,sys\nassert sys.argv[1]=='-nT'\nsrc,dst=sys.argv[2:4]\n"
                         "name=str(pathlib.Path(dst).relative_to(pathlib.Path(os.environ['HOME'])/'.local'))\n"
                         "with open(os.environ['FIXTURE_MV_LOG'],'a') as log: log.write(name+'\\n')\n"
                         "if name==os.environ.get('FIXTURE_RACE_MEMBER'):\n"
                         " if os.environ.get('FIXTURE_RACE_KIND')=='directory': os.mkdir(dst)\n"
                         " else: pathlib.Path(dst).write_text('foreign raced-in file')\n"
                         "if not os.path.lexists(dst): os.rename(src,dst)\n")
        self.write_member_lock()
        self.write_archive()

    def script(self, name, content):
        destination = self.prefix / "bin" / name
        destination.write_text("#!/bin/sh\nset -eu\n" + content)
        destination.chmod(0o755)
        return destination

    def python_tool(self, name, code):
        path = self.root / (name + ".py")
        path.write_text(code)
        self.script(name, f"exec {shlex.quote(sys.executable)} {shlex.quote(str(path))} \"$@\"\n")

    def write_member_lock(self):
        lines = []
        for name, data in self.members.items():
            mode = "0644" if name.endswith(".json") else "0755"
            lines.append(f"{name}|{hashlib.sha256(data).hexdigest()}|{len(data)}|{mode}\n")
        (self.repo / "config/codex-package-files.lock").write_text("".join(lines))

    def write_archive(self, *, overrides=None, missing=None, symlink=None, bad_mode=None, extra=None):
        path = self.root / "package.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name, original in self.members.items():
                if name == missing:
                    continue
                data = (overrides or {}).get(name, original)
                entry = tarfile.TarInfo(name)
                entry.mode = 0o644 if name.endswith(".json") else 0o755
                if name == bad_mode:
                    entry.mode = 0o644
                if name == symlink:
                    entry.type = tarfile.SYMTYPE
                    entry.linkname = "/outside/fixture"
                    archive.addfile(entry)
                else:
                    entry.size = len(data)
                    archive.addfile(entry, io.BytesIO(data))
            if extra:
                entry = tarfile.TarInfo(extra)
                entry.mode = 0o755
                entry.size = 1
                archive.addfile(entry, io.BytesIO(b"x"))
        data = path.read_bytes()
        (self.repo / "config/assets.lock").write_text(
            "codex|aarch64|fixture|https://example.invalid/codex-package.tar.gz|"
            f"{hashlib.sha256(data).hexdigest()}|tar.gz|bin/codex|{len(data)}\n")

    def install(self, *, env=None):
        return subprocess.run([str(self.prefix / "bin/bash"), str(self.repo / "scripts/codex-package.sh"), "install"],
                              env=env or self.env, text=True, capture_output=True, timeout=30)

    def existing_member(self, name, data=None):
        path = self.home / ".local" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.members[name] if data is None else data)
        path.chmod(0o644 if name.endswith(".json") else 0o755)
        return path

    def assert_no_staging(self):
        self.assertEqual(list((self.home / ".local").glob(".codex-package.*")), [])

    def test_initial_install_preserves_full_layout_and_publishes_main_last(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name, data in self.members.items():
            path = self.home / ".local" / name
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(path.stat().st_mode & 0o777, 0o644 if name.endswith(".json") else 0o755)
        self.assertEqual((self.root / "mv.log").read_text().splitlines()[-1], "bin/codex")
        status = (self.home / ".local/state/dotfiles-termux/tools/codex.status").read_text()
        self.assertIn("launch-only", status)
        self.assertIn("verified package companions", status)
        self.assertIn("acceptance pending", status)
        self.assert_no_staging()

    def test_old_exact_standalone_binary_is_retained_while_companions_are_added(self):
        binary = self.existing_member("bin/codex")
        inode = binary.stat().st_ino
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(binary.stat().st_ino, inode)
        self.assertNotIn("bin/codex", (self.root / "mv.log").read_text().splitlines())
        self.assertEqual((self.home / ".local/codex-resources/bwrap").read_bytes(), self.members["codex-resources/bwrap"])

    def test_complete_package_repeat_does_not_download(self):
        first = self.install()
        self.assertEqual(first.returncode, 0, first.stderr)
        result = self.install(env=dict(self.env, FIXTURE_FAIL_DOWNLOAD="1"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no download needed", result.stdout)
        self.assertEqual((self.root / "curl.log").read_text().splitlines(), ["download"])

    def test_different_main_or_companion_preflight_preserves_everything(self):
        for name in ("bin/codex", "codex-resources/bwrap"):
            with self.subTest(name=name):
                path = self.existing_member(name, b"user-owned differing file")
                result = self.install()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(path.read_bytes(), b"user-owned differing file")
                self.assertFalse((self.root / "curl.log").exists())
                path.unlink()

    def test_external_path_codex_is_preserved(self):
        external = self.script("codex", "exit 0\n")
        before = external.read_bytes()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("External Codex preserved", result.stderr)
        self.assertEqual(external.read_bytes(), before)
        self.assertFalse((self.home / ".local/bin/codex").exists())
        self.assertFalse((self.root / "curl.log").exists())

    def test_parent_and_member_symlinks_are_rejected_without_download(self):
        directory = self.home / ".local"
        directory.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        link = directory / "codex-resources"
        link.symlink_to(outside)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(link.is_symlink())
        self.assertEqual(list(outside.iterdir()), [])
        link.unlink()
        (directory / "bin").mkdir()
        link = directory / "bin/codex"
        link.symlink_to(self.root / "missing")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(link.is_symlink())
        self.assertFalse((self.root / "curl.log").exists())

    def test_member_hash_mismatch_never_runs_or_publishes_codex(self):
        original = self.members["codex-resources/bwrap"]
        self.write_archive(overrides={"codex-resources/bwrap": b"x" * len(original)})
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("member checksum mismatch", result.stderr)
        self.assertFalse((self.root / "launch.log").exists())
        self.assertFalse((self.home / ".local/bin/codex").exists())
        self.assert_no_staging()

    def test_archive_size_and_hash_are_checked_before_members(self):
        lock = self.repo / "config/assets.lock"
        original = lock.read_text()
        columns = original.strip().split("|")
        columns[4] = "0" * 64
        lock.write_text("|".join(columns) + "\n")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("archive SHA-256 mismatch", result.stderr)
        self.assertFalse((self.root / "launch.log").exists())
        self.assert_no_staging()

    def test_missing_linked_wrong_mode_and_unexpected_members_are_rejected(self):
        variants = ({"missing": "codex-path/rg"}, {"symlink": "codex-resources/bwrap"},
                    {"bad_mode": "bin/codex"}, {"extra": "../outside"})
        for variant in variants:
            with self.subTest(variant=variant):
                self.write_archive(**variant)
                result = self.install()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / "launch.log").exists())
                self.assertFalse((self.home / ".local/bin/codex").exists())
                self.assert_no_staging()

    def test_foreign_publish_race_is_not_overwritten_and_is_resumable(self):
        result = self.install(env=dict(self.env, FIXTURE_RACE_MEMBER="codex-resources/bwrap"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Concurrent Codex destination preserved", result.stderr)
        raced = self.home / ".local/codex-resources/bwrap"
        self.assertEqual(raced.read_text(), "foreign raced-in file")
        self.assertFalse((self.home / ".local/bin/codex").exists())
        self.assert_no_staging()
        raced.unlink()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_raced_in_directory_does_not_receive_the_staged_binary(self):
        result = self.install(env=dict(self.env, FIXTURE_RACE_MEMBER="bin/codex", FIXTURE_RACE_KIND="directory"))
        self.assertNotEqual(result.returncode, 0)
        directory = self.home / ".local/bin/codex"
        self.assertTrue(directory.is_dir())
        self.assertEqual(list(directory.iterdir()), [])
        self.assert_no_staging()

    def test_real_desktop_context_is_rejected(self):
        env = dict(self.env)
        del env["DOTFILES_TEST_ROOT"]
        result = self.install(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "curl.log").exists())


if __name__ == "__main__":
    unittest.main()
