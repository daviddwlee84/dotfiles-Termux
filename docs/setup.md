# Setup and maintenance

Use native Termux from F-Droid on Android 7 or newer; ARM64 is the first
runtime target for this repository. The computer helper supports macOS and
Linux. Windows users can follow the device-only instructions below.

## ADB setup from a computer

1. Clone `https://github.com/daviddwlee84/dotfiles-Termux.git` on the computer.
2. Run `sh scripts/host-deps.sh` to inspect dependencies. On supported macOS
   and Debian/Ubuntu hosts, `sh scripts/host-deps.sh --install` explicitly
   installs missing tools. Linux USB permission setup is separate:
   `sh scripts/host-deps.sh --usb-rules`.
3. On Android, enable Developer options and USB debugging, connect a data
   cable, unlock the screen, and approve this computer's ADB key.
4. Run the following from the clone:

```sh
export PATH="$HOME/.local/bin:$PATH"
uv run --script scripts/host.py devices
uv run --script scripts/host.py setup
uv run --script scripts/host.py ssh
uv run --script scripts/host.py doctor
```

The dependency helper does not require or install `just`. If already installed,
its shortcuts are `just devices`, `just setup`, `just ssh`, and `just doctor`.
The session-only `PATH` line covers uv under `~/.local/bin`; no shell profile
is changed.

If several devices are attached, pass `--serial SERIAL`. Setup accepts these
options; add them only when changing initial defaults or saved choices:

```sh
uv run --script scripts/host.py setup --serial SERIAL --manual
uv run --script scripts/host.py setup --serial SERIAL --api
uv run --script scripts/host.py setup --serial SERIAL --ssh-mode adb
uv run --script scripts/host.py setup --serial SERIAL --with herdr,codex
```

When pairing is needed, `--manual` prints the one-time command for you to
paste into a fresh Termux shell. `--api` adds the Termux:API companion. SSH defaults to LAN access on
port 8022; `--ssh-mode adb` binds it to loopback. `--no-boot` disables the
managed Boot integration; `--wake-lock` explicitly opts into keeping the CPU
awake. The default setup timeout is 900 seconds; increase `--timeout` on a
slow first package synchronization.

The helper verifies pinned APK sizes and SHA-256 hashes and installs the
selected F-Droid-channel apps. For initial pairing, it opens Termux and uses
a fresh shell for the small
pairing command and falls back to manual paste if that shell cannot be
established. It does not type commands into an arbitrary existing job.

Pairing transfers a dedicated **public** SSH key through a temporary USB
connection and records the device's SSH host key. The corresponding private
key stays on the computer. After pairing, the rest of setup runs over
USB-forwarded SSH; no LAN address is required. Keep the device unlocked for
Android dialogs. Resume an interrupted run by repeating the same command.
A rerun tries saved, working SSH first and only returns to fresh-shell/manual
pairing when needed. See [SSH and boot](ssh.md) for persisted state and ownership.

The serial is also accepted before the subcommand:

```sh
uv run --script scripts/host.py --serial SERIAL setup --manual
uv run --script scripts/host.py --serial SERIAL ssh -- uname -a
```

The umbrella `dotfiles-all` equivalents are `just termux-host-deps`,
`termux-devices`, `termux-setup`, `termux-ssh`, `termux-doctor`, and
`check-termux`. Its ordinary `just apply` still targets the computer's native
Unix/Windows configuration.

## APK source and signatures

The automated flow uses the F-Droid signing channel for Termux and its
companions. The F-Droid app is a convenience for future updates; it is not a
runtime requirement for an already-installed APK. In the F-Droid app, allow
the initial repository index refresh before searching for Termux.

