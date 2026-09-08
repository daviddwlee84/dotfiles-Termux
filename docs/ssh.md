# SSH and boot

SSH is enabled by default in **LAN mode**, on port **8022**, using public-key
authentication. A missing authorized key leaves SSH in `pending-key` state;
local tools can still be installed. Password login is not enabled by setup.

## USB access and pairing

After computer-assisted setup, use:

```sh
just ssh
just ssh --serial SERIAL
```

The host helper creates a temporary ADB forward and checks the device against
the SSH host key obtained during pairing. It removes only the mapping owned
by that invocation. A separate per-device identity avoids changing your
normal SSH configuration or authorized keys on other machines.

Host pairing data lives under `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-termux`,
in a directory derived from the selected device. It includes the generated
private key, known-hosts file and connection metadata; directories/files use
private permissions. Keep this directory private and out of Git. Deleting
the host's private key loses that pairing identity; the public key already
authorized on the device is not automatically revoked.

If the SSH host key changes after an app reset, investigate it. Do not solve
the error by disabling host-key checking or deleting unrelated known-hosts
entries. The helper preserves established trust rather than silently accepting
a different device.

## LAN versus USB-only mode

| Mode | Listener | How to connect |
| --- | --- | --- |
| `lan` (default) | IPv4 `0.0.0.0:8022` | ADB-forwarded helper or the device's LAN address |
| `adb` | IPv4 `127.0.0.1:8022` | ADB-forwarded helper |

To choose USB-only access during computer setup:

```sh
just setup --ssh-mode adb
```

To change it on the target, from its repository clone:

```sh
bash bootstrap.sh apply --ssh-mode adb
# Restore LAN access when wanted:
bash bootstrap.sh apply --ssh-mode lan
```

Use `--ssh-port PORT` consistently if you change the port. A port already
owned by an unrelated SSH server is a conflict, not permission to stop it.

<a id="manual-lan-access"></a>
## Manual LAN access

For manual installation, create or choose an SSH key on your computer. For a
new dedicated key:

```sh
ssh-keygen -t ed25519 -f "$HOME/.ssh/termux-dev"
```

Copy only `termux-dev.pub` to `$HOME/host.pub` inside Termux. From the device's
clone, authorize it and inspect the resulting status:

```sh
bash bootstrap.sh setup --authorized-key-file "$HOME/host.pub"
bash bootstrap.sh doctor
whoami
```

After initial setup, `termux-ssh authorize "$HOME/host.pub"` can add a key
and start the managed service without package synchronization.
`termux-ssh status`, `termux-ssh start` and `termux-ssh stop` manage that
service independently of unrelated sshd instances.

Use the reported Termux username and the Android Wi-Fi address:

```sh
ssh -p 8022 -i "$HOME/.ssh/termux-dev" TERMUX_USER@DEVICE_LAN_IP
```

For the first manual connection, compare the host-key fingerprint shown by
SSH with the device's host public key before accepting it. Manual LAN setup
does not populate the computer helper's separately pinned pairing state.

On the device, show the fingerprint with:

```sh
ssh-keygen -lf "$PREFIX/etc/ssh/ssh_host_ed25519_key.pub"
```

## Managed files

The repository owns its SSH configuration at
`~/.config/dotfiles-termux/sshd_config` and process state beneath
`~/.local/state/dotfiles-termux/`. It appends a supplied valid public key
without removing unrelated `authorized_keys` entries. Existing SSH host keys
are preserved. The repo controls only its own daemon/PID and its own Boot
hook; it does not kill a foreign sshd or replace the global OpenSSH config.

Target choices persist in `~/.config/dotfiles-termux/settings`.
To stop managing the repo's SSH service, apply with
`--install-ssh-server false`. This is not an app uninstall or a request to
remove other SSH services.

## Termux:Boot and Android background behavior

Boot integration defaults to enabled. Install Termux:Boot from the same
signing source as Termux and **open it once**. The repository creates one
script at `~/.termux/boot/50-dotfiles-termux`; other scripts remain yours.
The Boot app runs scripts in sorted order after a device boot.
[Upstream Boot instructions](https://github.com/termux/termux-boot#usage).

Wake-lock defaults to off. Opt in using `--termux-wake-lock true` on the
target or `--wake-lock` during host setup. A wake-lock can increase battery
use; it does not guarantee survival of an Android force-stop or an OEM
background-process restriction.

Battery optimization exemptions and notification/storage permissions are
separate Android choices. If you need long sessions, review Termux's battery
settings on that device and test a screen-off reconnect. A terminal
multiplexer preserves sessions across an SSH disconnect only while its
process remains alive; a reboot or Android process kill is different.
[Termux process model](https://github.com/termux/termux-packages/wiki/Termux-execution-environment#daemon-c-function).
