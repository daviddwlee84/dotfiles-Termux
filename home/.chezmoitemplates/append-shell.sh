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
        printf '%s\n' 'DOTFILES_TERMUX_BASHRC_SOURCED=1'
    fi
    cat <<'EOF'
[[ ! -r "$HOME/.config/dotfiles-termux/shell.bash" ]] || source "$HOME/.config/dotfiles-termux/shell.bash"
# <<< dotfiles-termux <<<
EOF
fi
