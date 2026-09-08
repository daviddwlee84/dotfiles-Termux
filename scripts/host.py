#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pair and maintain a native Termux environment over an authorized USB device."""
from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import hashlib
import http.server
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shlex
import shutil
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "dotfiles-termux"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class SetupError(RuntimeError):
    """An actionable setup failure; never an invitation to reset app data."""


def run(argv, *, check=True, timeout=120, input=None, capture=True):
    try:
        result = subprocess.run([str(arg) for arg in argv], input=input, text=True,
                                stdout=subprocess.PIPE if capture else None,
                                stderr=subprocess.PIPE if capture else None,
                                timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise SetupError(f"Missing {argv[0]}; run sh scripts/host-deps.sh --install.") from exc
    except subprocess.TimeoutExpired as exc:
        if Path(str(argv[0])).name == "adb":
            raise SetupError("ADB timed out on this computer. Check host ADB startup/permissions separately "
                             "from the device's USB connection and authorization prompt.") from exc
        raise SetupError(f"{argv[0]} timed out; rerun after checking the device.") from exc
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "command failed").strip()
        raise SetupError(f"{argv[0]}: {detail}")
    return result


class Adb:
    def __init__(self, serial):
        if not serial or any(ord(char) < 32 for char in serial):
            raise SetupError("Invalid device serial.")
        self.serial = serial

    def call(self, *args, **kwargs):
        return run(["adb", "-s", self.serial, *args], **kwargs)

    def shell(self, *args, **kwargs):
        # adb's remote shell is a second quoting boundary, even with host argv.
        return self.call("shell", shlex.join(str(arg) for arg in args), **kwargs)


def list_devices():
    result = run(["adb", "devices", "-l"])
    devices = []
    for line in result.stdout.splitlines():
        if not line.strip() or line.startswith(("List of devices", "*")):
            continue
        fields = line.split()
        if len(fields) >= 2:
            devices.append({"serial": fields[0], "state": fields[1], "details": " ".join(fields[2:])})
    return devices


def select_device(devices, serial=None):
    if serial:
        matches = [device for device in devices if device["serial"] == serial]
        if not matches:
            raise SetupError(f"Device {serial} is not attached.")
        if matches[0]["state"] != "device":
            raise SetupError(f"Device {serial} is {matches[0]['state']}; unlock it and authorize USB debugging.")
        return serial
    ready = [device for device in devices if device["state"] == "device"]
    if len(ready) == 1:
        return ready[0]["serial"]
    if len(ready) > 1:
        raise SetupError("Several devices are authorized; choose one with --serial SERIAL.")
    states = ", ".join(f"{d['serial']} ({d['state']})" for d in devices) or "none attached"
    raise SetupError(f"No authorized device: {states}. Enable USB debugging and accept the device prompt.")


def read_lock(path):
    lock = json.loads(path.read_text())
    if lock.get("schema") != 1 or not isinstance(lock.get("apks"), dict):
        raise SetupError("Unsupported APK lock schema; expected schema=1 and an apks object.")
    for name, row in lock["apks"].items():
        required = {"package", "version", "version_code", "url", "sha256", "size", "signer_sha256", "activity"}
        if not isinstance(row, dict) or not required <= row.keys():
            raise SetupError(f"Incomplete APK lock entry: {name}")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]+", row["package"]):
            raise SetupError(f"Invalid APK package: {name}")
        if not HEX64.fullmatch(row["sha256"]) or not HEX64.fullmatch(row["signer_sha256"]):
            raise SetupError(f"Invalid APK checksum or signer: {name}")
        if not row["url"].startswith("https://") or not isinstance(row["size"], int) or row["size"] <= 0:
            raise SetupError(f"Invalid APK URL/size: {name}")
        if not isinstance(row["version_code"], int):
            raise SetupError(f"Invalid version_code: {name}")
    return lock["apks"]


