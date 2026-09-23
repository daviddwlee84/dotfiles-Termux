"""The new Herdr seed migrates only exact old seeds, never customized files."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/herdr-shell.py"
SPEC = importlib.util.spec_from_file_location("herdr_shell", SCRIPT)
HERDR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HERDR)


class HerdrSeedTests(unittest.TestCase):
    def render(self, before):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.toml"
            target.write_text(before)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "render", str(target), directory,
                 "/termux", "zsh"], input=before, text=True,
                capture_output=True, check=True)
            self.assertEqual(target.read_text(), before)
            return result.stdout

    def test_legacy_seed_migrates_and_remains_repeatable(self):
        legacy = ('# Create-once seed. Herdr and the user own subsequent configuration changes.\n'
                  '[terminal]\ndefault_shell = "/termux/bin/bash"\n')
        output = self.render(legacy)
        parsed = tomllib.loads(output)
        self.assertEqual(parsed["terminal"]["default_shell"], "/termux/bin/zsh")
        self.assertEqual(parsed["ui"]["status_indicators"], "symbols")
        self.assertIn(["terminal_title_stripped"], parsed["ui"]["sidebar"]["agents"]["rows"])
        self.assertEqual(self.render(output), output)

    def test_runtime_writes_and_user_comments_prevent_seed_replacement(self):
        for seed in (HERDR.legacy_seed("/termux", "bash"), HERDR.seed("/termux", "bash")):
            for customization in ("# keep my settings\n", "\n[update]\nchannel = \"preview\"\n"):
                with self.subTest(seed=seed, customization=customization):
                    before = seed + customization
                    self.assertEqual(self.render(before), before)


if __name__ == "__main__":
    unittest.main()
