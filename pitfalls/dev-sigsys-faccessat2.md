# dev repo open: SIGSYS: bad system call in syscall.faccessat2

Observed 2026-09-13 on the ARM64 Android 15 device, with dev-cli v0.2.33's
official Linux release. `dev --version`, shell-init/completion generation,
config initialization and an empty `dev ls --json` succeeded. Opening a real
scratch Git repository failed with exit 2:

```text
SIGSYS: bad system call
syscall.faccessat2
syscall.Faccessat
internal/syscall/unix.Eaccess
os/exec.findExecutable
os/exec.lookPath
os/exec.Command
github.com/daviddwlee84/dev-cli/internal/gitx.runEnv
```

## Cause

The release was compiled for Linux with Go 1.26.4. Go's executable lookup
attempted `faccessat2` while locating Git. Android's app syscall filter rejected
that syscall. The Android Go target takes a different path in
[Eaccess](https://github.com/golang/go/blob/go1.27.1/src/internal/syscall/unix/eaccess.go),
allowing executable lookup to fall back to permission bits.

Static linkage and a passing `--version` do not prove that a Linux Go binary
can execute subprocesses in Termux. No Android restriction was changed.

## Fix and migration

The installer now verifies the v0.2.33 source archive, then builds with native
Termux Go/Clang, `GOOS=android`, `CGO_ENABLED=1`, `GOTOOLCHAIN=local`, and
`-mod=readonly`. Go dependencies retain the upstream `go.sum`. Native Go 1.27.1
produced an Android PIE executable using `/system/bin/linker64`.

Fresh installs use this route automatically when `dev` is selected. The
package layer adds `golang` only for that selection. Ordinary chezmoi apply
does not compile or install software.

Existing binaries are preserved by policy. If the earlier Linux candidate
is installed at `~/.local/bin/dev`, this guarded migration verifies that
**exact known binary**, retains a private backup, then installs the native
build. Run inside the updated Termux clone; adjust the optional selection
deliberately if you do not want all three tools selected:

```bash
(
    set -e
    printf '%s  %s\n' 9f2b4da1a07179d698914eb1afd59c7574e2fa22102bf16742584720a6087a54 "$HOME/.local/bin/dev" | sha256sum -c -
    mkdir -p "$HOME/.local/state/dotfiles-termux"
    dev_backup=$(mktemp "$HOME/.local/state/dotfiles-termux/dev-linux-backup.XXXXXX")
    mv "$HOME/.local/bin/dev" "$dev_backup"
    printf 'Previous binary saved at %s\n' "$dev_backup"
    bash bootstrap.sh packages --with herdr,codex,dev
)
```

This session retained the previous binary before running the native installer.
The replacement passed parent-shell navigation into a scratch Git repository
whose path contains spaces, Markdown note creation, and SQLite FTS search.
The temporary HOME, Git repository, notes and index were then removed.

## Prevention

- Keep the source archive version, hash and size pinned together.
- Build for Android with Termux's toolchain; do not substitute the Linux release
  or permit Go's automatic generic toolchain download.
- Verify at least one Git-backed operation, not just `--version`.
- Keep full task/worktree, runtime integration and network acceptance distinct
  from these bounded checks.
