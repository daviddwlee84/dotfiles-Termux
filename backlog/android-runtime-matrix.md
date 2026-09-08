# Validate Android runtime matrix

**Status**: P1
**Effort**: M
**Related**: [TODO](../TODO.md) · [acceptance checklist](../docs/verification.md#device-acceptance)

## Context

2026-09-09: the first implementation is developed on a macOS maintainer host.
Desktop fixture tests must not be promoted into Android runtime claims.
ARM64 is the first target; wider OEM coverage follows real evidence.

## Investigation

Primary-source and ELF inspection established native package and experimental
static-binary paths. It did not execute Herdr, Codex or an agent session on
Android. The checklist already exists in docs; record results here rather
than duplicating the procedure.

## Next run

Record date, Android/API, architecture, Termux version/signing channel,
package/tool versions, and pass/fail/unverified for setup/reapply, reconnect,
LAN/ADB mode, Boot, screen-off behavior, Pi and selected Herdr/Codex checks.
Preserve exact failures after removing secrets/device identifiers. Private
runtime artifacts stay outside Git.

## Decision

Native ARM64 first. Android runtime and authentication remain unverified
until a real run supplies evidence. Later devices extend the matrix rather
than overwriting the first device's limitations.
