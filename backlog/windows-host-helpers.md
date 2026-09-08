# Add native Windows host helpers

**Status**: P2
**Effort**: M
**Related**: [TODO](../TODO.md) · [setup guide](../docs/setup.md)

## Context

2026-09-09: initial host automation is macOS/Linux uv/Python with native
package-manager dependency helpers. Android-side setup is independent;
Windows users can follow the manual Termux guide.

## Work to resume

Implement Windows dependency handling and validate real ADB USB discovery,
APK paths, subprocess quoting, port lifecycle and OpenSSH key-file ACLs.
Preserve command/option meanings, F-Droid signatures, dedicated pairing
identity and SSH host-key trust. Retain manual fresh-shell fallback.

## Acceptance

Windows fixtures plus a real Windows-to-Android smoke run: paths containing
spaces, multiple/offline/unauthorized devices, interrupted resume, foreign
SSH ports and host-key mismatch. Python parsing alone is not native Windows
support.

## Decision

Defer the native Windows host layer. This repository owns its code and
research; do not duplicate the full backlog in dotfiles-windows.
