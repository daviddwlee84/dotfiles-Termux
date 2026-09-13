# Shared helpers; definitions deliberately reload in the same shell.
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH";; esac
export PATH
EDITOR=${EDITOR:-vim}
PAGER=${PAGER:-less}
export EDITOR PAGER
DOTFILES_TERMUX_CONFIG_DIR=${DOTFILES_TERMUX_CONFIG_DIR:-$HOME/.config/dotfiles-termux}
# shellcheck source=/dev/null
. "$DOTFILES_TERMUX_CONFIG_DIR/abspath.sh"

function source-rc {
    local rc
    if [ -n "${ZSH_VERSION:-}" ]; then
        rc="${ZDOTDIR:-$HOME}/.zshrc"
    elif [ -n "${BASH_VERSION:-}" ]; then
        rc="$HOME/.bashrc"
    else
        printf 'source-rc: Bash or zsh required\n' >&2; return 1
    fi
    [ -r "$rc" ] || { printf 'source-rc: cannot read %s\n' "$rc" >&2; return 1; }
    unset DOTFILES_TERMUX_SHELL_LOADED _DOTFILES_TERMUX_ZSH_LOCAL
    # shellcheck source=/dev/null
    . "$rc"
}

function chezmoi-cd {
    local destination
    destination=$(chezmoi source-path) || return
    [ -n "$destination" ] || return 1
    builtin cd -- "$destination" || return
}

# Yazi's cwd-file protocol; keep arguments and the program's exit status intact.
_dotfiles_termux_y() {
    local cwd_file cwd='' exit_code=0
    cwd_file=$(mktemp "${TMPDIR:-/tmp}/yazi-cwd.XXXXXX") || return
    command yazi "$@" --cwd-file="$cwd_file" || exit_code=$?
    if [ "$exit_code" -eq 0 ]; then
        # Yazi writes the path without a trailing newline. Read until EOF.
        IFS= read -r -d '' cwd <"$cwd_file" || :
        if [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
            builtin cd -- "$cwd" || exit_code=$?
        fi
    fi
    rm -f -- "$cwd_file"
    return "$exit_code"
}

# Preserve a pre-existing user shortcut; the managed implementation still reloads.
if ! command -v y >/dev/null 2>&1; then
    function y { _dotfiles_termux_y "$@"; }
fi

# Regenerate only when the binary path or modification time changes.
_dotfiles_termux_dev_init() {
    local kind=$1 binary=$2 cache script staged identity recorded
    [ -n "$binary" ] || return 0
    cache="${DOTFILES_TERMUX_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles-termux}/dev"
    [ ! -L "$cache" ] || return 1
    [ -d "$cache" ] || mkdir -p "$cache" || return 1
    for script in init completion; do
        identity="$cache/$kind-$script.binary"
        [ ! -L "$cache/$kind-$script" ] && [ ! -L "$identity" ] || return 1
        recorded=''
        [ ! -f "$identity" ] || IFS= read -r recorded <"$identity"
        if [ ! -r "$cache/$kind-$script" ] || [ "$binary" -nt "$cache/$kind-$script" ] || [ "$recorded" != "$binary" ]; then
            staged=$(mktemp "$cache/.generate.XXXXXX") || return 1
            if { [ "$script" = init ] && "$binary" shell-init "$kind" >"$staged"; } || { [ "$script" = completion ] && "$binary" completion "$kind" >"$staged"; }; then
                chmod 600 "$staged" && mv "$staged" "$cache/$kind-$script"
                printf '%s\n' "$binary" >"$identity"
            else
                rm -f "$staged"; return 1
            fi
        fi
        # shellcheck source=/dev/null
        . "$cache/$kind-$script"
    done
}

case $- in
    *i*)
        alias ll='ls -al'; alias g='git'; alias reload='source-rc'
        command -v lg >/dev/null 2>&1 || alias lg='lazygit'
        ;;
esac
