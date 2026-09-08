# Expand native agent compatibility

**Status**: P?
**Effort**: L
**Related**: [TODO](../TODO.md) · [tool guide](../docs/tools.md) · [PRoot](../docs/proot.md)

## Context

2026-09-09: native Termux is the chosen baseline. The user wants local
Herdr + sshd and ideally Claude/Codex, with a separate environment as fallback.
Pi has a maintained upstream Termux guide and ships first.

## Evidence to preserve

- Herdr v0.9.0 aarch64: 22,697,240 bytes; SHA-256
  `9c8db20fb7e7427b138d5367113f1621ffd319f2f65d6f009e2594029115f0d2`.
  ELF64 AArch64 ET_EXEC, no PT_INTERP/PT_DYNAMIC.
- Codex v0.153.4 aarch64-musl archive: 90,899,740 bytes; SHA-256
  `5cda6182bd94c3a30f2eb63a495489ebf7f691fddb14d70f48c6c1a5071b6cde`.
  Extracted binary 222,567,456 bytes; ELF64 AArch64 ET_EXEC, no PT_INTERP
  or DT_NEEDED. Inspection matched the existing OpenWrt lock.
- Claude 2.1.263 ARM64-musl ELF requests `/lib/ld-musl-aarch64.so.1`.
  Only a streamed header was inspected, not the full artifact hash. It is
  not a self-contained static executable.
- Herdr honors configured shell / `$SHELL` for main panes, but Linux custom
  commands contain `/bin/sh`; detection uses `/proc`. No Android build
  target does not rule out Linux static execution. Static programs do not
  load the Termux exec interception library.
- Codex's bubblewrap/seccomp gate depends on kernel support. PRoot cannot
  add missing namespaces or agent sandbox facilities.
- Termux now packages native Bun. OMP/OpenCode have separate native
  dependency gaps; Bun availability does not establish their acceptance.

These are read-only observations, not Android runtime results. The tool
guide contains primary links and support qualifications.

## Options and next work

1. Keep native Herdr/Codex explicit and collect actual isolated device failures.
2. Patch/upstream demonstrated path/PTY/process problems; avoid speculative
   platform spoofing or global preload changes.
3. Use the documented same-ABI PRoot guest for Linux userspace needs. Measure
   package installs, Git scans and terminal behavior separately.
4. Re-evaluate Claude native runtime, Gemini, OpenCode and OMP against current
   artifacts and device tests before adding installers.

## Decision

Native first, explicit fallback, no automatic PRoot conversion and no
weakening Android/agent protections. Revalidate versions before resuming;
the hashes preserve the initial investigation only.
