set -euo pipefail
candidate=$(mktemp)
trap 'rm -f "$candidate"' EXIT HUP INT TERM
cat >"$candidate"
if [[ ! -s $candidate ]]; then
    cat >"$candidate" <<'EOF'
# Preserve the startup files Bash used before this .bash_profile existed.
# These markers are deliberately not exported to child Bash processes.
if [[ -z ${DOTFILES_TERMUX_LOGIN_FORWARDING:-} ]]; then
    DOTFILES_TERMUX_LOGIN_FORWARDING=1
    unset DOTFILES_TERMUX_LOGIN_BASHRC_SEEN
    if [[ -r "$HOME/.bash_login" ]]; then
        source "$HOME/.bash_login"
    elif [[ -r "$HOME/.profile" ]]; then
        source "$HOME/.profile"
    fi
    # A .profile commonly sources .bashrc itself. Its managed marker prevents
    # repeating user rc commands while retaining rc aliases for SSH logins.
    if [[ $- == *i* && -z ${DOTFILES_TERMUX_LOGIN_BASHRC_SEEN:-} && -r "$HOME/.bashrc" ]]; then
        source "$HOME/.bashrc"
    fi
    unset DOTFILES_TERMUX_LOGIN_BASHRC_SEEN DOTFILES_TERMUX_LOGIN_FORWARDING
fi
EOF
fi
cat "$candidate"
if ! grep -qF '# >>> dotfiles-termux >>>' "$candidate"; then
    cat <<'EOF'

# >>> dotfiles-termux >>>
[[ ! -r "$HOME/.config/dotfiles-termux/shell.bash" ]] || source "$HOME/.config/dotfiles-termux/shell.bash"
# <<< dotfiles-termux <<<
EOF
fi
