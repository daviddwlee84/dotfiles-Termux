"""Host orchestration tests: isolated files, synthetic APKs and a loopback server."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.request
import zipfile

SPEC = importlib.util.spec_from_file_location("termux_host", Path(__file__).resolve().parents[1] / "scripts/host.py")
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)


def key(byte=b"a"):
    blob = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + byte * 32
    return "ssh-ed25519 " + base64.b64encode(blob).decode()


def lp(data):
    return struct.pack("<I", len(data)) + data


def signed_apk(certificate=b"fixture signing certificate", scheme=0x7109871A):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("AndroidManifest.xml", b"fixture")
    data = archive.getvalue()
    eocd = data.rfind(b"PK\x05\x06")
    central = struct.unpack_from("<I", data, eocd + 16)[0]
    signed_data = lp(b"") + lp(lp(certificate)) + lp(b"")
    signer = lp(signed_data) + lp(b"") + lp(b"")
    value = lp(lp(signer))
    entry = struct.pack("<Q", len(value) + 4) + struct.pack("<I", scheme) + value
    size = len(entry) + 24
    block = struct.pack("<Q", size) + entry + struct.pack("<Q", size) + b"APK Sig Block 42"
    end = bytearray(data[eocd:])
    struct.pack_into("<I", end, 16, central + len(block))
    return data[:central] + block + data[central:eocd] + end


def row(data=b"payload"):
    return {"package": "com.termux", "version": "fixture", "version_code": 1,
            "url": "https://example.invalid/termux.apk", "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data), "signer_sha256": hashlib.sha256(b"fixture signing certificate").hexdigest(),
            "activity": "com.termux/.app.TermuxActivity"}


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="termux-host-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_serial_is_required_for_multiple_ready_devices(self):
        devices = [{"serial": "one", "state": "device"}, {"serial": "two", "state": "device"}]
        with self.assertRaisesRegex(host.SetupError, "Several devices"):
            host.select_device(devices)
        self.assertEqual(host.select_device(devices, "two"), "two")

    def test_unauthorized_and_offline_devices_are_not_selected(self):
        for state in ("unauthorized", "offline", "no"):
            with self.subTest(state=state), self.assertRaises(host.SetupError):
                host.select_device([{"serial": "device", "state": state}], "device")
        with self.assertRaises(host.SetupError):
            host.select_device([])

    def test_serial_before_and_after_subcommand(self):
        for command in (["--serial", "one", "setup"], ["setup", "--serial", "one"]):
            self.assertEqual(host.parser().parse_args(command).serial, "one")
        args = host.parser().parse_args(["ssh", "--serial", "one", "--", "printf", "$HOME; touch nope"])
        self.assertEqual(args.command, ["--", "printf", "$HOME; touch nope"])

    def test_adb_remote_shell_quotes_values_once(self):
        value = "a b'\"$HOME;$(touch BAD)"
        with mock.patch.object(host, "run") as run:
            host.Adb("serial").shell("input", "text", value)
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["adb", "-s", "serial", "shell"])
        self.assertEqual(shlex.split(command[4]), ["input", "text", value])

    def test_download_verifies_size_hash_and_reuses_cache(self):
        data = b"verified fixture payload"
        expected = row(data)
        with mock.patch.object(host.urllib.request, "urlopen", return_value=io.BytesIO(data)) as fetch:
            path = host.download_apk(expected, self.root)
        self.assertEqual(path.read_bytes(), data)
        fetch.assert_called_once()
        with mock.patch.object(host.urllib.request, "urlopen", side_effect=AssertionError("cache bypass")):
            self.assertEqual(host.download_apk(expected, self.root), path)

    def test_invalid_download_never_becomes_cached_apk(self):
        for data in (b"wrong", b"too much fixture payload"):
            with self.subTest(data=data), mock.patch.object(host.urllib.request, "urlopen", return_value=io.BytesIO(data)):
                with self.assertRaisesRegex(host.SetupError, "(checksum|size)"):
                    host.download_apk(row(b"right"), self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_apk_v2_and_v3_certificate_extraction(self):
        for scheme in (0x7109871A, 0xF05368C0, 0x1B93AD61):
            with self.subTest(scheme=scheme):
                path = self.root / "fixture.apk"
                path.write_bytes(signed_apk(scheme=scheme))
                self.assertEqual(host.apk_signers(path), {row()["signer_sha256"]})

    def test_malformed_apk_fails_without_trusting_certificates(self):
        path = self.root / "fixture.apk"
        path.write_bytes(signed_apk()[:-5])
        with self.assertRaises(host.SetupError):
            host.apk_signers(path)

    def test_installed_signer_conflict_never_installs_or_uninstalls(self):
        adb = mock.Mock()
        adb.shell.return_value = subprocess.CompletedProcess([], 0, "package:/data/app/base.apk\n", "")

        def pull(*args, **_kwargs):
            self.assertEqual(args[0], "pull")
            Path(args[2]).write_bytes(signed_apk(b"different signing source"))
            return subprocess.CompletedProcess([], 0, "", "")

        adb.call.side_effect = pull
        with self.assertRaisesRegex(host.SetupError, "different signing source"):
            host.install_apk(adb, row(signed_apk()), self.root)
        self.assertEqual(adb.call.call_count, 1)

    def test_newer_compatible_installed_apk_is_retained(self):
        adb = mock.Mock()
        adb.shell.side_effect = [subprocess.CompletedProcess([], 0, "package:/data/app/base.apk\n", ""),
                                 subprocess.CompletedProcess([], 0, "versionCode=9999 targetSdk=28", "")]
        adb.call.side_effect = lambda *args, **kwargs: Path(args[2]).write_bytes(signed_apk())
        with mock.patch.object(host, "download_apk", side_effect=AssertionError("unneeded download")):
            host.install_apk(adb, row(signed_apk()), self.root)
        self.assertEqual(adb.call.call_count, 1)

    def test_mapping_cleanup_only_removes_owned_port_on_failure(self):
        adb = mock.Mock()
        adb.call.return_value = subprocess.CompletedProcess([], 0, "32123\n", "")
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            with host.mapping(adb, "reverse", 43210) as port:
                self.assertEqual(port, 32123)
                raise RuntimeError("fixture")
        self.assertEqual(adb.call.call_args_list,
                         [mock.call("reverse", "tcp:0", "tcp:43210"),
                          mock.call("reverse", "--remove", "tcp:32123", check=False, timeout=10)])

    def test_pairing_pins_key_and_refuses_changed_identity(self):
        receipt = {"status": "ready", "user": "u0_a123", "ssh_port": 8022, "host_key": key()}
        metadata = host.save_pairing(self.root, "serial", receipt)
        before = (self.root / "known_hosts").read_bytes()
        self.assertEqual(host.save_pairing(self.root, "serial", receipt), metadata)
        with self.assertRaisesRegex(host.SetupError, "host key changed"):
            host.save_pairing(self.root, "serial", dict(receipt, host_key=key(b"b")))
        self.assertEqual((self.root / "known_hosts").read_bytes(), before)
        self.assertEqual((self.root / "device.json").stat().st_mode & 0o777, 0o600)

    def test_callback_fields_reject_shell_and_port_injection(self):
        receipt = {"status": "ready", "user": "u0_a123", "ssh_port": 8022, "host_key": key()}
        for override in ({"user": "user; touch nope"}, {"ssh_port": "8022;nope"}, {"host_key": "not a key"}):
            with self.subTest(override=override), self.assertRaises(host.SetupError):
                host.save_pairing(self.root, "serial", dict(receipt, **override))

    def test_server_limits_paths_and_accepts_one_result(self):
        with host.PairingServer() as server:
            server.payload = b"fixture payload"
            base = f"http://127.0.0.1:{server.port}"
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + "/not-the-token")
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
            with urllib.request.urlopen(base + f"/{server.nonce}/payload") as response:
                self.assertEqual(response.read(), b"fixture payload")
            request = urllib.request.Request(base + f"/{server.nonce}/result",
                                             data=b'{"status":"error"}', method="POST")
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 204)
            self.assertTrue(server.done.wait(1))
            self.assertEqual(server.receipt, {"status": "error"})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request)
            error.exception.close()

    def test_capsule_is_valid_bash_with_public_key_and_callback_args(self):
        script = 'printf "%s\\n" "$@"\n'
        output = host.capsule(script, key(), "http://127.0.0.1:12345/abcdef/result", "lan", 8022)
        result = subprocess.run(["bash", "-n"], input=output, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"--authorized-key-file", output)
        self.assertNotIn(b"PRIVATE KEY", output)

    def test_bootstrap_command_is_single_ascii_line_and_checked(self):
        command = host.bootstrap_command("http://127.0.0.1:12345/abcdef/payload", "a" * 64)
        self.assertTrue(command.isascii())
        self.assertNotIn("%", command)
        self.assertNotIn("\n", command)
        self.assertLess(command.index("sha256sum -c -"), command.index('bash "$dft_bootstrap_file"'))
        result = subprocess.run(["bash", "-n"], input=command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaises(host.SetupError):
            host.bootstrap_command("http://127.0.0.1:1/a/payload;touch BAD", "a" * 64)

    def test_idle_shell_requires_one_new_bash_without_children(self):
        before = {1: (0, "com.termux"), 2: (1, "bash"), 3: (2, "vim")}
        after = dict(before, **{})
        after[4] = (1, "bash")
        self.assertEqual(host.new_idle_bash(before, after), 4)
        after[5] = (4, "claude")
        self.assertIsNone(host.new_idle_bash(before, after))
        self.assertIsNone(host.new_idle_bash(before, before))

    def test_ui_failure_never_sends_text_to_existing_session(self):
        adb = mock.Mock()
        with mock.patch.object(host, "launch_activity"), \
             mock.patch.object(host, "foreground_termux", return_value=True), \
             mock.patch.object(host, "ui_dump", side_effect=host.SetupError("locked")):
            self.assertFalse(host.try_ui_bootstrap(adb, "com.termux/.app.TermuxActivity", "harmless"))
        self.assertFalse(any(call.args[:2] == ("input", "text") for call in adb.shell.call_args_list))

    def test_ssh_uses_strict_dedicated_trust(self):
        metadata = {"host_alias": "fixture", "user": "u0_a123"}
        command = host.ssh_arguments(self.root, metadata, 30222)
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertIn(f"UserKnownHostsFile={self.root / 'known_hosts'}", command)
        self.assertIn("HostKeyAlias=fixture", command)
        self.assertEqual(command[-1], "u0_a123@127.0.0.1")

    def test_device_lock_does_not_allow_concurrent_mutations(self):
        with host.device_lock(self.root):
            with self.assertRaisesRegex(host.SetupError, "already using"):
                with host.device_lock(self.root):
                    self.fail("lock should prevent entry")

    def test_launcher_resolution_prefers_installed_component(self):
        adb = mock.Mock()
        adb.shell.return_value = subprocess.CompletedProcess([], 0, "com.termux/.ChangedActivity\n", "")
        self.assertEqual(host.resolve_activity(adb, row()), "com.termux/.ChangedActivity")
        adb.shell.return_value = subprocess.CompletedProcess([], 1, "No activity found\n", "")
        self.assertEqual(host.resolve_activity(adb, row()), "com.termux/.app.TermuxActivity")

    def test_activity_error_with_zero_exit_status_is_failure(self):
        adb = mock.Mock()
        adb.shell.return_value = subprocess.CompletedProcess([], 0, "Error type 3\nError: Activity does not exist", "")
        with self.assertRaisesRegex(host.SetupError, "could not open"):
            host.launch_activity(adb, "com.termux/.Missing")

    def test_existing_key_symlink_is_preserved(self):
        destination = self.root / "foreign-private-key"
        destination.write_text("untouched")
        (self.root / "id_ed25519").symlink_to(destination)
        with self.assertRaisesRegex(host.SetupError, "symlinks"):
            host.ensure_identity(self.root)
        self.assertEqual(destination.read_text(), "untouched")

    def test_default_setup_does_not_override_device_choices(self):
        args = host.parser().parse_args(["setup"])
        self.assertEqual(host.setup_options(args), ["--non-interactive"])
        args = host.parser().parse_args(["setup", "--no-boot", "--wake-lock", "--ssh-port", "9922",
                                        "--install-ssh-server", "false", "--install-coding-agents", "false"])
        options = host.setup_options(args)
        self.assertIn("9922", options)
        self.assertNotIn("--ssh-mode", options)
        self.assertEqual(options[options.index("--install-ssh-server") + 1], "false")
        self.assertEqual(options[options.index("--install-coding-agents") + 1], "false")

    def test_pairing_without_explicit_settings_uses_target_defaults(self):
        result = host.capsule("true", key(), "http://127.0.0.1:12345/abcdef/result", None, None)
        self.assertNotIn(b"--ssh-mode", result)
        self.assertNotIn(b"--ssh-port", result)

    def test_final_report_updates_port_mode_and_disabled_state(self):
        initial = {"status": "ready", "user": "u0_a123", "ssh_port": 8022, "host_key": key()}
        host.save_pairing(self.root, "serial", initial)
        report = "logs before\nMARKER\tu0_a123\t9922\tadb\tfalse\tfalse\ttrue\tfalse\t" + key() + "\n"
        receipt = host.parse_target_state(report, "MARKER")
        metadata = host.save_pairing(self.root, "serial", receipt)
        self.assertEqual(metadata["ssh_port"], 9922)
        self.assertEqual(metadata["ssh_mode"], "adb")
        self.assertFalse(metadata["install_ssh_server"])
        self.assertTrue(metadata["termux_wake_lock"])

    def test_resume_uses_saved_ssh_without_needing_finished_source(self):
        metadata = host.save_pairing(self.root, "serial",
                                     {"status": "ready", "user": "u0_a123", "ssh_port": 8022, "host_key": key()})
        adb = mock.Mock(serial="serial")
        responses = [subprocess.CompletedProcess([], 0, "", ""),
                     subprocess.CompletedProcess([], 1, "", "source not installed yet")]
        with mock.patch.object(host, "mapping", return_value=contextlib.nullcontext(30222)), \
             mock.patch.object(host, "run", side_effect=responses) as run:
            self.assertEqual(host.resume_pairing(adb, self.root), metadata)
        self.assertEqual(run.call_args_list[0].args[0][-1], "true")

    def test_setup_resumes_without_ui_and_keeps_saved_boot_disabled(self):
        args = host.parser().parse_args(["setup", "--state-dir", str(self.root)])
        metadata = {"install_termux_boot": False, "install_ssh_server": True, "ssh_mode": "adb", "ssh_port": 9922}
        adb = mock.Mock(serial="fixture")
        adb.shell.side_effect = [subprocess.CompletedProcess([], 0, "1\n", ""),
                                 subprocess.CompletedProcess([], 0, "35\n", "")]
        rows = {name: dict(row(), package=name) for name in ("fdroid", "termux", "boot", "api")}
        with mock.patch.object(host, "read_lock", return_value=rows), \
             mock.patch.object(host, "resume_pairing", return_value=metadata), \
             mock.patch.object(host, "install_apk") as install, \
             mock.patch.object(host, "try_ui_bootstrap", side_effect=AssertionError("must not type")), \
             mock.patch.object(host, "full_setup", return_value=metadata):
            host.setup(adb, args)
        self.assertEqual([call.args[1]["package"] for call in install.call_args_list], ["fdroid", "termux"])

    def test_doctor_without_device_still_reports_host_dependencies(self):
        output = io.StringIO()
        with mock.patch.object(host, "list_devices", return_value=[]), contextlib.redirect_stdout(output):
            self.assertEqual(host.main(["doctor"]), 1)
        self.assertIn("Host:", output.getvalue())
        self.assertIn("No authorized device", output.getvalue())

    def test_streaming_remote_result_keeps_progress_and_final_marker(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = host.run_streaming(["bash", "-s"], input="echo progress; echo FINAL\n", timeout=10)
        self.assertIn("progress", output.getvalue())
        self.assertIn("FINAL", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_same_session_report_is_valid_bash(self):
        result = subprocess.run(["bash", "-n"], input=host.target_state_script("MARKER"), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_streaming_failure_retains_output_and_original_status(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = host.run_streaming(["bash", "-s"], input="echo FINAL; exit 8\n", timeout=10)
        self.assertEqual(result.returncode, 8)
        self.assertIn("FINAL", result.stdout)

    def test_partial_setup_failure_saves_final_ssh_configuration(self):
        args = host.parser().parse_args(["setup", "--ssh-port", "9922"])
        initial = host.save_pairing(self.root, "serial",
                                   {"status": "ready", "user": "u0_a123", "ssh_port": 8022, "host_key": key()})
        adb = mock.Mock(serial="serial")

        device_home = self.root / "device-home"
        source = device_home / ".local/share/dotfiles-Termux/scripts"
        source.mkdir(parents=True)
        (source / "pair.sh").write_text(
            'termux_context() { PREFIX="$HOME/prefix"; }\n'
            'termux_defaults() { SSH_PORT=9922; SSH_MODE=adb; INSTALL_SSH=true; INSTALL_BOOT=false; '
            'WAKE_LOCK=false; INSTALL_AGENTS=true; }\n'
            'termux_validate_settings() { true; }\n')
        key_dir = device_home / "prefix/etc/ssh"
        key_dir.mkdir(parents=True)
        (key_dir / "ssh_host_ed25519_key.pub").write_text(key())
        (self.root / "bootstrap.sh").write_text('echo "optional tool failed after SSH configuration"; exit 8\n')

        def partial_failure(argv, **_kwargs):
            script = shlex.split(argv[-1])[-1]
            return subprocess.run(["bash", "-c", script], input=_kwargs["input"], text=True,
                                  capture_output=True, env=dict(os.environ, HOME=str(device_home)))

        with mock.patch.object(host, "mapping", return_value=contextlib.nullcontext(30222)), \
             mock.patch.object(host, "run", return_value=subprocess.CompletedProcess([], 0, "", "")), \
             mock.patch.object(host, "ROOT", self.root), \
             mock.patch.object(host, "run_streaming", side_effect=partial_failure):
            with self.assertRaisesRegex(host.SetupError, "status 8; final SSH configuration was saved"):
                host.full_setup(adb, self.root, initial, args)
        final = json.loads((self.root / "device.json").read_text())
        self.assertEqual(final["ssh_port"], 9922)
        self.assertEqual(final["ssh_mode"], "adb")
        self.assertFalse(final["install_termux_boot"])

    def test_resume_host_key_mismatch_stops_instead_of_provisioning(self):
        host.save_pairing(self.root, "serial",
                          {"status": "ready", "user": "u0_a123", "ssh_port": 8022, "host_key": key()})
        adb = mock.Mock(serial="serial")
        for message in ("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!", "Host key verification failed."):
            with self.subTest(message=message), \
                 mock.patch.object(host, "mapping", return_value=contextlib.nullcontext(30222)), \
                 mock.patch.object(host, "run", return_value=subprocess.CompletedProcess([], 255, "", message)):
                with self.assertRaisesRegex(host.SetupError, "No UI re-pairing was attempted"):
                    host.resume_pairing(adb, self.root)

    def test_adb_timeout_distinguishes_host_startup_from_device_authorization(self):
        with mock.patch.object(host.subprocess, "run", side_effect=subprocess.TimeoutExpired("adb", 1)):
            with self.assertRaisesRegex(host.SetupError, "host ADB startup/permissions separately"):
                host.run(["adb", "devices"], timeout=1)

    def test_foreground_requires_actual_focused_termux_window_on_primary_display(self):
        adb = mock.Mock()
        activity = "topResumedActivity=ActivityRecord{abcd u0 com.termux/.app.TermuxActivity t20}\n"
        focused = "mCurrentFocus=Window{ef01 u0 com.termux/com.termux.app.TermuxActivity}\nmTopFocusedDisplayId=0\n"
        adb.shell.side_effect = [subprocess.CompletedProcess([], 0, activity, ""),
                                 subprocess.CompletedProcess([], 0, focused, "")]
        self.assertTrue(host.foreground_termux(adb))
        self.assertEqual(adb.shell.call_args.args, ("dumpsys", "window"))

    def test_split_screen_resumed_termux_does_not_allow_input_to_other_window(self):
        adb = mock.Mock()
        activity = "mResumedActivity=ActivityRecord{abcd u0 com.termux/.app.TermuxActivity t20}\n"
        focused = "mCurrentFocus=Window{ef01 u0 com.android.settings/.Settings}\nmTopFocusedDisplayId=0\n"
        adb.shell.side_effect = [subprocess.CompletedProcess([], 0, activity, ""),
                                 subprocess.CompletedProcess([], 0, focused, "")]
        self.assertFalse(host.foreground_termux(adb))

    def test_top_resumed_other_app_rejects_stale_resumed_termux(self):
        adb = mock.Mock()
        activity = ("topResumedActivity=ActivityRecord{aaaa u0 com.android.settings/.Settings t21}\n"
                    "mResumedActivity=ActivityRecord{abcd u0 com.termux/.app.TermuxActivity t20}\n")
        adb.shell.return_value = subprocess.CompletedProcess([], 0, activity, "")
        self.assertFalse(host.foreground_termux(adb))
        self.assertEqual(adb.shell.call_count, 1)

    def test_unknown_focus_fields_and_secondary_display_fall_back_to_manual(self):
        activity = "topResumedActivity=ActivityRecord{abcd u0 com.termux/.app.TermuxActivity t20}\n"
        for windows in ("", "mCurrentFocus=null\nmTopFocusedDisplayId=0\n",
                        "mCurrentFocus=Window{ef01 u0 com.termux/.app.TermuxActivity}\n",
                        "mCurrentFocus=Window{ef01 u0 com.termux/.app.TermuxActivity}\nmTopFocusedDisplayId=2\n"):
            with self.subTest(windows=windows):
                adb = mock.Mock()
                adb.shell.side_effect = [subprocess.CompletedProcess([], 0, activity, ""),
                                         subprocess.CompletedProcess([], 0, windows, "")]
                self.assertFalse(host.foreground_termux(adb))


if __name__ == "__main__":
    unittest.main()
