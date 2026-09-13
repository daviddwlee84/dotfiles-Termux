# dotfiles-Termux

Native Android development tools and dotfiles for [Termux](https://termux.dev/),
with an optional ADB setup helper on macOS and Linux. This is a standalone,
experimental repository; ARM64 is the first runtime target.

[English guide](docs/setup.md) · [繁體中文指南](docs/setup.zh-TW.md) ·
[Tool compatibility](docs/tools.md) · [Verification](docs/verification.md)

The default setup provides Bash, chezmoi, Starship, Git, Vim, tmux,
development utilities, Node.js and Pi. Public-key SSH listens on port 8022;
Termux:Boot integration is enabled and wake-lock is off. Herdr and Codex are
explicit native experiments (`--with herdr,codex`). Our dev-cli (`dev`) is also
opt-in: use `--with herdr,dev` for Herdr 0.9.0 and dev-cli 0.2.33. Claude Code has a separate
[PRoot guide](docs/proot.md).

On the first Android 15 device, native SSH, tmux and Herdr session checks
passed. The complete Codex package installed, but its normal sandbox failed
on a denied kernel-file read. Pi rendered its login UI; authenticated model
use and reboot/background behavior remain unverified. See the
[dated device results](docs/verification.md#current-verification-record-2026-09-09).

## One-line setup: Herdr + dev-cli + coding agents

On **macOS/Linux**, from an existing clone of this repository, connect and
authorize the Android USB device, then run:

```sh
uv run --script scripts/host.py setup --with herdr,codex,dev --install-coding-agents true
```

From the umbrella **dotfiles-all** clone, the equivalent is:

```sh
just termux-setup --with herdr,codex,dev --install-coding-agents true
```

For a **fresh native Termux shell**, without a computer, this single line
installs Git, clones the repository and runs setup:

```sh
pkg update -y && pkg upgrade -y && pkg install -y git && mkdir -p "$HOME/.local/share" && git clone https://github.com/daviddwlee84/dotfiles-Termux.git "$HOME/.local/share/dotfiles-Termux" && bash "$HOME/.local/share/dotfiles-Termux/bootstrap.sh" setup --with herdr,codex,dev --install-coding-agents true
```

This selects **Herdr 0.9.0**, **dev-cli 0.2.33** (`dev`), **Pi 0.85.1** and
**Codex 0.153.4**, alongside the native baseline. Codex's normal sandbox is
blocked on the tested device; installing it does not make that gate pass.
For Herdr + dev-cli + Pi only, use `--with herdr,dev` instead. Claude Code
requires the separate [PRoot guide](docs/proot.md). See [tool support](docs/tools.md).

If the Termux clone already exists, use this line **inside Termux** to update
its source/configuration and install the selected tools:

```sh
cd "$HOME/.local/share/dotfiles-Termux" && bash bootstrap.sh update && bash bootstrap.sh packages --with herdr,codex,dev --install-coding-agents true
```

`--with` replaces the saved optional list; omitting it preserves that list.
Existing binaries are retained, so these commands install missing tools but
do not force their versions. Open a new Bash shell for dev navigation and
tab completion. Device-only setup leaves SSH `pending-key` until you add a
trusted public key; computer setup pairs one automatically.

**Yes, chezmoi manages this afterward.** `chezmoi diff`, `chezmoi apply` and
`chezmoi update` work from any directory after setup. They manage configuration;
`just packages` / `just upgrade` inside the Termux clone explicitly synchronize
packages. New tool selections require `packages` or setup. dev's own config
and the create-once Herdr config remain locally editable. See
[saved settings and maintenance](docs/setup.md#configuration-and-package-updates).

## Set up a connected device

On the computer, clone this repository and check/install the host dependencies:

```sh
git clone https://github.com/daviddwlee84/dotfiles-Termux.git
cd dotfiles-Termux
sh scripts/host-deps.sh
# Explicitly install missing dependencies on a supported host:
sh scripts/host-deps.sh --install
export PATH="$HOME/.local/bin:$PATH"
uv run --script scripts/host.py devices
uv run --script scripts/host.py setup
uv run --script scripts/host.py ssh
uv run --script scripts/host.py doctor
```

`just` is optional on the computer: if installed, `just devices`, `just setup`,
`just ssh` and `just doctor` are shortcuts. The dependency helper does not
edit shell profiles; the `PATH` line covers a newly installed uv.

Enable USB debugging and approve this computer on the unlocked Android device.
On first setup, the helper installs verified F-Droid-channel APKs, opens a
new Termux shell, pairs a dedicated SSH key, and finishes over USB-forwarded
SSH. Reruns preserve saved choices and reuse working paired SSH before
requesting a new shell. Android
confirmation dialogs and first launches can still need a tap. If a new idle
shell cannot be established, use `uv run --script scripts/host.py setup --manual` and paste the displayed
command yourself. Existing app data and keys are preserved.

With several devices, select one explicitly, for example
`uv run --script scripts/host.py setup --serial SERIAL`. From the umbrella `dotfiles-all` repository, the
matching commands are `just termux-host-deps`, `termux-devices`, `termux-setup`,
`termux-ssh`, `termux-doctor`, and `check-termux`.

## Manage the device

Run these inside the cloned repository in Termux:

```sh
bash bootstrap.sh setup             # first setup, including full package sync
chezmoi diff                       # preview actual managed-file differences
just apply                         # configuration only
bash bootstrap.sh update            # ff-only source update + configuration
just packages                      # explicit full package sync + selected tools
just upgrade                       # explicit full package synchronization
```

`home/` is the chezmoi source root. Ordinary `chezmoi apply` and `chezmoi update`
are configuration operations; package upgrades happen only through explicit
setup/packages/upgrade commands. Termux does not support partial upgrades.
Do not apply the desktop Unix dotfiles repository to Termux.

For a device without ADB, follow the [manual setup guide](docs/setup.md#manual-setup-on-the-device).
The [SSH guide](docs/ssh.md) covers LAN access, USB-only mode, keys, Boot and
Android background-process limits.

## Development

```sh
just check
```

Checks use temporary directories and fixture devices on macOS/Linux. They do
not install Android apps or prove Android runtime compatibility. See the
[verification guide](docs/verification.md) before claiming device support.

<!-- project-knowledge-harness:readme-roadmap -->
<!-- Snippet for project's README.md, placed near other meta sections like
     "Customization" or "Contributing". -->

## Roadmap & lessons learned

Forward-looking work — long-term ideas, deferred items, things needing
evaluation — lives in [`TODO.md`](TODO.md), prioritised P1 → P3 with effort
estimates (S/M/L/XL). Items with accompanying research, design notes, or paused
troubleshooting link to a corresponding [`backlog/<slug>.md`](backlog/) doc.

Backward-looking knowledge — past traps and non-obvious debugging — lives in
[`pitfalls/`](pitfalls/), titled by symptom so future-you can grep the error
message and land on the root cause + workaround instead of re-debugging from
scratch.
<!-- project-knowledge-harness:readme-roadmap (end) -->
