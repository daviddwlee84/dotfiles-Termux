"""Pinned zsh archives publish without overwriting foreign state."""
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import unittest

import test_tools


class ZshAssetTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_tools.ToolTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        shutil.copy2(test_tools.SOURCE / 'scripts/zsh-assets.sh', f.repo / 'scripts/zsh-assets.sh')
        (f.prefix / 'bin/python3').symlink_to(sys.executable)
        self.version = 'a' * 40
        with tarfile.open(f.payload, 'w:gz') as archive:
            for name in ('oh-my-zsh.sh', 'zsh-autosuggestions.zsh', 'zsh-syntax-highlighting.zsh'):
                body = b'# fixture\n'
                entry = tarfile.TarInfo('fixture/' + name)
                entry.size = len(body)
                archive.addfile(entry, io.BytesIO(body))
        data = f.payload.read_bytes()
        rows = [f'{name}|any|{self.version}|https://example.invalid/{name}|{hashlib.sha256(data).hexdigest()}|tar.gz|fixture|{len(data)}'
                for name in ('oh-my-zsh', 'zsh-autosuggestions', 'zsh-syntax-highlighting')]
        (f.repo / 'config/assets.lock').write_text('\n'.join(rows) + '\n')
        self.base = f.home / '.local/share/dotfiles-termux/zsh'

    def run_assets(self, action='install'):
        f = self.fixture
        return subprocess.run([str(f.prefix / 'bin/bash'), str(f.repo / 'scripts/zsh-assets.sh'), action],
                              env=f.env, capture_output=True, text=True, timeout=20)

    def test_check_missing_assets_does_not_create_directories(self):
        result = self.run_assets('check')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.base.exists())

    def test_install_repeat_reuses_complete_assets_without_download(self):
        result = self.run_assets()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        original = (self.base / 'assets.sh').read_bytes()
        self.fixture.payload.write_text('invalid archive; must not download')
        result = self.run_assets()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.base / 'assets.sh').read_bytes(), original)
        self.assertEqual(self.run_assets('check').returncode, 0)

    def test_bad_download_never_publishes_assets(self):
        self.fixture.payload.write_text('corrupted')
        result = self.run_assets()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base / 'assets.sh').exists())
        self.assertEqual(list(self.base.iterdir()), [])

    def test_foreign_version_directory_and_index_are_preserved(self):
        destination = self.base / ('oh-my-zsh-' + self.version)
        destination.mkdir(parents=True)
        (destination / 'user').write_text('keep')
        self.assertNotEqual(self.run_assets().returncode, 0)
        self.assertEqual((destination / 'user').read_text(), 'keep')
        shutil.rmtree(destination)
        self.assertEqual(self.run_assets().returncode, 0)
        (self.base / 'assets.sh').write_text('foreign index\n')
        self.assertNotEqual(self.run_assets().returncode, 0)
        self.assertEqual((self.base / 'assets.sh').read_text(), 'foreign index\n')
