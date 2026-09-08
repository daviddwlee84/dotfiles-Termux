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

Herdr's probe creates private temporary configuration and a separate headless
server, then checks a PTY, command input/output and a split. It cleans up only
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

## Current verification record — 2026-09-09

On the macOS maintainer host, 65 fixture tests passed across the suites
(35 host, 19 target, 11 optional-tool tests); the umbrella's 13 orchestration
tests also passed. Lint, harness validation and the strict English/zh-TW
MkDocs build passed. These are desktop results, not Android runtime tests.

All four locked APK downloads passed their actual size/SHA-256 checks and
signer-certificate checks. `host-deps.sh --install` installed ADB 37.0.1.
The real `adb devices -l` probe then timed out during startup after 120 seconds;
`adb version` also stalled, and the probe's own processes were terminated.
The cause was not established. Device availability, Android execution, USB
SSH pairing and Boot behavior therefore remain unverified; this is not a
report that no devices were connected.

The public repository has been created at
[github.com/daviddwlee84/dotfiles-Termux](https://github.com/daviddwlee84/dotfiles-Termux).
GitHub Actions CI is pending; no remote CI success is claimed in this record.
