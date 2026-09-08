# Native Termux Bash; no installs, downloads or service starts at shell startup.
[[ -z ${DOTFILES_TERMUX_SHELL_LOADED:-} ]] || return 0
DOTFILES_TERMUX_SHELL_LOADED=1
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH";; esac
export PATH
EDITOR=${EDITOR:-vim}
PAGER=${PAGER:-less}
export EDITOR PAGER
if [[ $- == *i* ]]; then
    alias ll='ls -al'
    alias g='git'
    if [[ ${TERM:-dumb} != dumb ]] && command -v starship >/dev/null 2>&1; then
        eval "$(starship init bash)"
    fi
fi
# shellcheck source=/dev/null
[[ ! -r "$HOME/.config/dotfiles-termux/local.sh" ]] || source "$HOME/.config/dotfiles-termux/local.sh"
