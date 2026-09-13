# Native Termux interactive zsh. Dependencies are installed by explicit setup.
[[ -o interactive ]] || return 0
DOTFILES_TERMUX_CONFIG_DIR=${DOTFILES_TERMUX_CONFIG_DIR:-$HOME/.config/dotfiles-termux}
source "$DOTFILES_TERMUX_CONFIG_DIR/common.sh"

if [[ -z ${_DOTFILES_TERMUX_ZSH_CORE:-} ]]; then
    _dft_assets="$HOME/.local/share/dotfiles-termux/zsh/assets.sh"
    if [[ ! -r $_dft_assets ]]; then
        print -u2 'Termux zsh plugins are pending; run bootstrap.sh packages --primary-shell zsh.'
        unset _dft_assets
        return 0
    fi
    source "$_dft_assets"
    unset _dft_assets
    export ZSH="$DOTFILES_TERMUX_OMZ"
    ZSH_CUSTOM="$ZSH/custom"
    ZSH_CACHE_DIR="${DOTFILES_TERMUX_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles-termux}/omz"
    [[ -d $ZSH_CACHE_DIR ]] || mkdir -p "$ZSH_CACHE_DIR"
    ZSH_COMPDUMP="$ZSH_CACHE_DIR/zcompdump-$ZSH_VERSION"
    ZSH_THEME=''
    DISABLE_AUTO_TITLE=true
    zstyle ':omz:update' mode disabled
    typeset -U fpath
    fpath=("$PREFIX/share/zsh/site-functions" $fpath)
    plugins=(git)
    HISTFILE="$HOME/.zsh_history"
    HISTSIZE=10000
    SAVEHIST=10000
    source "$ZSH/oh-my-zsh.sh"
    bindkey -e
    source "$DOTFILES_TERMUX_AUTOSUGGEST/zsh-autosuggestions.zsh"
    _DOTFILES_TERMUX_ZSH_CORE=1
fi

_dotfiles_termux_dev_init zsh "$(whence -p dev)"
if [[ ${TERM:-dumb} != dumb ]] && (( $+commands[starship] && ! $+functions[prompt_starship_precmd] )); then
    eval "$(starship init zsh)"
fi
if [[ -z ${_DOTFILES_TERMUX_ZSH_LOCAL:-} ]]; then
    [[ ! -r "$DOTFILES_TERMUX_CONFIG_DIR/local.zsh" ]] || source "$DOTFILES_TERMUX_CONFIG_DIR/local.zsh"
    _DOTFILES_TERMUX_ZSH_LOCAL=1
fi
# Highlight after all widget/key bindings, without wrapping them repeatedly.
if (( ! $+functions[_zsh_highlight] )); then
    source "$DOTFILES_TERMUX_HIGHLIGHT/zsh-syntax-highlighting.zsh"
fi