Keep Termux, Termux:Boot and Termux:API from the **same source**. An existing
GitHub-signed app cannot be updated with an F-Droid-signed APK. Setup stops
on a signature conflict and preserves data. If you deliberately change
channels, export your Termux data first and follow the upstream migration
instructions; the helper never uninstalls an app to make a mismatch disappear.
The current Google Play branch is experimental and is outside this helper's
APK flow. [Termux installation guidance](https://github.com/termux/termux-app#installation).

## Manual setup on the device

1. Download F-Droid from [f-droid.org](https://f-droid.org/). Allow that
   browser/file manager to install the downloaded app when Android asks.
2. Refresh F-Droid's repositories, then install
   [Termux](https://f-droid.org/en/packages/com.termux/) and
   [Termux:Boot](https://f-droid.org/en/packages/com.termux.boot/).
   Install Termux:API only if you want clipboard/device integrations.
   Allow F-Droid to install apps when prompted.
3. Open Termux and wait for its bootstrap to finish. Open Termux:Boot once
   so Android permits its boot receiver to run.
4. In Termux, synchronize packages, obtain Git, clone this repository, and
   run setup:

```sh
pkg update && pkg upgrade -y && pkg install -y git
mkdir -p "$HOME/.local/share"
git clone https://github.com/daviddwlee84/dotfiles-Termux.git "$HOME/.local/share/dotfiles-Termux"
cd "$HOME/.local/share/dotfiles-Termux"
bash bootstrap.sh setup
```

Without an authorized public key, setup still installs the local environment
and reports SSH as `pending-key`. To enable SSH, put a trusted computer's
public-key line in `$HOME/host.pub` on the device, then run:

```sh
bash bootstrap.sh setup --authorized-key-file "$HOME/host.pub"
```

Only copy the `.pub` file. Never transfer a private key to Android or commit
pairing material. See [manual SSH access](ssh.md#manual-lan-access).

## Configuration and package updates

The native package policy deliberately separates frequent dotfile updates
from full package synchronization:

| Operation in the Termux clone | Behavior |
| --- | --- |
| `just diff` | Preview managed configuration |
| `just apply` / `bash bootstrap.sh apply` | Apply configuration without package upgrades |
| `bash bootstrap.sh update` | Fast-forward the Git source, then apply configuration |
| `just packages` | Fully synchronize Termux packages, then install selected tools |
| `just upgrade` | Fully synchronize native packages; existing optional binaries stay unchanged |
| `bash bootstrap.sh setup` | Initial setup or an explicit repeat of full setup |
| `bash bootstrap.sh doctor` | Inspect target status |

Ordinary `chezmoi apply` and `chezmoi update` do not install/upgrade packages.
`--config-only` selects configuration-only application. Termux does not
support partial upgrades: do not replace a full sync with isolated upgrades
of individual dependencies. Package operations require a working mirror;
if downloads fail, resolve the mirror/network problem and repeat the explicit
command. [Termux package management](https://github.com/termux/termux-packages/wiki/Package-Management).

Target selections persist between runs. Omitting `--with` retains the optional
Herdr/Codex selection; providing it replaces that selection without uninstalling
tools. Pi is controlled by `--install-coding-agents true|false` and defaults
to true. Boolean host and target options also include `--install-ssh-server`,
`--install-termux-boot`, and `--termux-wake-lock`.

Use `--non-interactive` when all desired values are supplied/defaulted.
Existing unrelated chezmoi sources are preserved; resolve a source conflict
explicitly instead of deleting another configuration.


Computer provisioning uses `~/.local/share/dotfiles-Termux` as the canonical
device clone; the manual instructions use the same path. The rendered
`~/.config/dotfiles-termux/settings` comes from chezmoi init data and should
not be edited directly. For configuration-only changes to saved values, use
`chezmoi edit-config`, edit the relevant `[data]` values, and run `chezmoi apply`.

To review native init prompts, run `chezmoi init --prompt` and then
`chezmoi apply`. Saved values:

| Data key | Default | Prompt |
| --- | --- | --- |
| `installSshServer` | `true` | Install SSH server |
| `sshMode` | `"lan"` | SSH access mode |
| `sshPort` | `"8022"` | SSH port |
| `installTermuxBoot` | `true` | Start SSH with Termux Boot |
| `termuxWakeLock` | `false` | Acquire wake lock at boot |
| `installCodingAgents` | `true` | Install coding agents (Pi) |
| `optionalTools` | `""` | Optional tools (herdr,codex or empty) |

A changed package selection takes effect at the next explicit
setup/packages/upgrade; configuration-only apply does not fetch that tool.
Computer `setup` uses the defaults only for a fresh configuration. Reruns
preserve device choices; only explicitly supplied options change them.

The host accepts `true|false` for `--install-ssh-server`,
`--install-coding-agents`, `--install-termux-boot`, and `--termux-wake-lock`.
`--no-boot` aliases `--install-termux-boot false`; `--wake-lock` aliases
`--termux-wake-lock true`. If SSH is explicitly disabled, setup records that
final state and local Termux remains usable.

Host `doctor` reports installed host capabilities even when it cannot select
a device, returning nonzero with next steps. For a paired reachable device,
it also runs the native target doctor over SSH. A failed device discovery
is not evidence that no device is connected.

## Device-side network failures

Host APK downloads and device-side package/GitHub access use different
network paths. In the first device run, GitHub TLS requests failed with EOF
or timeout while provisioning was already reachable over USB SSH. After the
user enabled their own VPN on the device, GitHub access and `git ls-remote`
succeeded and setup could resume.

This observation does not establish the cause of the original TLS failure.
The code did not change global VPN, proxy or DNS settings. Resolve device
connectivity and repeat setup; it can reuse the saved SSH pairing. An
offline bundle/install mode has not been implemented.
