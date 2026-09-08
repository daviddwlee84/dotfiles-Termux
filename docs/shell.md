# Shell and configuration

The native shell is Termux Bash. Keep its actual `$PREFIX` and `$HOME` paths;
do not assume `/usr/bin`, `/etc`, or a desktop Linux username. No root access,
Ansible, Homebrew, or desktop shell framework is needed on the device.

chezmoi manages the `home/` source root. The bootstrap preserves existing
shell content and adds the managed configuration without turning a foreign
chezmoi source into this repository. Inspect changes with `just diff`, then
use `just apply`. Existing user-owned settings and unrelated SSH keys remain
in place.

Starship initializes in interactive Bash sessions. Vim, Git and tmux
provide a usable editor/source-control/multiplexer baseline before optional
agents are configured. Try both a local Termux tab and a new SSH login when
checking prompt and terminal behavior.

## Native paths

| Purpose | Location |
| --- | --- |
| Home and repositories | `$HOME` (normally `/data/data/com.termux/files/home`) |
| Termux programs | `$PREFIX/bin` |
| Termux package configuration | `$PREFIX/etc` |
| Temporary files | `$TMPDIR` |
| Dotfile source root | The clone's `home/` |
| This repository's saved choices | `~/.config/dotfiles-termux/settings` |

Keep project checkouts in app-private storage. Shared Android storage can be
`noexec`, cannot preserve all Unix file semantics, and is a poor location for
Git repositories or binaries. `termux-setup-storage` is an optional separate
step for exchanging files; bootstrap does not request broad storage access.
[Official filesystem/execution notes](https://github.com/termux/termux-packages/wiki/Termux-execution-environment#file-execution-and-special-file-features-not-allowed-in-external-storage).

## Daily workflow

```sh
# In the Termux repository clone:
just diff
just apply
bash bootstrap.sh update
```

These operations do not upgrade packages. Use `just packages` or `just upgrade`
for explicit full package synchronization. If a new configuration needs a new
dependency, run that synchronization separately.

Termux uses Bionic libc. A Linux ARM64 download is not automatically a native
Termux package: a matching CPU architecture does not prove loader, paths,
DNS, PTY or sandbox compatibility. Prefer `pkg` for packaged tools and follow
the [agent compatibility guide](tools.md) for experiments.