def verify_file(path, row):
    if not path.is_file() or path.stat().st_size != row["size"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"]


def download_apk(row, cache):
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = cache / f"{row['package']}-{row['sha256']}.apk"
    if verify_file(destination, row):
        return destination
    fd, temporary = tempfile.mkstemp(prefix="apk-", dir=cache)
    try:
        count = 0
        digest = hashlib.sha256()
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(row["url"], timeout=60) as source:
            while block := source.read(1024 * 1024):
                count += len(block)
                if count > row["size"]:
                    raise SetupError("APK download exceeds its pinned size.")
                digest.update(block)
                output.write(block)
        if count != row["size"] or digest.hexdigest() != row["sha256"]:
            raise SetupError("APK checksum/size mismatch; no installation performed.")
        os.replace(temporary, destination)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
    return destination


def length_prefixed(data, offset=0):
    if offset + 4 > len(data):
        raise SetupError("Truncated APK signature data.")
    size = struct.unpack_from("<I", data, offset)[0]
    end = offset + 4 + size
    if end > len(data):
        raise SetupError("Invalid APK signature length.")
    return data[offset + 4:end], end


def apk_signers(path):
    """Read signing certificates, not verify signatures (the lock pins APK bytes).

    Android verifies installed APK signatures. Read v2/v3 signer certificates
    directly; legacy v1 PKCS7 containers use the host's openssl command.
    """
    data = path.read_bytes()
    eocd = data.rfind(b"PK\x05\x06", max(0, len(data) - 65557))
    if eocd < 0 or eocd + 22 > len(data):
        raise SetupError("APK has no valid ZIP end record.")
    comment_size = struct.unpack_from("<H", data, eocd + 20)[0]
    if eocd + 22 + comment_size != len(data):
        raise SetupError("Malformed APK ZIP end record.")
    central = struct.unpack_from("<I", data, eocd + 16)[0]
    fingerprints = set()
    if 24 <= central <= len(data) and data[central - 16:central] == b"APK Sig Block 42":
        size = struct.unpack_from("<Q", data, central - 24)[0]
        start = central - size - 8
        if size < 24 or start < 0 or struct.unpack_from("<Q", data, start)[0] != size:
            raise SetupError("Malformed APK signing block.")
        offset = start + 8
        while offset < central - 24:
            if offset + 8 > central - 24:
                raise SetupError("Truncated APK signing block entry.")
            pair_size = struct.unpack_from("<Q", data, offset)[0]
            end = offset + 8 + pair_size
            if pair_size < 4 or end > central - 24:
                raise SetupError("Invalid APK signing block entry.")
            identifier = struct.unpack_from("<I", data, offset + 8)[0]
            if identifier in (0x7109871A, 0xF05368C0, 0x1B93AD61):
                signers, _ = length_prefixed(data[offset + 12:end])
                signer_offset = 0
                while signer_offset < len(signers):
                    signer, signer_offset = length_prefixed(signers, signer_offset)
                    signed, _ = length_prefixed(signer)
                    _, signed_offset = length_prefixed(signed)
                    certificates, _ = length_prefixed(signed, signed_offset)
                    certificate, _ = length_prefixed(certificates)
                    fingerprints.add(hashlib.sha256(certificate).hexdigest())
            offset = end
    if fingerprints:
        return fingerprints
    with zipfile.ZipFile(path) as archive:
        signatures = [name for name in archive.namelist()
                      if re.fullmatch(r"META-INF/[^/]+\.(RSA|DSA|EC)", name, re.IGNORECASE)]
        for name in signatures:
            with tempfile.NamedTemporaryFile(suffix=".der") as signature:
                signature.write(archive.read(name))
                signature.flush()
                result = run(["openssl", "pkcs7", "-inform", "DER", "-in", signature.name, "-print_certs"])
                for pem in re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                                      result.stdout, flags=re.DOTALL):
                    fingerprints.add(hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest())
    if not fingerprints:
        raise SetupError("Could not determine APK signing certificate; preserving existing app data.")
    return fingerprints


def install_apk(adb, row, cache):
    result = adb.shell("pm", "path", row["package"], check=False)
    paths = [line.removeprefix("package:").strip() for line in result.stdout.splitlines()
             if line.startswith("package:")]
    if paths:
        path = next((item for item in paths if item.endswith("/base.apk")), paths[0])
        with tempfile.TemporaryDirectory(prefix="termux-installed-apk-") as directory:
            installed = Path(directory) / "base.apk"
            adb.call("pull", path, installed)
            if row["signer_sha256"] not in apk_signers(installed):
                raise SetupError(f"{row['package']} has a different signing source. Existing app/data kept; "
                                 "use the matching Termux/plugin source or back up and migrate manually.")
        info = adb.shell("dumpsys", "package", row["package"]).stdout
        version = re.search(r"\bversionCode=(\d+)", info)
        if version and int(version.group(1)) >= row["version_code"]:
            print(f"{row['package']}: compatible installed version retained.", flush=True)
            return
    print(f"Installing verified {row['package']} {row['version']}…", flush=True)
    apk = download_apk(row, cache)
    if row["signer_sha256"] not in apk_signers(apk):
        raise SetupError(f"Pinned APK signer mismatch: {row['package']}")
    adb.call("install", "-r", apk, timeout=180)


