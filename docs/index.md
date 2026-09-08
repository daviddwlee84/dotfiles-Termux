# Native development tools on Android

dotfiles-Termux turns Termux into a small development environment and provides
macOS/Linux helpers for first setup over ADB. It is a standalone experimental
repository inspired by dotfiles-iSH; it uses native Termux packages and does
not share iSH's Alpine bootstrap.

Start with the [setup guide](setup.md). The default includes chezmoi, Bash,
Starship, Git, Vim, tmux, development utilities, Node.js and Pi.
Public-key SSH and Termux:Boot integration are enabled; wake-lock is off.
Herdr and Codex are optional native experiments, with explicit
[compatibility checks](tools.md).

Termux uses Android's Linux kernel and its app-private filesystem. It is not
a Debian VM, and the ordinary Android ADB shell is not a Termux session.
Keep repositories and executables under Termux `$HOME`, not shared storage.
See the [official execution environment](https://github.com/termux/termux-packages/wiki/Termux-execution-environment).

| Task | Computer | Inside the Termux clone |
| --- | --- | --- |
| Discover/connect | `just devices`, `just ssh` | — |
| Initial provisioning | `just setup` | `bash bootstrap.sh setup` |
| Inspect health | `just doctor` | `bash bootstrap.sh doctor` |
| Preview/apply config | — | `just diff`, `just apply` |
| Synchronize packages | — | `just packages` |
| Fully upgrade packages | — | `just upgrade` |

The [SSH guide](ssh.md) explains LAN and USB-only access. The
[optional Linux userspace guide](proot.md) covers PRoot when a Linux
distribution is needed for Claude Code or another tool. PRoot is never
installed by the native bootstrap.

Desktop CI validates fixtures, scripts and rendered configuration. A green
build is not a claim that an Android device or coding-agent session has been
tested. See [verification levels](verification.md).
