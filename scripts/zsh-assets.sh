#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ZSH_REPO=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=scripts/pair.sh
source "$ZSH_REPO/scripts/pair.sh"
termux_context
action=${1:-check}
[[ $action == install || $action == check ]] || exit 2
base="$HOME/.local/share/dotfiles-termux/zsh"
[[ $action != install ]] || termux_safe_dir "$base"

install_asset() (
    set -euo pipefail
    local name=$1 row arch version url digest format member bytes destination temp staged receipt cleanup
    row=$(awk -F '|' -v name="$name" '$1==name {print; exit}' "$ZSH_REPO/config/assets.lock")
    IFS='|' read -r name arch version url digest format member bytes <<<"$row"
    [[ $arch == any && $version =~ ^[a-f0-9]{40}$ && $digest =~ ^[a-f0-9]{64}$ && $bytes =~ ^[0-9]+$ && $format == tar.gz && $url == https://* && $member =~ ^[a-zA-Z0-9._-]+$ ]] || { termux_die "Invalid zsh asset lock: $name"; return 1; }
    destination="$base/$name-$version"
    receipt="$digest $bytes"
    if [[ -e $destination || -L $destination ]]; then
        [[ ! -L $destination && -d $destination && -f $destination/.dotfiles-receipt && ! -L $destination/.dotfiles-receipt && $(cat "$destination/.dotfiles-receipt") == "$receipt" ]] || { termux_die "Existing zsh asset preserved: $destination"; return 1; }
    else
        [[ $action == install ]] || { termux_die 'zsh assets are missing; run bootstrap.sh packages with zsh selected'; return 1; }
        temp=$(mktemp -d "$base/.install.XXXXXX")
        # Bash 3.2 may drop function locals before this subshell's EXIT trap.
        # Capture a shell-quoted path now, rather than expanding it on exit.
        printf -v cleanup 'rm -rf -- %q' "$temp"
        # shellcheck disable=SC2064 # Intentionally capture the quoted local now.
        trap "$cleanup" EXIT
        curl --fail --location --proto '=https' --tlsv1.2 --retry 2 --connect-timeout 15 --max-time 600 --output "$temp/download" "$url"
        [[ $(wc -c <"$temp/download" | tr -d ' ') == "$bytes" ]] || { termux_die "$name size mismatch"; return 1; }
        printf '%s  %s\n' "$digest" "$temp/download" | sha256sum -c - >/dev/null
        # Python's data filter rejects traversal, device nodes and escaping links.
        python3 - "$temp/download" "$temp" "$member" <<'PY'
import pathlib, sys, tarfile
archive, destination, root = sys.argv[1:]
with tarfile.open(archive) as stream:
    for item in stream.getmembers():
        parts = pathlib.PurePosixPath(item.name).parts
        if not parts or parts[0] != root or '..' in parts:
            raise ValueError('unexpected zsh archive member')
    stream.extractall(destination, filter='data')
PY
        staged="$temp/$member"
        [[ -d $staged && ! -L $staged ]] || return 1
        printf '%s\n' "$receipt" >"$staged/.dotfiles-receipt"
        mv -nT "$staged" "$destination"
        [[ ! -e $staged ]] || { termux_die "Concurrent zsh asset preserved: $destination"; return 1; }
    fi
    case "$name" in
        oh-my-zsh) test -r "$destination/oh-my-zsh.sh" ;;
        zsh-autosuggestions) test -r "$destination/zsh-autosuggestions.zsh" ;;
        zsh-syntax-highlighting) test -r "$destination/zsh-syntax-highlighting.zsh" ;;
    esac
    printf '%s\n' "$destination"
)

omz=$(install_asset oh-my-zsh)
suggest=$(install_asset zsh-autosuggestions)
highlight=$(install_asset zsh-syntax-highlighting)
if [[ $action == install ]]; then
    [[ ! -L $base/assets.sh ]] || { termux_die 'zsh asset index symlink preserved'; exit 1; }
    if [[ -e $base/assets.sh ]] && ! grep -qx '# Managed by dotfiles-Termux zsh-assets' "$base/assets.sh"; then
        termux_die 'Foreign zsh asset index preserved'; exit 1
    fi
    staged=$(mktemp "$base/.assets.XXXXXX")
    trap 'rm -f "$staged"' EXIT
    {
        printf '# Managed by dotfiles-Termux zsh-assets\n'
        printf 'DOTFILES_TERMUX_OMZ=%q\n' "$omz"
        printf 'DOTFILES_TERMUX_AUTOSUGGEST=%q\n' "$suggest"
        printf 'DOTFILES_TERMUX_HIGHLIGHT=%q\n' "$highlight"
    } >"$staged"
    chmod 600 "$staged"
    mv "$staged" "$base/assets.sh"
else
    [[ -f $base/assets.sh && ! -L $base/assets.sh ]] || { termux_die 'zsh asset index missing; run packages'; exit 1; }
fi