def resolve_activity(adb, row):
    result = adb.shell("cmd", "package", "resolve-activity", "--brief", "-a", "android.intent.action.MAIN",
                       "-c", "android.intent.category.LAUNCHER", "-p", row["package"], check=False)
    pattern = re.compile(re.escape(row["package"]) + r"/[A-Za-z0-9_.]+\Z")
    for line in result.stdout.splitlines():
        if pattern.fullmatch(line.strip()):
            return line.strip()
    if not pattern.fullmatch(row["activity"]):
        raise SetupError(f"No valid launch activity for {row['package']}.")
    return row["activity"]


def launch_activity(adb, activity):
    result = adb.shell("am", "start", "-W", "-n", activity, timeout=30)
    if re.search(r"(?:^|\n)(?:Error|Exception|Permission Denial)", result.stdout):
        raise SetupError(f"Android could not open {activity}; open the app from its launcher.")


def state_for(base, serial):
    return base / "devices" / hashlib.sha256(serial.encode()).hexdigest()[:24]


@contextlib.contextmanager
def device_lock(state):
    if state.is_symlink() or state.parent.is_symlink() or (state / "lock").is_symlink():
        raise SetupError("Refusing a symlink in the dedicated device state.")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    with (state / "lock").open("a+") as lock:
        os.chmod(lock.name, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SetupError("Another helper is already using this device.") from exc
        yield


def normalized_key(value):
    fields = value.strip().split()
    if len(fields) < 2 or fields[0] != "ssh-ed25519":
        raise SetupError("Expected an Ed25519 public key.")
    try:
        blob = base64.b64decode(fields[1], validate=True)
        name_size = struct.unpack_from(">I", blob, 0)[0]
        name = blob[4:4 + name_size]
        key_offset = 4 + name_size
        key_size = struct.unpack_from(">I", blob, key_offset)[0]
        if name != b"ssh-ed25519" or key_size != 32 or key_offset + 4 + key_size != len(blob):
            raise ValueError("wrong key format")
    except (ValueError, struct.error) as exc:
        raise SetupError("Malformed Ed25519 public key.") from exc
    return f"{fields[0]} {fields[1]}"


def ensure_identity(state):
    identity = state / "id_ed25519"
    public = Path(str(identity) + ".pub")
    if identity.is_symlink() or public.is_symlink():
        raise SetupError("Pairing key symlinks are preserved; use a private dedicated state directory.")
    if not identity.exists():
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "dotfiles-termux", "-f", identity])
    identity.chmod(0o600)
    if not public.exists():
        public.write_text(run(["ssh-keygen", "-y", "-f", identity]).stdout)
    public.chmod(0o600)
    return normalized_key(public.read_text())


def save_pairing(state, serial, receipt):
    if receipt.get("status") != "ready":
        raise SetupError("Pairing failed on the device; inspect the Termux terminal, then rerun setup.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", str(receipt.get("user", ""))):
        raise SetupError("Invalid username in pairing result.")
    port = receipt.get("ssh_port")
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise SetupError("Invalid SSH port in pairing result.")
    host_key = normalized_key(receipt.get("host_key", ""))
    metadata_path = state / "device.json"
    known_hosts = state / "known_hosts"
    if metadata_path.is_symlink() or known_hosts.is_symlink():
        raise SetupError("Pairing trust symlinks are preserved.")
    if metadata_path.exists():
        previous = json.loads(metadata_path.read_text())
        if previous.get("host_key") != host_key:
            raise SetupError("Device SSH host key changed. Existing trust kept; investigate before re-pairing.")
    metadata = {"serial": serial, "user": receipt["user"], "ssh_port": port, "host_key": host_key,
                "host_alias": f"dotfiles-termux-{state.name}"}
    if "ssh_mode" in receipt:
        if receipt["ssh_mode"] not in ("lan", "adb"):
            raise SetupError("Invalid SSH mode in target state.")
        metadata["ssh_mode"] = receipt["ssh_mode"]
    for field in ("install_ssh_server", "install_termux_boot", "termux_wake_lock", "install_coding_agents"):
        if field in receipt:
            if not isinstance(receipt[field], bool):
                raise SetupError("Invalid boolean in target state.")
            metadata[field] = receipt[field]
    expected = f"{metadata['host_alias']} {host_key}\n"
    if known_hosts.exists() and known_hosts.read_text() != expected:
        raise SetupError("Dedicated known_hosts differs from the pairing result; existing trust kept.")
    known_hosts.write_text(expected)
    known_hosts.chmod(0o600)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    metadata_path.chmod(0o600)
    return metadata


