# Tools and compatibility

The baseline stays in native Termux. Package availability and the compatibility
evidence below were reviewed on **2026-09-09**. The first Android device now
has partial installation/launch results; see the [verification record](verification.md#current-verification-record-2026-09-09)
for the exact completed and pending checks.

| Tool | Installation path | Support level here |
| --- | --- | --- |
| chezmoi, Bash, Starship, Git, Vim, tmux, Python and build utilities | Official Termux packages | Native baseline; device acceptance still required |
| Node.js LTS and npm | Official Termux packages | Runtime for Pi |
| Pi | Maintained `@earendil-works/pi-coding-agent` npm package | Native default, controlled by `installCodingAgents` |
| Herdr | Pinned upstream Linux static binary | Explicit native experiment |
| dev-cli (`dev`) | Pinned v0.2.33 upstream Linux ARM64 static binary | Opt-in with `--with dev`; Android runtime unverified |
| Codex | Complete pinned official Linux-musl package and companions | Installed on the first device; normal sandbox blocked there |
| Claude Code | Official Linux installer inside an optional PRoot distro | Guide only; no native installer in this repo |
| Gemini CLI, OpenCode, OMP | Future compatibility work | No automatic installer |

Termux packages are built for Android. Use `pkg` instead of generic Linux
release assets when a native package exists. The official package recipes
include [chezmoi](https://github.com/termux/termux-packages/blob/master/packages/chezmoi/build.sh)
and [Starship](https://github.com/termux/termux-packages/blob/master/packages/starship/build.sh).
Neovim is also available as a separate Termux package if you prefer it.

## Pi

Pi is enabled by default. Its upstream Termux guide documents the maintained
package and installation without dependency lifecycle scripts:

```sh
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

The bootstrap pins and verifies Pi’s top-level npm tarball (version, size
and SHA-256). npm resolves its transitive dependencies through the normal
registry process; this is not a complete dependency lock. You do not need
to repeat the upstream installation command after normal setup. Start `pi`
in a project and complete its provider login yourself. No API token or provider login is copied from the computer.
To leave Pi out of a subsequent explicit setup, use
`--install-coding-agents false`; existing installations are not uninstalled.


On the first device, an isolated Pi 0.85.1 UI launched without credentials
and displayed `No models available` / `/login`. The timed smoke run ended
with 124 at its deadline; no graceful exit, provider login or model call
was verified. This is a UI launch result, not an authenticated agent session.

Text clipboard integration requires both the Termux:API Android app and the
`termux-api` command package. Image clipboard paste is not supported by Pi on
Termux. The companion is optional; basic terminal work does not need Android
device permissions. [Pi Termux guide](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/termux.md).

The host `--api` option installs the Android companion APK. To add its native
commands, explicitly synchronize packages and install them in Termux:

```sh
pkg update && pkg upgrade -y && pkg install -y termux-api
```

## dev-cli

Install our repository/task CLI together with Herdr 0.9.0:

```sh
# On the computer, from this standalone clone:
just setup --with herdr,dev
# From dotfiles-all, the equivalent is: just termux-setup --with herdr,dev

# Or inside the Termux clone:
bash bootstrap.sh packages --with herdr,dev
```

`--with` replaces the saved optional selection. Include `codex` as well if
you want to retain that selection: `--with herdr,codex,dev`. Omit `--with`
on later runs to retain all saved choices. These tools remain opt-in; a
plain fresh setup does not install them.

The installer verifies the dev-cli v0.2.33 archive's size and SHA-256,
extracts its `dev` member, checks native `--version`, then installs
`~/.local/bin/dev`. Existing commands are preserved, including other versions;
setup/packages/upgrade do not replace existing optional binaries.

On **2026-09-13**, the downloaded archive matched the upstream release
metadata. Its executable was an AArch64 ELF with no dynamic interpreter or
dynamic section. This is an asset inspection result; Android execution,
SQLite state, Git/worktree operations and Herdr integration still need a
device test. Sources: [release](https://github.com/daviddwlee84/dev-cli/releases/tag/v0.2.33),
[static build workflow](https://github.com/daviddwlee84/dev-cli/blob/v0.2.33/.github/workflows/release.yml).

Open a new Bash shell after setup. Interactive shells load `dev shell-init bash`
for parent-directory navigation and `dev completion bash` for tab completion.
Shell startup performs no installation. Keep Termux's `$TMPDIR` pointing at
`$PREFIX/tmp`, since navigation uses private temporary files. Verify:

```sh
herdr --version
dev --version
type dev
complete -p dev
dev config path
```

Use `dev config init --help` to set up repository scan roots for this device,
then inspect `dev doctor`. Account credentials and desktop dev configuration
are not part of this setup. Test repository navigation in a scratch project
before relying on task/worktree or Herdr operations on Android.

## Native Herdr and Codex experiments

Select either or both explicitly:

```sh
# On the computer:
just setup --with herdr,codex

# Or inside the Termux clone:
bash bootstrap.sh packages --with herdr,codex
```

New downloads use pinned upstream assets with size and SHA-256 checks.
An existing command is preserved rather than replaced or declared equivalent
to the pinned candidate.
An optional failure is reported separately from baseline setup. Keep tmux
available while validating Herdr. A version string means that an executable
started; it is not proof that sessions, authentication or agent tools work.

Read-only inspection found that the Herdr v0.9.0 ARM64 binary and Codex
v0.153.4 ARM64-musl binary are self-contained ELF executables with no dynamic
interpreter. Both verified assets subsequently launched with `--version` on
the first ARM64 Android device. Installation then hit a hard-link
`Permission denied` error in app-private storage. The installer now uses
no-clobber rename and checks for a skipped move. A complete setup rerun later
exited 0. Codex now installs the full official distribution with its code-mode
host, rg, bwrap, zsh and manifest; archive and member checks preserve matching
managed files and reject conflicting files/symlinks. Main-binary startup alone
is not a complete-package check or official Android support.

For Herdr, verify a shell pane, split/resize, pane CLI operations, and
disconnect/reattach through native Termux sshd. Keep `$SHELL` and `$TMPDIR`
pointing at the actual Termux paths. Some Linux helpers invoke literal
`/bin/sh`; process/CWD/agent detection also depends on `/proc` access.
Features can fail independently of the main terminal session.
[Herdr shell selection](https://github.com/herdrdev/herdr/blob/v0.9.0/src/pane.rs),
[Linux command helpers](https://github.com/herdrdev/herdr/blob/v0.9.0/src/platform/linux.rs).


The first-device headless workspace probe passed run/read/split. Its
interactive SSH TUI also accepted a command and preserved the marker after
Ctrl+b q detach/reattach within the **same SSH connection**. Physical/network
disconnect recovery and interactive resize remain separate unverified gates.

For Codex, verify provider login, DNS/TLS, file operations, shell/PTY behavior,
and the ordinary sandbox. Current official Linux sandboxing uses bubblewrap
and seccomp and depends on host kernel support. If it cannot initialize,
report that gate as failed. Do not disable the sandbox to label the probe
successful. [Official Codex CLI documentation](https://learn.chatgpt.com/docs/codex/cli),
[official sandbox documentation](https://learn.chatgpt.com/docs/sandboxing).


On the tested Android 15 device, the complete Codex 0.153.4 package launched,
but its normal sandbox stopped with this exact error:

```text
bwrap: Can't read /proc/sys/kernel/overflowuid: Permission denied
```

This is a confirmed sandbox-startup failure, not proof that user namespaces
are disabled. No bypass was used. Installing the bundled helper fixes package
completeness; it does not remove the observed device restriction. Codex is
not recorded as ready for normal sandboxed coding on this device.

Android execution policies differ by app build and device. Termux's
system-linker execution mode cannot load static binaries. Do not change
Android protections to make a candidate pass.
[Termux execution limitations](https://github.com/termux/termux-exec-package/blob/master/site/pages/en/projects/docs/technical/index.md).

## Claude and other agents

The inspected Claude Code 2.1.263 Linux ARM64-musl package names
`/lib/ld-musl-aarch64.so.1` as its loader; it is not a self-contained static
binary. A regular Termux filesystem does not supply that conventional Linux
layout. Current npm packaging also launches platform-native executables,
so an old pure-JavaScript workaround is not a reliable default.
Use the [optional Linux userspace guide](proot.md) and upstream
[Claude setup instructions](https://code.claude.com/docs/en/setup).

Gemini has Android-aware upstream fixes, but runtime dependencies still need
device validation. OpenCode and OMP currently publish native dependencies for
Linux/macOS/Windows; native Bun availability alone does not resolve those
dependencies. Their support is recorded as future work rather than hidden
fallback installers.
[Gemini installation](https://geminicli.com/docs/get-started/installation/),
[OpenCode package metadata](https://registry.npmjs.org/opencode-ai/latest),
[OMP native dependencies](https://registry.npmjs.org/@oh-my-pi/pi-natives/latest).
