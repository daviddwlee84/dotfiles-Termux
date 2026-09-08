# Tools and compatibility

The baseline stays in native Termux. Package availability and the compatibility
evidence below were reviewed on **2026-09-09**; this date is not an Android
device-test result.

| Tool | Installation path | Support level here |
| --- | --- | --- |
| chezmoi, Bash, Starship, Git, Vim, tmux, Python and build utilities | Official Termux packages | Native baseline; device acceptance still required |
| Node.js LTS and npm | Official Termux packages | Runtime for Pi |
| Pi | Maintained `@earendil-works/pi-coding-agent` npm package | Native default, controlled by `installCodingAgents` |
| Herdr | Pinned upstream Linux static binary | Explicit native experiment |
| Codex | Pinned upstream Linux-musl static binary | Explicit native experiment; sandbox is a separate gate |
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
to repeat the upstream installation command after normal setup. Start `pi` in a project and complete its provider
login yourself. No API token or provider login is copied from the computer.
To leave Pi out of a subsequent explicit setup, use
`--install-coding-agents false`; existing installations are not uninstalled.

Text clipboard integration requires both the Termux:API Android app and the
`termux-api` command package. Image clipboard paste is not supported by Pi on
Termux. The companion is optional; basic terminal work does not need Android
device permissions. [Pi Termux guide](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/termux.md).

The host `--api` option installs the Android companion APK. To add its native
commands, explicitly synchronize packages and install them in Termux:

```sh
pkg update && pkg upgrade -y && pkg install -y termux-api
```

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
interpreter. That makes direct execution on Android's Linux kernel plausible.
It does not establish official Android support. A missing Android build target
alone is also not proof that these Linux static binaries cannot run.

For Herdr, verify a shell pane, split/resize, pane CLI operations, and
disconnect/reattach through native Termux sshd. Keep `$SHELL` and `$TMPDIR`
pointing at the actual Termux paths. Some Linux helpers invoke literal
`/bin/sh`; process/CWD/agent detection also depends on `/proc` access.
Features can fail independently of the main terminal session.
[Herdr shell selection](https://github.com/herdrdev/herdr/blob/v0.9.0/src/pane.rs),
[Linux command helpers](https://github.com/herdrdev/herdr/blob/v0.9.0/src/platform/linux.rs).

For Codex, verify provider login, DNS/TLS, file operations, shell/PTY behavior,
and the ordinary sandbox. Current official Linux sandboxing uses bubblewrap
and seccomp and depends on host kernel support. If it cannot initialize,
report that gate as failed. Do not disable the sandbox to label the probe
successful. [Official Codex CLI documentation](https://learn.chatgpt.com/docs/codex/cli),
[official sandbox documentation](https://learn.chatgpt.com/docs/sandboxing).

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