class PairingServer:
    def __init__(self):
        self.nonce = secrets.token_hex(24)
        self.payload = b""
        self.receipt = None
        self.done = threading.Event()
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass  # Do not persist callback tokens or key material.

            def do_GET(self):
                if self.path != f"/{owner.nonce}/payload":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(owner.payload)))
                self.end_headers()
                self.wfile.write(owner.payload)

            def do_POST(self):
                if self.path != f"/{owner.nonce}/result" or owner.done.is_set():
                    self.send_error(404)
                    return
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 8192:
                        raise ValueError("invalid size")
                    self.connection.settimeout(5)
                    receipt = json.loads(self.rfile.read(size))
                    if not isinstance(receipt, dict) or receipt.get("status") not in ("ready", "error"):
                        raise ValueError("invalid result")
                except (ValueError, TimeoutError):
                    self.send_error(400)
                    return
                owner.receipt = receipt
                owner.done.set()
                self.send_response(204)
                self.end_headers()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def port(self):
        return self.server.server_port

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def capsule(pair_script, public_key, callback, mode, port):
    delimiter = "DOTFILES_PAIR_" + secrets.token_hex(16)
    if delimiter in pair_script:
        raise SetupError("Unexpected pairing script delimiter collision.")
    options = ["--callback-url", callback]
    if mode is not None:
        options += ["--ssh-mode", mode]
    if port is not None:
        options += ["--ssh-port", str(port)]
    invocation = shlex.join(options)
    return ("#!/usr/bin/env bash\nset -eu\n"
            'dft_pair_dir=$(mktemp -d)\ntrap \'rm -rf "$dft_pair_dir"\' EXIT\n'
            f'cat > "$dft_pair_dir/key.pub" <<\'{delimiter}_KEY\'\n{public_key}\n{delimiter}_KEY\n'
            f'cat > "$dft_pair_dir/pair.sh" <<\'{delimiter}\'\n{pair_script}\n{delimiter}\n'
            f'bash "$dft_pair_dir/pair.sh" --authorized-key-file "$dft_pair_dir/key.pub" {invocation}\n').encode()


def bootstrap_command(url, digest):
    if not HEX64.fullmatch(digest) or not re.fullmatch(r"http://127\.0\.0\.1:\d+/[0-9a-f]+/payload", url):
        raise SetupError("Invalid local bootstrap URL or checksum.")
    return ('dft_bootstrap_file=$(mktemp); '
            f'curl -fSs --max-time 60 {url} -o "$dft_bootstrap_file" && '
            f'echo {digest}\"  $dft_bootstrap_file\" | sha256sum -c - && '
            'bash "$dft_bootstrap_file"; rm -f "$dft_bootstrap_file"')


def ui_dump(adb):
    path = f"/data/local/tmp/dotfiles-termux-{secrets.token_hex(8)}.xml"
    try:
        adb.shell("uiautomator", "dump", path, timeout=20)
        output = adb.call("exec-out", "cat", path, timeout=10).stdout
        return ET.fromstring(output[output.index("<?xml"):])
    finally:
        adb.shell("rm", "-f", path, check=False, timeout=10)


def node_bounds(node):
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", ""))
    if not match:
        raise SetupError("Cannot determine Termux control bounds.")
    return tuple(int(value) for value in match.groups())


def terminal_node(tree):
    return next((node for node in tree.iter("node")
                 if node.get("resource-id") == "com.termux:id/terminal_view"
                 or (node.get("package") == "com.termux" and node.get("class") == "com.termux.view.TerminalView")), None)


def foreground_termux(adb):
    text = adb.shell("dumpsys", "activity", "activities", timeout=10).stdout
    return any(re.search(r"(?:mResumedActivity|topResumedActivity).*\bcom\.termux/", line)
               for line in text.splitlines())


def termux_processes(adb):
    package = adb.shell("cmd", "package", "list", "packages", "-U", "com.termux").stdout
    match = re.search(r"package:com\.termux\s+uid:(\d+)", package)
    if not match:
        raise SetupError("Cannot verify Termux application UID.")
    uid = int(match.group(1))
    processes = {}
    output = adb.shell("ps", "-A", "-o", "UID,PID,PPID,NAME").stdout
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 4 and all(field.isdigit() for field in fields[:3]) and int(fields[0]) == uid:
            processes[int(fields[1])] = (int(fields[2]), fields[3])
    if not processes:
        raise SetupError("Android did not expose Termux process information.")
    return processes


