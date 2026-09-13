#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
SHELL_REPO=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=scripts/pair.sh
source "$SHELL_REPO/scripts/pair.sh"
termux_context
termux_defaults
case ${1:-doctor} in
    default) printf '%s\n' "$PRIMARY_SHELL"; exit ;;
    doctor)
        printf 'Interactive shell: selected=%s current=%s\n' "$PRIMARY_SHELL" "$(termux_current_shell)"
        if [[ $PRIMARY_SHELL == zsh ]]; then bash "$SHELL_REPO/scripts/zsh-assets.sh" check; fi
        exit ;;
    backup-herdr)
        PRIMARY_SHELL=${2:-$PRIMARY_SHELL}
        if [[ $PRIMARY_SHELL == zsh ]]; then
            [[ -x $PREFIX/bin/zsh ]] || exit 0
            bash "$SHELL_REPO/scripts/zsh-assets.sh" check >/dev/null 2>&1 || exit 0
        fi
        termux_safe_dir "$TERMUX_STATE"
        python3 "$SHELL_REPO/scripts/herdr-shell.py" backup "$HOME/.config/herdr/config.toml" "$TERMUX_STATE" "$PREFIX" "$PRIMARY_SHELL"
        exit ;;
    configure) ;;
    *) exit 2 ;;
esac
termux_validate_settings
[[ -x $PREFIX/bin/$PRIMARY_SHELL ]] || { termux_die "$PRIMARY_SHELL is not installed; run bootstrap.sh packages --primary-shell $PRIMARY_SHELL; login shell unchanged"; exit 1; }
if [[ $PRIMARY_SHELL == zsh ]]; then
    bash "$SHELL_REPO/scripts/zsh-assets.sh" check
    "$PREFIX/bin/zsh" -n "$HOME/.zshrc"
    timeout --kill-after=2 10 "$PREFIX/bin/zsh" -i -c '(( $+functions[abspath] && $+functions[compdef] ))' </dev/null
fi
current=$(termux_current_shell)
if [[ $current == unknown && ${DOTFILES_SHELL_EXPLICIT:-false} != true ]]; then
    termux_die 'Unrecognized login shell preserved; choose --primary-shell explicitly'; exit 1
fi
if [[ $current != "$PRIMARY_SHELL" ]]; then
    termux_safe_dir "$HOME/.termux"
    [[ ! -e $HOME/.termux/shell || -L $HOME/.termux/shell ]] || { termux_die 'Non-symlink shell override preserved'; exit 1; }
    # Older Termux chsh prepends PREFIX even to an absolute argument. The
    # relative name is supported by both those versions and current chsh.
    chsh -s "$PRIMARY_SHELL"
    [[ $(termux_current_shell) == "$PRIMARY_SHELL" ]] || { termux_die 'Login shell selection did not persist'; exit 1; }
fi

# The modify_ target preserves custom Herdr content and owns seed changes.
if [[ ,$OPTIONAL_TOOLS, == *,herdr,* && -f $HOME/.config/herdr/config.toml ]]; then
    python3 "$SHELL_REPO/scripts/herdr-shell.py" doctor "$HOME/.config/herdr/config.toml" "$TERMUX_STATE" "$PREFIX" "$PRIMARY_SHELL"
fi
