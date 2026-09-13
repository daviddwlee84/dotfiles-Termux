# Herdr config: has changed since chezmoi last wrote it?

During the Bash/zsh selection work on 2026-09-13, retargeting the Herdr
`create_config.toml.tmpl` output from an after-apply script caused the next
non-interactive apply to fail:

```text
.config/herdr/config.toml has changed since chezmoi last wrote it?
chezmoi: .config/herdr/config.toml: could not open a new TTY: open /dev/tty: device not configured
```

Keeping the template's Bash default constant did not fix it: the after-hook
still changed the destination outside chezmoi's writer. Tests that deliberately
edited the managed settings file to simulate an old version produced the same
class of conflict; they must establish an actual old rendered baseline instead.

The Herdr target now uses a pure `modify_` transformation. It reads the current
contents, retargets only an exact unchanged dotfiles seed, and returns custom
contents unchanged. A before-apply script backs up a seed that will change;
the after-apply shell selector no longer writes the Herdr config. Missing zsh
dependencies leave the Herdr target unchanged too.

The regression test covers repeated apply, switching zsh → Bash → zsh, and
preserving custom Herdr content. Do not bypass this conflict with global
`--force` or put destination writes back into the after-hook.
