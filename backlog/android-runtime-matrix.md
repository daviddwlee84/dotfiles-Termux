# Validate Android runtime matrix

**Status**: P1 — partial device validation
**Effort**: M
**Related**: [TODO](../TODO.md) · [current verification](../docs/verification.md#current-verification-record-2026-09-09)

## Device and confirmed progress

Xiaomi Pad 6S Pro 12.4, ARM64, Android 15 / API 35 / HyperOS 2.0; tested
2026-09-09. No serials, user IDs, addresses, keys or private runtime state.

- Matching-signer app installation/update, Boot installation/first opening,
  verified-new-shell input, strict USB SSH pairing and saved-SSH resume passed.
- Direct LAN SSH on 8022 used the same pinned host identity successfully.
- Full setup rerun at `38cbc3c` exited 0 without terminal input: apps retained,
  full package sync unchanged, Pi/Herdr preserved and full Codex package
  verified without downloading. Host/target doctor exited 0.
- Two consecutive chezmoi applies produced empty status with scripts excluded;
  `sshd -t` and managed configuration equality passed. Normal SSH Bash login
  rendered Starship and the expected ll/g aliases and exited cleanly with 0.
- Native tmux isolated PTY input, two-pane split and resize passed.
- Herdr 0.9.0 explicit-workspace headless run/read/split passed. Interactive
  SSH TUI input and Ctrl+b q detach/reattach preserved a marker in the same
  SSH connection; this was not a physical/network-disconnect test.
- Pi 0.85.1 credential-free UI rendered `No models available` / `/login`.
  The test deadline ended it with 124; no crash, graceful exit, login or
  model-call result is claimed.
- Codex 0.153.4 complete package and companions installed and --version passed;
  the normal sandbox failed with the exact overflowuid read error recorded
  in [its pitfall](../pitfalls/codex-overflowuid-permission-denied.md).
- Boot hook is executable and passes bash -n; no reboot/background test.
- Device GitHub TLS EOF/timeouts cleared after the user's own VPN choice.
  No global network change or offline-bundle implementation was added.

## Remaining acceptance

Physical/network-disruption recovery; Herdr interactive resize; screen-off
and background survival; Boot after an actual reboot; Pi/Codex authentication
and real model/tool use. Keep the observed Codex sandbox failure as a failed
gate until an independently verified compatible path exists. Do not weaken
protections to make the checklist green.

## Decision

Keep P1 open and partially validated. The first-device results establish
specific native capabilities, not complete runtime support or an OEM-wide
guarantee. Later results extend this record rather than erasing its limits.
