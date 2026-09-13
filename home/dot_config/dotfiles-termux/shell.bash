# Native Termux Bash; no installs, downloads or service starts at shell startup.
DOTFILES_TERMUX_CONFIG_DIR=${DOTFILES_TERMUX_CONFIG_DIR:-$HOME/.config/dotfiles-termux}
# shellcheck source=/dev/null
source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"
[[ -z ${DOTFILES_TERMUX_SHELL_LOADED:-} ]] || return 0
DOTFILES_TERMUX_SHELL_LOADED=1
if [[ $- == *i* ]]; then
    _dotfiles_termux_dev_init bash "$(type -P dev)"
    # Official Termux uv package generates this file during installation.
    # shellcheck source=/dev/null
    [[ ! -r "$PREFIX/share/bash-completion/completions/uv" ]] || source "$PREFIX/share/bash-completion/completions/uv"
    if [[ ${TERM:-dumb} != dumb ]] && command -v starship >/dev/null 2>&1 && ! declare -F starship_precmd >/dev/null; then
        eval "$(starship init bash)"
    fi
fi
# shellcheck source=/dev/null
[[ ! -r "$DOTFILES_TERMUX_CONFIG_DIR/local.sh" ]] || source "$DOTFILES_TERMUX_CONFIG_DIR/local.sh"
