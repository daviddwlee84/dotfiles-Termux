# Verification and maintenance

## What the checks prove

| Level | Evidence | Does not prove |
| --- | --- | --- |
| Desktop fixtures | Parsing, fake ADB, temporary HOME/PREFIX, rendering and repeatability | Android execution or real USB pairing |
| Asset inspection | Pinned version, size/hash, architecture and loader metadata | PTY, network, authentication or sandbox behavior |
| Device smoke | Recorded Android/Termux versions and actual command results | Every OEM or background policy |
| Agent session | Authentication and representative tool use with intended protections | Future releases or arbitrary workloads |

CI runs fixtures on macOS and Ubuntu. It never needs a connected phone,
real pairing credentials, a provider key or the maintainer's live chezmoi
source. A version string does not establish runtime support.

## Desktop checks

Maintainer checks require just, uv, ShellCheck and chezmoi on the computer.
From a maintainer checkout:

```sh
just check
```

Individual checks:

```sh
bash scripts/lint.sh
uv run --no-project --python 3.12 python -m unittest discover -s tests -v
uv run --no-project --with 'mkdocs<2' --with mkdocs-material --with mkdocs-static-i18n mkdocs build --strict
bash scripts/todo-kanban.sh --validate-only TODO.md
```

ShellCheck covers maintained scripts. Tests use temporary paths and explicit
fixture-only environment markers. Secret checks run before public commits
and in CI. Keep pairing keys, device identities, known-hosts data and runtime
state out of the repository.

## Explicit native probes

Run these only inside native Termux after selecting/installing the tools:

```sh
bash scripts/tools.sh probe herdr
bash scripts/tools.sh probe codex
```

Herdr's probe creates private temporary configuration, a separate headless
server and an explicit workspace, then checks a PTY, command input/output
and a split. It cleans up only
its own session. Interactive SSH rendering, resize and reconnect remain
manual acceptance checks.

Codex's probe uses an isolated `CODEX_HOME`, runs a harmless command under
the normal read-only sandbox and checks that a write is denied. It never
adds bypass flags. Failure to initialize the sandbox is a failed gate, not
permission to weaken it. Authentication, DNS/TLS and interactive behavior
remain separate checks.

## Device acceptance

Record date, Android version/API, architecture, Termux app version/source,
relevant tool versions, and native versus PRoot execution. Keep serials and
account details private.

1. Complete setup, reconnect, then repeat setup. Unrelated shell content,
   SSH keys and Boot scripts must remain intact.
2. In a local Termux tab and a new SSH login, verify Bash, Starship, Git,
   Vim and tmux using a scratch directory under `$HOME`.
3. Apply configuration twice. The second application must be stable and
   neither run may install or upgrade packages.
4. Exercise explicit full package synchronization and an interrupted retry.
   Failures remain visible and working binaries remain intact.
5. Check LAN and loopback-only SSH as applicable, wrong/untrusted keys,
   a busy foreign port, and reconnect after removing USB.
6. Open Termux:Boot once, reboot, and check the managed service. Test
   screen-off behavior separately and record battery settings.
7. Complete the selected [agent checks](tools.md), including normal sandbox
   behavior. An unavailable check is unverified, not passed.

## Updating pinned downloads

Review upstream metadata and the actual artifact together. Update version,
exact URL, SHA-256 and expected size as one change; verify architecture and
archive members. APK updates must retain the F-Droid signing channel.
Do not accept a changed hash merely because a download failed, and do not
commit downloaded APKs or binaries. Optional tool updates need new device
probes; `musl` in the filename does not prove static linkage.

## Project memory

`TODO.md` indexes future work, `backlog/` holds resume-friendly research, and
`pitfalls/` indexes investigated symptoms. They sit outside the chezmoi source
root `home/` and are never deployed.

The vendored maintenance scripts come from `project-knowledge-harness`:

```sh
bash scripts/add-todo.sh --priority P3 --effort S --title 'Example' --description 'A concrete future improvement'
bash scripts/todo-kanban.sh --validate-only TODO.md
```

Use `--backlog` for a research note; its template is
`backlog/.backlog-doc.md.template`. New user documentation needs English/zh-TW
pairs and both navigation entries in `mkdocs.yml`.

## Shell and uv follow-up — 2026-09-13

The ARM64 Android 15 tablet now selects native zsh 5.9.2 for new Termux/SSH
logins. The saved selection and actual Termux shell override agree. Existing
sessions were retained. Its older `chsh` needs a relative shell name; the
selector uses the form supported by both old and current Termux versions.

