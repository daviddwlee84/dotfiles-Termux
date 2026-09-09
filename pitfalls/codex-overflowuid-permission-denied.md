# Codex sandbox cannot read overflowuid: Permission denied

**Symptoms**: `bwrap: Can't read /proc/sys/kernel/overflowuid: Permission denied`;
Codex --version works but the normal sandbox does not start
**First seen**: 2026-09-09
**Affects**: official Codex 0.153.4 ARM64 Linux-musl package on the tested
Xiaomi Pad 6S Pro 12.4 / Android 15 / API 35 / HyperOS 2.0 device
**Status**: normal-sandbox compatibility gate failed; no validated fix or bypass

## Symptom

The complete official package was installed at repository commit `38cbc3c`,
including the code-mode host, rg, bwrap, zsh and package manifest. The main
executable passed --version, but the normal sandbox reported:

```text
bwrap: Can't read /proc/sys/kernel/overflowuid: Permission denied
```

The denied file path is a standard kernel path, not a device identifier.
No private runtime paths or account data are recorded here.

## What is established

The bundled sandbox helper was present and encountered a denied read while
starting the normal sandbox. This is distinct from an incomplete standalone-
binary installation and from successful CLI/UI startup. The specific policy
that denies the read was not established. In particular, the error alone
is not evidence that user namespaces are disabled, or that all later
sandbox facilities would otherwise work.

## Handling

Retain the failed gate and exact error. Do not use bypass flags, disable
Android protections, or claim success from --version/doctor output. PRoot
has not been validated as a remedy and cannot be assumed to add kernel
capabilities. A future compatibility investigation must preserve the
intended sandbox and independently test normal command execution plus the
expected denied-write behavior.

## Prevention

Install the full pinned distribution and verify every required companion.
Keep package integrity, startup, UI and sandbox results separate. The
isolated probe in [`scripts/tools.sh`](../scripts/tools.sh) must fail when
normal sandbox initialization fails; do not weaken its assertions.

## Related

- [Current tool behavior](../docs/tools.md)
- [Partial runtime matrix](../backlog/android-runtime-matrix.md)
- [Native compatibility research](../backlog/native-agent-compatibility.md)
- [Official sandbox documentation](https://learn.chatgpt.com/docs/sandboxing)