def new_idle_bash(before, after):
    added = {pid: row for pid, row in after.items() if pid not in before}
    shells = [pid for pid, (_, name) in added.items() if name.rsplit("/", 1)[-1] in ("bash", "-bash")]
    if len(shells) != 1:
        return None
    shell = shells[0]
    if any(parent == shell for parent, _ in after.values()):
        return None
    return shell


def try_ui_bootstrap(adb, activity, command):
    """Only send text after a new app-owned, idle Bash session is observed."""
    try:
        launch_activity(adb, activity)
        deadline = time.monotonic() + 90
        terminal = None
        while time.monotonic() < deadline:
            if foreground_termux(adb):
                terminal = terminal_node(ui_dump(adb))
                if terminal is not None:
                    break
            time.sleep(2)
        if terminal is None:
            raise SetupError("Termux is not ready or a system dialog covers the terminal.")
        before = termux_processes(adb)
        x1, y1, x2, y2 = node_bounds(terminal)
        adb.shell("input", "swipe", str(max(1, x1 + 1)), str((y1 + y2) // 2),
                  str(x1 + (x2 - x1) * 3 // 4), str((y1 + y2) // 2), "300")
        tree = ui_dump(adb)
        button = next((node for node in tree.iter("node")
                       if node.get("resource-id") == "com.termux:id/new_session_button"
                       and node.get("enabled") == "true"), None)
        if button is None:
            raise SetupError("Cannot verify the New session control.")
        x1, y1, x2, y2 = node_bounds(button)
        adb.shell("input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
        time.sleep(2)
        after = termux_processes(adb)
        shell = new_idle_bash(before, after)
        if shell is None:
            raise SetupError("A new idle Bash shell could not be verified.")
        time.sleep(1)
        if new_idle_bash(before, termux_processes(adb)) != shell or not foreground_termux(adb):
            raise SetupError("Termux session changed before input.")
        tree = ui_dump(adb)
        terminal = terminal_node(tree)
        if terminal is None or terminal.get("focused") != "true":
            raise SetupError("The new terminal is not focused.")
        if "%" in command or "\n" in command or not command.isascii():
            raise SetupError("Bootstrap input is not in the supported ASCII alphabet.")
        adb.shell("input", "text", command.replace(" ", "%s"), timeout=30)
        if not foreground_termux(adb):
            raise SetupError("Focus changed during input; press Enter manually in the new Termux shell.")
        adb.shell("input", "keyevent", "KEYCODE_ENTER")
        return True
    except (SetupError, ET.ParseError, ValueError) as exc:
        print(f"Automatic terminal input unavailable: {exc}", flush=True)
        return False


@contextlib.contextmanager
def mapping(adb, direction, destination):
    result = adb.call(direction, "tcp:0", f"tcp:{destination}")
    port = result.stdout.strip()
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise SetupError(f"ADB returned an invalid {direction} port.")
    try:
        yield int(port)
    finally:
        adb.call(direction, "--remove", f"tcp:{port}", check=False, timeout=10)


def ssh_arguments(state, metadata, port):
    return ["ssh", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=10", "-o", f"UserKnownHostsFile={state / 'known_hosts'}",
            "-o", f"HostKeyAlias={metadata['host_alias']}", "-i", str(state / "id_ed25519"),
            "-p", str(port), f"{metadata['user']}@127.0.0.1"]


def target_state_script(marker):
    # pair.sh validates values read from rendered settings; no user values are
    # interpolated into executable shell text. Keep reporting in the same SSH
    # connection so a listener port change or stop does not lose the result.
    return ('source "$HOME/.local/share/dotfiles-Termux/scripts/pair.sh" || exit; '
            'termux_context && termux_defaults && termux_validate_settings || exit; '
            'dft_host_key=$(awk \'NR==1 {print $1 " " $2}\' "$PREFIX/etc/ssh/ssh_host_ed25519_key.pub") || exit; '
            f"printf '{marker}\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n' "
            '"$(id -un)" "$SSH_PORT" "$SSH_MODE" "$INSTALL_SSH" "$INSTALL_BOOT" '
            '"$WAKE_LOCK" "$INSTALL_AGENTS" "$dft_host_key"')


def parse_target_state(output, marker):
    lines = [line for line in output.splitlines() if line.startswith(marker + "\t")]
    if len(lines) != 1:
        raise SetupError("Target did not report its final SSH configuration; existing host state preserved.")
    fields = lines[0].split("\t")
    if len(fields) != 9 or not fields[2].isdigit() or any(value not in ("true", "false") for value in fields[4:8]):
        raise SetupError("Malformed target state report.")
    return {"status": "ready", "user": fields[1], "ssh_port": int(fields[2]), "ssh_mode": fields[3],
            "install_ssh_server": fields[4] == "true", "install_termux_boot": fields[5] == "true",
            "termux_wake_lock": fields[6] == "true", "install_coding_agents": fields[7] == "true",
            "host_key": fields[8]}


def load_pairing(state):
    path = state / "device.json"
    if not path.exists():
        return None
    if path.is_symlink() or (state / "known_hosts").is_symlink() or (state / "id_ed25519").is_symlink():
        raise SetupError("Dedicated SSH state contains symlinks; preserving it for inspection.")
    metadata = json.loads(path.read_text())
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", metadata.get("user", "")):
        raise SetupError("Invalid saved SSH username.")
    if metadata.get("host_alias") != f"dotfiles-termux-{state.name}":
        raise SetupError("Invalid dedicated SSH host alias.")
    if not isinstance(metadata.get("ssh_port"), int) or not 1024 <= metadata["ssh_port"] <= 65535:
        raise SetupError("Invalid saved SSH port.")
    normalized_key(metadata.get("host_key", ""))
    return metadata


def resume_pairing(adb, state):
    metadata = load_pairing(state)
    if metadata is None:
        return None
    with mapping(adb, "forward", metadata["ssh_port"]) as port:
        command = ssh_arguments(state, metadata, port)
        connection = run([*command, "true"], check=False, timeout=15)
        check_ssh_identity(connection)
        if connection.returncode:
            return None
        marker = "DOTFILES_TERMUX_STATE_" + secrets.token_hex(8)
        result = run([*command, shlex.join(["bash", "-c", target_state_script(marker)])], check=False, timeout=20)
        if result.returncode == 0:
            metadata = save_pairing(state, adb.serial, parse_target_state(result.stdout, marker))
        # A paired device interrupted before cloning has working SSH but no
        # canonical source yet. It can still resume without UI re-pairing.
    print("Saved USB SSH pairing verified; resuming without terminal input.", flush=True)
    return metadata


def check_ssh_identity(result):
    detail = ((result.stderr or "") + "\n" + (result.stdout or "")).lower()
    if "remote host identification has changed" in detail or "host key verification failed" in detail:
        raise SetupError("SSH host-key verification failed. Existing device trust is preserved; investigate "
                         "the changed identity before provisioning. No UI re-pairing was attempted.")


def run_streaming(argv, *, input, timeout):
    """Show target progress while retaining a bounded tail for its final report."""
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    events = queue.Queue()

    def read_output():
        try:
            for line in process.stdout:
                events.put(line)
        finally:
            events.put(None)

    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()
    tail = ""
    try:
        process.stdin.write(input)
        process.stdin.close()
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() >= deadline:
                raise SetupError("Target setup timed out; its saved pairing can be reused.")
            try:
                line = events.get(timeout=0.25)
            except queue.Empty:
                continue
            if line is None:
                break
            print(line, end="", flush=True)
            tail = (tail + line)[-65536:]
        status = process.wait(timeout=5)
        return subprocess.CompletedProcess(argv, status, tail, "")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        process.stdout.close()
        if not process.stdin.closed:
            process.stdin.close()
        thread.join(timeout=2)


def setup_options(args):
    options = ["--non-interactive"]
    for attribute, flag in (("ssh_mode", "--ssh-mode"), ("ssh_port", "--ssh-port"),
                            ("install_termux_boot", "--install-termux-boot"),
                            ("termux_wake_lock", "--termux-wake-lock"),
                            ("install_ssh_server", "--install-ssh-server"),
                            ("install_coding_agents", "--install-coding-agents")):
        value = getattr(args, attribute)
        if value is not None:
            options += [flag, str(value)]
    if args.with_tools is not None:
        options += ["--with", args.with_tools]
    return options


def full_setup(adb, state, metadata, args):
    options = setup_options(args)
    marker = "DOTFILES_TERMUX_STATE_" + secrets.token_hex(8)
    script = ('dft_setup=$(mktemp) || exit; cat > "$dft_setup" || exit; '
              f'bash "$dft_setup" {shlex.join(options)}; dft_status=$?; '
              'rm -f "$dft_setup"; dft_report_status=1; '
              'if [ -f "$HOME/.local/share/dotfiles-Termux/scripts/pair.sh" ]; then ( '
              + target_state_script(marker) + ' ); dft_report_status=$?; fi; '
              '[ "$dft_status" = 0 ] || exit "$dft_status"; exit "$dft_report_status"')
    with mapping(adb, "forward", metadata["ssh_port"]) as port:
        command = ssh_arguments(state, metadata, port)
        for attempt in range(12):
            connection = run([*command, "true"], check=False, timeout=15)
            check_ssh_identity(connection)
            if connection.returncode == 0:
                break
            if attempt == 11:
                raise SetupError("SSH did not become ready; pairing is saved and setup can be rerun.")
            time.sleep(1)
        print("USB SSH verified; applying the native Termux environment…", flush=True)
        result = run_streaming([*command, shlex.join(["bash", "-c", script])],
                               input=(ROOT / "bootstrap.sh").read_text(), timeout=args.timeout)
        try:
            receipt = parse_target_state(result.stdout, marker)
        except SetupError as exc:
            if result.returncode:
                raise SetupError(f"Target setup exited with status {result.returncode}; final SSH configuration "
                                 "could not be read. Existing host state was preserved; inspect the target error.") from exc
            raise
        metadata = save_pairing(state, adb.serial, receipt)
        if result.returncode:
            raise SetupError(f"Target setup exited with status {result.returncode}; final SSH configuration was "
                             "saved. Resolve the reported target error and rerun setup to resume.")
        return metadata


def setup(adb, args):
    if adb.shell("getprop", "sys.boot_completed").stdout.strip() != "1":
        raise SetupError("Android is still booting; unlock the device and retry.")
    sdk = adb.shell("getprop", "ro.build.version.sdk").stdout.strip()
    if not sdk.isdigit() or int(sdk) < 24:
        raise SetupError("This setup requires Android 7 or later and a supported native Termux installation.")
    rows = read_lock(ROOT / "config/apks.lock.json")
    state = state_for(args.state_dir, adb.serial)
    with device_lock(state):
        metadata = resume_pairing(adb, state)
        install_boot = (args.install_termux_boot == "true" if args.install_termux_boot is not None
                        else (metadata or {}).get("install_termux_boot", True))
        names = ["fdroid", "termux"] + (["boot"] if install_boot else []) + (["api"] if args.api else [])
        for name in names:
            install_apk(adb, rows[name], args.state_dir / "cache/apks")
        if install_boot:
            print("Opening Termux:Boot once to enable its boot receiver…", flush=True)
            launch_activity(adb, resolve_activity(adb, rows["boot"]))
        if metadata is not None:
            # Updating the Termux APK can stop its services. Recheck before
            # deciding that no new foreground/manual pairing is necessary.
            metadata = resume_pairing(adb, state)
        if metadata is None:
            key = ensure_identity(state)
            with PairingServer() as server, mapping(adb, "reverse", server.port) as port:
                base = f"http://127.0.0.1:{port}/{server.nonce}"
                server.payload = capsule((ROOT / "scripts/pair.sh").read_text(), key,
                                         f"{base}/result", args.ssh_mode, args.ssh_port)
                command = bootstrap_command(f"{base}/payload", hashlib.sha256(server.payload).hexdigest())
                automatic = not args.manual and try_ui_bootstrap(adb, resolve_activity(adb, rows["termux"]), command)
                if not automatic:
                    print("Open a NEW Bash shell in Termux and paste this single line. Keep this helper running:\n", flush=True)
                    print(command + "\n", flush=True)
                print("Waiting for pairing; package synchronization can take several minutes…", flush=True)
                deadline = time.monotonic() + args.timeout
                while not server.done.wait(5):
                    if time.monotonic() >= deadline:
                        raise SetupError("Pairing timed out. Inspect the Termux terminal and rerun setup; app data is preserved.")
                    if adb.call("get-state", check=False, timeout=10).stdout.strip() != "device":
                        raise SetupError("Device disconnected. Reconnect and rerun setup; app data is preserved.")
                metadata = save_pairing(state, adb.serial, server.receipt)
        metadata = full_setup(adb, state, metadata, args)
    if metadata["install_ssh_server"]:
        print(f"Setup complete. SSH mode: {metadata['ssh_mode']}, port: {metadata['ssh_port']}. LAN reachability is not inferred from USB.")
        print(f"Connect over USB: uv run --script scripts/host.py ssh --serial {shlex.quote(adb.serial)}")
    else:
        print("Setup complete. SSH is disabled by the device configuration; local Termux remains available.")


def ssh(adb, args):
    state = state_for(args.state_dir, adb.serial)
    with device_lock(state):
        metadata = load_pairing(state)
        if metadata is None:
            raise SetupError("This device is not paired; run setup first.")
        with mapping(adb, "forward", metadata["ssh_port"]) as port:
            command = ssh_arguments(state, metadata, port)
            trailing = args.command[1:] if args.command[:1] == ["--"] else args.command
            if trailing:
                command += [shlex.join(trailing)]
            else:
                command.insert(1, "-t")
            return run(command, capture=False, timeout=None, check=False).returncode


def doctor(adb, args):
    print(f"Host: {sys.platform}; Python {sys.version.split()[0]}")
    for program in ("uv", "adb", "ssh", "ssh-keygen", "openssl"):
        print(f"{program}: {shutil.which(program) or 'missing'}")
    if adb is None:
        print("Target diagnostics require an attached, authorized device.")
        return
    for prop in ("ro.product.model", "ro.build.version.release", "ro.product.cpu.abi", "sys.boot_completed"):
        print(f"{prop}: {adb.shell('getprop', prop).stdout.strip()}")
    for package in ("org.fdroid.fdroid", "com.termux", "com.termux.boot", "com.termux.api"):
        found = adb.shell("pm", "path", package, check=False).stdout.strip()
        print(f"{package}: {'installed' if found.startswith('package:') else 'missing'}")
    state = state_for(args.state_dir, adb.serial)
    print(f"Pairing: {'saved' if (state / 'device.json').exists() else 'not paired'}")
    metadata = load_pairing(state)
    if metadata is not None:
        with device_lock(state), mapping(adb, "forward", metadata["ssh_port"]) as port:
            script = 'bash "$HOME/.local/share/dotfiles-Termux/bootstrap.sh" doctor'
            print("Native Termux diagnostics over saved SSH:", flush=True)
            result = run([*ssh_arguments(state, metadata, port), shlex.join(["bash", "-c", script])],
                         capture=False, check=False, timeout=90)
            if result.returncode:
                print("Target doctor could not complete; check its SSH listener and saved port.")
    print("USB diagnostics do not verify LAN access, Boot after reboot, or Android runtime compatibility.")


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--serial")
    cli.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    subcommands = cli.add_subparsers(dest="subcommand", required=True)
    for name in ("devices", "doctor", "setup", "ssh"):
        sub = subcommands.add_parser(name)
        sub.add_argument("--serial", default=argparse.SUPPRESS)
        sub.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
        if name == "setup":
            sub.add_argument("--manual", action="store_true", help="print the pairing command instead of UI typing")
            sub.add_argument("--api", action="store_true", help="also install Termux:API")
            sub.add_argument("--ssh-mode", choices=("lan", "adb"))
            sub.add_argument("--ssh-port", type=int)
            sub.add_argument("--install-termux-boot", choices=("true", "false"))
            sub.add_argument("--no-boot", dest="install_termux_boot", action="store_const", const="false")
            sub.add_argument("--termux-wake-lock", choices=("true", "false"))
            sub.add_argument("--wake-lock", dest="termux_wake_lock", action="store_const", const="true")
            sub.add_argument("--install-ssh-server", choices=("true", "false"))
            sub.add_argument("--install-coding-agents", choices=("true", "false"))
            sub.add_argument("--with", dest="with_tools", help="optional native experiments: herdr,codex")
            sub.add_argument("--timeout", type=int, default=900)
        if name == "ssh":
            sub.add_argument("command", nargs=argparse.REMAINDER)
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if sys.platform not in ("darwin", "linux"):
            raise SetupError("Host automation currently supports macOS and Linux.")
        if args.subcommand == "setup":
            if (args.ssh_port is not None and not 1024 <= args.ssh_port <= 65535) or args.timeout <= 0:
                raise SetupError("Choose an SSH port from 1024–65535 and a positive timeout.")
            if args.with_tools not in (None, "") and any(value not in ("herdr", "codex") for value in args.with_tools.split(",")):
                raise SetupError("--with accepts herdr,codex only.")
        if args.subcommand == "doctor":
            try:
                adb = Adb(select_device(list_devices(), args.serial))
            except SetupError as exc:
                doctor(None, args)
                print(f"Device: {exc}")
                return 1
            doctor(adb, args)
            return 0
        devices = list_devices()
        if args.subcommand == "devices":
            print(json.dumps(devices, indent=2))
            return 0
        adb = Adb(select_device(devices, args.serial))
        if args.subcommand == "setup":
            setup(adb, args)
        else:
            return ssh(adb, args)
        return 0
    except (SetupError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped; owned USB mappings removed. Rerun setup to continue.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