- Thirty interleaved warm samples per shell/location passed the performance
  gates. With the same managed helpers, zsh median was 186–190 ms versus Bash
  116–119 ms; zsh P95 was 204–208 ms and cold private caches took 692–694 ms.
  See [methodology and reproduction](shell.md#startup-measurements).
- A fresh SSH session loaded zsh, Starship, syntax highlighting and helpers.
  Typing `dev sta` then Tab displayed start/stats/status completion choices.
  The `dev` and `uv` completion functions were registered.
- A separate Herdr server using the device config created a zsh pane, ran the
  helpers and uv, confirmed dev completion, and split successfully. Its state
  was removed. Herdr had added an onboarding field to its seed; a backed-up,
  explicit one-field edit selected zsh while retaining onboarding.
- uv 0.12.13 (`aarch64-linux-android`) created a Python 3.14.6 venv, installed
  `packaging==25.0` from PyPI, and ran it through `uv run --no-project --with`.
  The native config uses system Python and copy mode; later user edits survive.
- Two consecutive chezmoi applies completed with no remaining managed-file
  differences. Bash remains the interpreter for management/Boot scripts.

The initial desktop suite passed 110 tests locally. CI then exposed an older
Bash EXIT-trap lifetime difference and a fake OMZ fixture that omitted the real
framework's `compinit -i`; both were corrected without disabling completion audits.
The [Checks workflow](https://github.com/daviddwlee84/dotfiles-Termux/actions/workflows/check.yml)
records the final revision's macOS/Ubuntu results. Reboot/background and fresh
ADB pairing remain separate gates; saved USB SSH pairing was reused here.

## Native dev upgrade to v0.2.35 — 2026-09-13

On the ARM64 Android 15 device with native Termux Go 1.27.1 and Clang:

- The self-update unit tests and an actual compact-source build passed before
  publication. The warm source build took 15.9 seconds and passed Git lookup.
- After [dev-cli v0.2.35](https://github.com/daviddwlee84/dev-cli/releases/tag/v0.2.35)
  was published, an isolated development binary ran the real `dev upgrade`.
  It selected the published 3,676,371-byte source archive, verified SHA-256,
  built with native Go/Clang and two workers, checked the candidate version,
  and replaced itself. Download, verification and compilation took approximately
  **11 seconds with existing dependency/build caches**.
- The verified v0.2.35 binary was installed at `~/.local/bin/dev` with a private
  recovery copy of the prior native v0.2.33 binary. Git repository navigation
  passed, the actual TUI rendered under a PTY and quit normally with `q`, and
  `dev upgrade --check` reported that v0.2.35 was already current.
- The device checkout was updated by fast-forward to the v0.2.35 installation
  pin. Temporary test repositories, binaries and state were removed afterward.

The pin update passed 111 desktop fixtures, focused installer checks, strict
bilingual documentation and secret checks. Its
[macOS/Ubuntu CI](https://github.com/daviddwlee84/dotfiles-Termux/actions/runs/34751565943)
passed. Full task/worktree lifecycle and authenticated agent use retain their
separate verification scope.

## Herdr and dev-cli follow-up — 2026-09-13

On the same ARM64 Android 15 device:

- Herdr 0.9.0 was already installed. Its isolated PTY/run/read/split probe passed
  again after the native package synchronization.
- Full package synchronization and optional selection `herdr,codex,dev` completed.
  Pi and the complete Codex package were preserved; no new Codex sandbox claim
  is made. Two consecutive chezmoi applies left no managed-file differences.
- The Linux dev-cli v0.2.33 artifact passed launch checks but crashed at
  `syscall.faccessat2` during Git lookup. It is superseded by the native source
  build; see [failure and migration](https://github.com/daviddwlee84/dotfiles-Termux/blob/main/pitfalls/dev-sigsys-faccessat2.md).
- The source installer built dev-cli v0.2.33 with Termux Go 1.27.1/Clang for
  Android. The result used `/system/bin/linker64`. It passed navigation into
  a scratch Git repository with spaces in its path, Markdown note creation,
  and SQLite FTS search under an isolated HOME. Probe state was removed.
- A fresh interactive SSH login loaded the dev shell wrapper and completion.
  The actual dev TUI opened, switched to REPOS, displayed the Termux checkout,
  and exited normally with `q`. A user-owned dev config was initialized for
  this device; the desktop configuration was not copied.

Full task/worktree lifecycle, dev-to-Herdr operations, network disruption,
reboot/background behavior and authenticated agent use remain separate gates.

## Current verification record — 2026-09-09

Published baseline evidence: [GitHub Actions run 34298511347](https://github.com/daviddwlee84/dotfiles-Termux/actions/runs/34298511347)
passed on `ad710fe` with 71 fixtures (39 host, 19 target, 13 optional-tool
checks), the macOS/Ubuntu matrix, strict bilingual docs and gitleaks.
Earlier local validation also passed the umbrella's 13 orchestration tests,
lint and harness validation. This is evidence for those revisions, not an
implicit result for later commits; see the [Checks workflow runs](https://github.com/daviddwlee84/dotfiles-Termux/actions/workflows/check.yml)
for subsequent revision status.

The follow-up local `just check` ran 87 fixtures in 455 seconds and ended with
five deadline errors: three Codex package checks exceeded 30 seconds and two
Herdr checks exceeded 10 seconds. Targeted package runs also timed out under
Python 3.12 and 3.14; the cause was not established. Deadlines and assertions
remain unchanged. On `38cbc3c`, the macOS CI job passed all 87 fixtures in
61 seconds, while Ubuntu stopped at a ShellCheck expression now rewritten as
an explicit condition. Local lint, cached strict docs and secret checks passed;
the local full suite is not recorded as passing.

All four locked APK downloads passed actual size/SHA-256 and signer-
certificate checks. The host dependency installer installed ADB 37.0.1.
Earlier startup probes timed out; ADB subsequently worked after device
authorization. The earlier timeout's cause was not established.

The tested device is a **Xiaomi Pad 6S Pro 12.4**, **ARM64**, running
**Android 15 / API 35 / HyperOS 2.0**. No serials, Android user IDs, addresses,
keys or private runtime state are recorded here.

| Check | Confirmed result |
| --- | --- |
| APK deployment | Matching-signer F-Droid/Termux installation or updates succeeded; Termux:Boot installed and opened |
| Initial command delivery | Automatic typing into a verified new Termux shell succeeded |
| USB SSH and resume | Pairing/strict host-key pinning succeeded; interrupted setup resumed over saved SSH without typing |
| LAN SSH | Direct port 8022 connection passed using the same pinned host identity |
| Full setup rerun | Exited 0 at `38cbc3c`; reused SSH, retained apps, full native package sync had no changes, preserved Pi/Herdr and verified the complete Codex package without downloading |
| Configuration | Two consecutive chezmoi applies left empty status with scripts excluded; `sshd -t` and managed SSH configuration equality passed |
| Normal SSH login | Bash and colored prompt rendered; `PROMPT_COMMAND=starship_precmd`, `ll='ls -al'`, `g='git'`; clean exit 0 |
| Health commands | Host and target doctor exited 0; the separate Codex sandbox result below still failed |
| tmux | Isolated native PTY input, two-pane split and resize passed |
| Herdr 0.9.0 | Explicit-workspace headless run/read/split passed; interactive SSH TUI accepted a typed command and Ctrl+b q detach/reattach preserved its marker within the same SSH connection |
| Pi 0.85.1 | Installed; isolated UI rendered without credentials and showed `No models available` / `/login`; test deadline ended the run with 124 |
| Codex 0.153.4 | Complete official package installed, including code-mode host, rg, bwrap, zsh and manifest; `--version` passed; normal sandbox failed as shown below |
| Boot | App installed/opened once; executable hook passed `bash -n`; no reboot/background result |
| Device network | Initial GitHub TLS EOF/timeouts cleared after the user enabled their own VPN; GitHub access and `git ls-remote` then succeeded |

The exact Codex failure was:

```text
bwrap: Can't read /proc/sys/kernel/overflowuid: Permission denied
```

This confirms a denied file read during normal sandbox startup. It does not
establish whether user namespaces are disabled. No sandbox bypass was used.

The earlier hard-link installation failure was addressed with no-clobber
rename and explicit skip detection. That installation result is separate
from runtime acceptance. Pi's 124 is the intentional test timeout, not an
application-crash or graceful-exit result; no provider login or model call
was performed.

P1 remains partial for physical/network-disruption recovery, Herdr interactive
resize, screen-off/background behavior, Boot after a real reboot, and agent
authentication/model/tool use. Herdr detach/reattach in one SSH connection
does not prove survival across a broken network connection. The VPN was a
user choice; the code made no global network change or offline-bundle feature.

Repository: [github.com/daviddwlee84/dotfiles-Termux](https://github.com/daviddwlee84/dotfiles-Termux).
