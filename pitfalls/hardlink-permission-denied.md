# Native tool install stops with hard-link Permission denied

**Symptoms**: `Permission denied`; `ln -T`; verified Herdr/Codex asset starts
with `--version` but final installation fails
**First seen**: 2026-09-09
**Affects**: the hard-link promotion path in `scripts/tools.sh`, observed on
Xiaomi Pad 6S Pro 12.4 / Android 15 / API 35 / HyperOS 2.0 / ARM64
**Status**: no-clobber rename fix and regression coverage; later full device
setup rerun exited 0; individual runtime gates remain separate

## Symptom

Both verified Herdr 0.9.0 and Codex 0.153.4 assets executed `--version` on
native Termux. Promoting the staged executable with `ln -T` then failed in
app-private directories. The exact confirmed stderr fragment is:

```text
Permission denied
```

This is an excerpt, not an invented full transcript; device-specific paths
are intentionally absent. A controlled scratch check reproduced the denied
hard link while a rename succeeded. `mv -nT` preserved an existing target.

## Mechanism and limits of the diagnosis

The installer used a hard link to avoid replacing a destination that appeared
concurrently. The tested Android environment denied that operation even
though file creation/copying and rename worked in the private directory.
The responsible policy or filesystem mechanism was not established. Do not
attribute it to SELinux, a specific vendor policy, a read-only mount, or all
Android devices without further evidence.

Successful `--version` output is not an installation commit: promotion must
also succeed before recording an installed status.

## Fix

Stage the verified candidate in the destination directory, then use GNU
`mv -nT` for no-clobber promotion. Verify that the staged path disappeared.
If the destination already exists, `mv -n` can return success while skipping
the move; the remaining staged file must therefore produce a preserved-
destination failure, not a false installed result.

Keep an existing binary, symlink or directory untouched. Do not request root,
relax Android protections or relocate executables to shared storage as a
workaround. See the implementation in [`scripts/tools.sh`](../scripts/tools.sh).

## Prevention

Regression coverage in [`tests/test_tools.py`](../tests/test_tools.py) checks
an existing/concurrently created destination and the success-on-skip case.
Continue testing checksum/size rejection before candidate execution and
preservation of unrelated installed tools. A later full setup rerun exited
0; Herdr and Codex runtime results are still tracked separately, including
the observed Codex sandbox failure.

## Related

- [Partial device matrix](../backlog/android-runtime-matrix.md)
- [Native compatibility investigation](../backlog/native-agent-compatibility.md)
- [Current tool guide](../docs/tools.md)
