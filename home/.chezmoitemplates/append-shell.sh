set -euo pipefail
candidate=$(mktemp)
trap 'rm -f "$candidate"' EXIT HUP INT TERM
cat >"$candidate"
cat "$candidate"
if ! grep -qF '# >>> dotfiles-termux >>>' "$candidate"; then
    cat <<'EOF'

# >>> dotfiles-termux >>>
EOF
    if [[ ${DOTFILES_MODIFY_BASHRC:-false} == true ]]; then
        cat <<'EOF'
[[ -z ${DOTFILES_TERMUX_LOGIN_FORWARDING:-} ]] || DOTFILES_TERMUX_LOGIN_BASHRC_SEEN=1
EOF
    fi
    cat <<'EOF'
[[ ! -r "$HOME/.config/dotfiles-termux/shell.bash" ]] || source "$HOME/.config/dotfiles-termux/shell.bash"
# <<< dotfiles-termux <<<
EOF
fi
