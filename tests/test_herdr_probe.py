"""Exercise the headless probe's CLI contract without Herdr, PTYs or a device."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]

FAKE_HERDR = r'''
import json
import os
from pathlib import Path
import sys

observer = Path(os.environ["FIXTURE_OBSERVER"])
args = sys.argv[1:]
state_file = observer / "server.json"
with (observer / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps(args) + "\n")

def save(state):
    state_file.write_text(json.dumps(state))

def reply(value, *, error=False):
    print(json.dumps(value), file=sys.stderr if error else sys.stdout)

if args == ["server"]:
    private_home = Path(os.environ["HOME"]).resolve()
    probe = private_home.parent
    assert private_home != Path(os.environ["FIXTURE_ORIGINAL_HOME"]).resolve()
    assert Path.cwd() == private_home
    for key in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR", "TMPDIR", "HERDR_CONFIG_PATH", "HERDR_SOCKET_PATH"):
        assert Path(os.environ[key]).resolve().is_relative_to(probe), key
    for key in ("HERDR_SESSION", "HERDR_ENV", "HERDR_PANE_ID", "HERDR_CLIENT_SOCKET_PATH", "HERDR_STARTUP_CWD"):
        assert key not in os.environ, key
    config = Path(os.environ["HERDR_CONFIG_PATH"]).read_text()
    assert 'shell_mode = "non_login"' in config
    assert 'onboarding = false' in config
    save({"started": True, "created": False, "count": 0})
    (observer / "isolated").write_text(str(probe))
    print("fixture headless server running")
    sys.exit(0)

if args == ["server", "stop"]:
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    state["stopped"] = True
    save(state)
    sys.exit(0)

if not state_file.exists():
    reply({"error": {"code": "server_not_running"}}, error=True)
    sys.exit(1)
state = json.loads(state_file.read_text())
if args == ["pane", "list"]:
    # This is the important upstream behavior: readiness does not create a PTY.
    reply({"result": {"type": "pane_list", "panes": []}})
    (observer / "empty-list").touch()
    sys.exit(0)

if args[:2] == ["workspace", "create"]:
    assert (observer / "empty-list").exists(), "workspace created before readiness"
    assert args[args.index("--cwd") + 1] == os.environ["HOME"]
    assert args[args.index("--label") + 1] == "termux-probe"
    assert "--no-focus" in args
    mode = os.environ.get("FIXTURE_HERDR_MODE", "success")
    if mode == "pty-error":
        reply({"error": {"code": "workspace_create_failed", "message": "fixture PTY allocation denied"}}, error=True)
        sys.exit(1)
    result = {"type": "workspace_created", "workspace": {"workspace_id": "fixture-workspace"}, "tab": {"tab_id": "fixture-tab"}}
    if mode != "missing-root":
        result["root_pane"] = {"pane_id": "fixture-workspace:p7"}
    state.update(created=True, count=1)
    save(state)
    reply({"result": result})
    sys.exit(0)

assert state.get("created"), "pane operation before workspace creation"
if args[:2] == ["pane", "run"]:
    assert args[2] == "fixture-workspace:p7"
    assert args[3] == r'printf "termux-herdr-%s\n" "probe"'
    state["ran"] = True
    save(state)
    reply({"result": {"type": "ok"}})
elif args == ["pane", "read", "fixture-workspace:p7", "--format", "text"]:
    assert state.get("ran"), "output checked before running command"
    state["read"] = True
    save(state)
    print("fixture output\ntermux-herdr-probe")
elif args == ["pane", "split", "fixture-workspace:p7", "--direction", "right"]:
    assert state.get("read"), "split before successful read"
    state["count"] = 2
    save(state)
    reply({"result": {"type": "pane_info", "pane": {"pane_id": "fixture-workspace:p8"}}})
elif args == ["pane", "list", "--workspace", "fixture-workspace"]:
    reply({"result": {"type": "pane_list", "panes": [{"pane_id": "fixture-workspace:p7"}, {"pane_id": "fixture-workspace:p8"}][:state["count"]]}})
else:
    raise AssertionError("Unexpected fixture CLI operation: " + repr(args))
'''

# Keep CI's documented host requirements unchanged. This narrowly implements
# the JSON selections used by the probe, including the obsolete empty-pane
# selection so a regression back to that flow fails instead of gaining a PTY.
FAKE_JQ = r'''
import json
import sys

args = sys.argv[1:]
while args and args[0].startswith("-"):
    args.pop(0)
query = args.pop(0)
value = json.load(open(args[0])) if args else json.load(sys.stdin)
result = value.get("result", {})
if ".result.root_pane.pane_id" in query:
    value = result.get("root_pane", {}).get("pane_id") if result.get("type") == "workspace_created" else None
elif ".result.workspace.workspace_id" in query:
    value = result.get("workspace", {}).get("workspace_id")
elif ".result.panes[0].pane_id" in query:
    panes = result.get("panes", [])
    value = panes[0].get("pane_id") if panes else None
elif ".result.panes | length >= 2" in query:
    value = len(result.get("panes", [])) >= 2
else:
    print("Unsupported fixture JSON query: " + query, file=sys.stderr)
    sys.exit(2)
if value is None or value is False or value == "":
    sys.exit(1)
if "select(type ==" in query and not isinstance(value, str):
    sys.exit(1)
print(json.dumps(value) if isinstance(value, bool) else value)
'''


class HerdrProbeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="termux-herdr-probe-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.prefix = self.root / "prefix"
        self.repo = self.root / "repo"
        self.observer = self.root / "observer"
        for directory in (self.home, self.prefix / "bin", self.prefix / "tmp", self.repo / "scripts", self.observer):
            directory.mkdir(parents=True)
        (self.root / ".fixture").touch()
        (self.prefix / "bin/bash").symlink_to(shutil.which("bash"))
        for filename in ("tools.sh", "pair.sh"):
            shutil.copy2(SOURCE / "scripts" / filename, self.repo / "scripts" / filename)
        self.env = dict(os.environ, HOME=str(self.home), PREFIX=str(self.prefix),
                        DOTFILES_TEST_ROOT=str(self.root), DOTFILES_TEST_MODE="fixture-only-v1",
                        PATH=str(self.prefix / "bin") + os.pathsep + os.defpath,
                        FIXTURE_OBSERVER=str(self.observer), FIXTURE_ORIGINAL_HOME=str(self.home),
                        HERDR_STARTUP_CWD=str(self.home), HERDR_ENV="1", HERDR_SESSION="external-session",
                        HERDR_PANE_ID="external-pane", HERDR_CLIENT_SOCKET_PATH=str(self.home / "external.sock"))
        self.script("timeout", 'case "$1" in --kill-after=*) shift;; esac\nshift\nexec "$@"\n')
        for name, code in (("herdr", FAKE_HERDR), ("jq", FAKE_JQ)):
            path = self.root / (name + ".py")
            path.write_text(code)
            self.script(name, f'exec {shlex.quote(sys.executable)} {shlex.quote(str(path))} "$@"\n')
        self.user_config = self.home / ".config/herdr/config.toml"
        self.user_config.parent.mkdir(parents=True)
        self.user_config.write_text("# user-owned Herdr configuration\n")
        self.env["HERDR_CONFIG_PATH"] = str(self.user_config)

    def script(self, name, content):
        path = self.prefix / "bin" / name
        path.write_text("#!/bin/sh\nset -eu\n" + content)
        path.chmod(0o755)

    def probe(self, mode="success"):
        result = subprocess.run([str(self.prefix / "bin/bash"), str(self.repo / "scripts/tools.sh"), "probe", "herdr"],
                                env=dict(self.env, FIXTURE_HERDR_MODE=mode), capture_output=True, text=True, timeout=10)
        self.assertEqual(list((self.prefix / "tmp").iterdir()), [])
        self.assertEqual(self.user_config.read_text(), "# user-owned Herdr configuration\n")
        self.assertTrue(json.loads((self.observer / "server.json").read_text())["stopped"])
        self.assertTrue((self.observer / "isolated").exists())
        return result

    def calls(self):
        return [json.loads(line) for line in (self.observer / "calls.jsonl").read_text().splitlines()]

    def test_empty_headless_server_creates_workspace_before_pane_operations(self):
        result = self.probe()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PTY/run/read/split probe passed", result.stdout)
        calls = self.calls()
        create = next(index for index, call in enumerate(calls) if call[:2] == ["workspace", "create"])
        run = next(index for index, call in enumerate(calls) if call[:2] == ["pane", "run"])
        self.assertIn(["pane", "list"], calls[:create])
        self.assertLess(create, run)
        self.assertIn(["pane", "list", "--workspace", "fixture-workspace"], calls)
        self.assertEqual(json.loads((self.observer / "server.json").read_text())["count"], 2)

    def test_workspace_pty_error_is_visible_after_cleanup(self):
        result = self.probe("pty-error")
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("workspace_create_failed", output)
        self.assertIn("fixture PTY allocation denied", output)
        self.assertIn("fixture headless server running", output)
        self.assertFalse(any(call[:2] == ["pane", "run"] for call in self.calls()))

    def test_missing_root_pane_keeps_raw_response_diagnostic_and_fails(self):
        result = self.probe("missing-root")
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("workspace_created", output)
        self.assertIn("fixture-workspace", output)
        self.assertIn("did not contain a pane", output)
        self.assertFalse(any(call[:2] == ["pane", "run"] for call in self.calls()))


if __name__ == "__main__":
    unittest.main()
