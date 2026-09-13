# Setup and maintenance

Use native Termux from F-Droid on Android 7 or newer; ARM64 is the first
runtime target for this repository. The computer helper supports macOS and
Linux. Windows users can follow the device-only instructions below.

## Quick setup with the selected tools

On the computer, from this clone, select Herdr 0.9.0, dev-cli 0.2.33,
Pi 0.85.1 and Codex 0.153.4 in one command:

```sh
uv run --script scripts/host.py setup --with herdr,codex,dev --install-coding-agents true
```

For a fresh native Termux shell, use the device-only
[one-line bootstrap in the README](https://github.com/daviddwlee84/dotfiles-Termux#one-line-setup-herdr--dev-cli--coding-agents).
For an existing device checkout, run inside Termux:

```sh
cd "$HOME/.local/share/dotfiles-Termux" && bash bootstrap.sh update && bash bootstrap.sh packages --with herdr,codex,dev --install-coding-agents true
```

Use `--with herdr,dev` to select Herdr/dev-cli without Codex; Pi remains
enabled. `--with` replaces the saved optional list, and existing binaries
are preserved. Installation is separate from [runtime support](tools.md),
especially the observed Codex sandbox failure.

After setup, use `chezmoi diff/apply/update` from any directory for managed
configuration. Use `packages` for newly selected tools and full package
synchronization. dev config is user-owned; the Herdr config is a create-once
seed. Open a new Bash shell to load dev navigation and completion.

## Which command runs where?

All provisioning and SSH helper code is in the public
[dotfiles-Termux repository](https://github.com/daviddwlee84/dotfiles-Termux):
its `justfile`, `scripts/host.py` and `scripts/host-deps.sh`. You can clone it
standalone; access to the umbrella repository is not required. The
`dotfiles-all` recipes only pass arguments to these public helpers.

The following are **computer-side commands**, run on macOS/Linux:

| Task | From `dotfiles-all/` | From the public `dotfiles-Termux/` clone | Without just, from that public clone |
| --- | --- | --- | --- |
| Host dependencies | `just termux-host-deps` | `just host-deps` | `sh scripts/host-deps.sh` |
| List devices | `just termux-devices` | `just devices` | `uv run --script scripts/host.py devices` |
| Provision Android | `just termux-setup` | `just setup` | `uv run --script scripts/host.py setup` |
| Connect to Android | `just termux-ssh` | `just ssh` | `uv run --script scripts/host.py ssh` |
| Host/device health | `just termux-doctor` | `just doctor` | `uv run --script scripts/host.py doctor` |
| Maintainer checks | `just check-termux` | `just check` | See [verification](verification.md) |

The umbrella-prefixed recipe names are not defined in the standalone
justfile. Inside **Termux on Android**, use `bash bootstrap.sh setup` for
initial target setup and `just target-doctor` or `bash bootstrap.sh doctor`
for target health, from the device's repository working tree. Standalone
`just setup`, `just ssh` and `just doctor` remain computer-side recipes even
when you are looking at the same repository on Android.

The installed `termux-ssh` command **without just** is a different target-side
helper: `termux-ssh status|start|stop` manages the tablet's own sshd. Private
pairing keys/state stay on the computer; the helper implementation itself
is public.

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
uv run --script scripts/host.py setup --serial SERIAL --with herdr,dev
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

Use the command-location table above when switching between the umbrella
and standalone clone. The umbrella's ordinary `just apply` still targets
the computer's native Unix/Windows configuration.

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

## HOME, PREFIX and the chezmoi source

In this supported native Termux app layout, `~` means `$HOME`:

| Layer | Location | Purpose |
| --- | --- | --- |
| Device HOME | `/data/data/com.termux/files/home` | Your files and the dotfile destination |
| Package PREFIX | `/data/data/com.termux/files/usr` | Native package programs in `$PREFIX/bin`, package configuration in `$PREFIX/etc` |
| Repository working tree | `$HOME/.local/share/dotfiles-Termux` | Git checkout, bootstrap, scripts, justfile and docs |
| Effective chezmoi source | `$HOME/.local/share/dotfiles-Termux/home` | Templates selected by the repository's `.chezmoiroot` file |
| Default chezmoi configuration | `$HOME/.config/chezmoi/chezmoi.toml` | Saved source location and feature choices |

The repository's `home/` directory contains **source templates**; it is not
Android's `$HOME`. The `.chezmoiroot` file contains the single word `home`.
Consequently, `chezmoi source-path` and `.chezmoi.sourceDir` resolve to the
checkout's `home/`, while `.chezmoi.workingTree` is the checkout root.

Using `.local/share/dotfiles-Termux` rather than chezmoi's usual
`.local/share/chezmoi` is this bootstrap's convention, not a Termux or chezmoi
requirement. It gives the bootstrap and SSH-resume helper a known repository
location and keeps scripts alongside the templates. No second clone in the
usual chezmoi location is required. Existing unrelated chezmoi state is
preserved rather than silently moved or overwritten.

During setup, `scripts/manage.sh` runs `chezmoi init` with explicit source
(the working tree) and destination (`$HOME`). `home/.chezmoi.toml.tmpl` saves
`sourceDir` as the absolute **working-tree root** in the config; chezmoi then
uses `.chezmoiroot` to select the effective `home/` source. This also records
feature data and the fast-forward-only update helper. Once initialized,
ordinary chezmoi commands find the saved source from any current directory.
You can inspect the paths in Termux with:

```sh
printf 'HOME=%s\nPREFIX=%s\n' "$HOME" "$PREFIX"
chezmoi source-path
chezmoi execute-template '{{ .chezmoi.workingTree }}'
```

`bootstrap.sh` is the device's initial entry point. From an existing clone it
delegates to `scripts/manage.sh`; when delivered as a standalone bootstrap
file, it obtains the canonical clone first. Computer `setup` delivers this
entry point over the paired SSH connection. The manual instructions above
clone the same public repo and invoke it locally. This initial step installs
packages and initializes chezmoi; daily `chezmoi diff`, `chezmoi apply` and
`chezmoi update` handle configuration only.

## Configuration and package updates

The native package policy deliberately separates frequent dotfile updates
from full package synchronization:

| Operation in the Termux clone | Behavior |
| --- | --- |
| `chezmoi diff` | Preview actual managed-file differences; works from any directory after init |
| `just diff` | Preview bootstrap settings/dry-run choices; this recipe does not show the file diff |
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
Herdr/Codex/dev-cli selection; providing it replaces that selection without uninstalling
tools. Pi is controlled by `--install-coding-agents true|false` and defaults
to true. Boolean host and target options also include `--install-ssh-server`,
`--install-termux-boot`, and `--termux-wake-lock`.

Use `--non-interactive` when all desired values are supplied/defaulted.
Existing unrelated chezmoi sources are preserved; resolve a source conflict
explicitly instead of deleting another configuration.


The rendered `~/.config/dotfiles-termux/settings` comes from chezmoi init
data and should not be edited directly. For configuration-only changes to
saved values, use `chezmoi edit-config`, edit the relevant `[data]` values,
and run `chezmoi apply`.

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
| `optionalTools` | `""` | Optional tools (herdr,codex,dev or empty) |

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

## Missing command: which or file

`which` is a [separate Termux package](https://github.com/termux/termux-packages/blob/master/packages/which/build.sh); having `util-linux` installed does not
supply it. The baseline now explicitly requests both `which` and `file`.
For a command-path check without `which`, Bash already provides
`command -v git` and `type -a git`.

After updating an older checkout with `chezmoi update`, run `just packages`
from `$HOME/.local/share/dotfiles-Termux` to synchronize the full native
package set and add missing baseline commands. An ordinary chezmoi apply
intentionally does not install newly added packages.

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
