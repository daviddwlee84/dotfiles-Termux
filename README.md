# dotfiles-Termux

Native Android development tools and dotfiles for [Termux](https://termux.dev/),
with an optional ADB setup helper on macOS and Linux. This is a standalone,
experimental repository; ARM64 is the first runtime target.

[English guide](docs/setup.md) · [繁體中文指南](docs/setup.zh-TW.md) ·
[Tool compatibility](docs/tools.md) · [Verification](docs/verification.md)

The default setup provides Bash, chezmoi, Starship, Git, Vim, tmux,
development utilities, Node.js and Pi. Public-key SSH listens on port 8022;
Termux:Boot integration is enabled and wake-lock is off. Herdr and Codex are
explicit native experiments (`--with herdr,codex`). Claude Code has a separate
[PRoot guide](docs/proot.md).

On the first Android 15 device, native SSH, tmux and Herdr session checks
passed. The complete Codex package installed, but its normal sandbox failed
on a denied kernel-file read. Pi rendered its login UI; authenticated model
use and reboot/background behavior remain unverified. See the
[dated device results](docs/verification.md#current-verification-record-2026-09-09).

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
just diff                          # preview managed configuration
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
