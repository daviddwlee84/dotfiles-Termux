# Optional Linux userspace

Use a PRoot distro when a tool needs a conventional Linux distribution, for
example Claude Code's Linux loader and filesystem layout. This is a manual,
opt-in fallback. The native bootstrap never installs PRoot or changes an
agent command to enter it silently.

Keep Termux's native sshd as the entry point. After SSH login, enter the
guest explicitly. Keep guest tools/configuration in the guest and native
Termux tools/configuration in Termux; do not apply this repository inside
the guest or reuse a native tool's private state directory for both.

## Prepare a same-architecture guest

In Termux, fully synchronize its packages before adding PRoot-Distro:

```sh
pkg update && pkg upgrade -y && pkg install -y proot-distro
proot-distro install ubuntu:24.04 --name agents
proot-distro login agents
```

The named guest is an example; inspect existing installations before reusing
that name. On an ARM64 phone, keep the guest ARM64. The current PRoot-Distro
supports OCI images and does not require a Docker daemon or device root.
Check the [upstream CLI documentation](https://github.com/termux/proot-distro#readme)
if your installed version uses a different image syntax.

Inside the Ubuntu guest:

```sh
apt update && apt full-upgrade -y
apt install -y ca-certificates curl git vim tmux
mkdir -p "$HOME/projects"
```

Install Claude Code using the [official Linux instructions](https://code.claude.com/docs/en/setup)
inside this guest, preserving the installer's verification. Run `claude`
from a guest project and complete authentication yourself. For Herdr, use
the upstream Linux installation instructions at [herdr.dev](https://herdr.dev/)
and verify a shell pane and detach/reattach before relying on it.

Codex can also be evaluated in the guest using its
[official Linux instructions](https://learn.chatgpt.com/docs/codex/cli).
A working Linux loader does not prove a working agent sandbox: run the
same sandbox checks required for the native experiment.

To exit the guest, run `exit`; to return later:

```sh
proot-distro login agents
```

If persistence across the host SSH connection is needed, start the guest
inside a native Termux tmux session and detach that session. Current
PRoot-Distro also supports detached sessions and `ps`/`kill` management;
use its documentation for that mode and keep logs for long-running commands.
Do not start a second guest sshd just to reach an environment already
accessible through native Termux SSH.

## Performance and limits

For a matching ARM64 guest, PRoot rewrites syscall paths rather than
emulating ARM64 instructions. Nevertheless, syscall interception adds cost:
package installs, compilation, Git scans and workloads touching many small
files can be noticeably slower. A terminal session waiting for a remote
model has a different workload; there is no fixed slowdown percentage that
applies to every phone. Measure the same checkout and command natively and
in the guest before deciding where to work.

PRoot does not add kernel namespaces, cgroups or real root privileges.
Individual long-running processes can work; full init systems and service
supervisors are generally outside its scope. Android battery/process limits
still apply. [Official limitations](https://github.com/termux/proot-distro#limitations).

Consequently, PRoot cannot manufacture kernel features needed by Codex or
Claude's sandbox. If the ordinary sandbox fails, record the failure and
use a supported remote machine for that workflow; do not disable it as a
compatibility fix. No guest runtime or agent authentication is claimed as
verified by this repository's desktop CI.
