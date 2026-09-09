#!/data/data/com.termux/files/usr/bin/bash
# Install the complete pinned Codex distribution without replacing user files.
set -euo pipefail
CODEX_PACKAGE_REPO=$(CDPATH='' cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=scripts/pair.sh
source "$CODEX_PACKAGE_REPO/scripts/pair.sh"

codex_package_help() {
    printf '%s\n' 'Usage: bash scripts/codex-package.sh [install]' \
        'Installs or repairs the pinned ARM64 package, including its sandbox companions.' \
        'Exact existing files are retained; differing files and symlinks are preserved.' \
        'Installation verifies launch only; run the separate normal sandbox probe.'
}

codex_package_member_allowed() {
    case "$1" in
        bin/codex|bin/codex-code-mode-host|codex-package.json|codex-path/rg|codex-resources/bwrap|codex-resources/zsh/bin/zsh) return 0 ;;
        *) return 1 ;;
    esac
}

codex_package_load_lock() {
    local name hash bytes mode extra seen='|' count=0
    while IFS='|' read -r name hash bytes mode extra; do
        [[ -n $name && $name != \#* ]] || continue
        if ! codex_package_member_allowed "$name" || ! [[ -z $extra && $hash =~ ^[a-f0-9]{64}$ && $bytes =~ ^[0-9]+$ ]]; then
            termux_die 'Invalid Codex package member lock'; return 1;
        fi
        case "$seen" in *"|$name|"*) termux_die 'Duplicate Codex package member lock'; return 1;; esac
        if [[ $name == codex-package.json ]]; then
            [[ $mode == 0644 ]] || return 1
        else
            [[ $mode == 0755 ]] || return 1
        fi
        seen+="$name|"
        count=$((count + 1))
    done <"$CODEX_PACKAGE_REPO/config/codex-package-files.lock"
    [[ $count == 6 ]] || { termux_die 'Incomplete Codex package member lock'; return 1; }
}

codex_package_member_row() {
    awk -F '|' -v name="$1" '$1==name {print; exit}' "$CODEX_PACKAGE_REPO/config/codex-package-files.lock"
}

codex_package_parents_safe() {
    local relative=$1 current=$HOME component remaining=".local/${1%/*}"
    [[ $relative == */* ]] || remaining=.local
    while [[ -n $remaining ]]; do
        component=${remaining%%/*}
        current="$current/$component"
        [[ ! -L $current && ( ! -e $current || -d $current ) ]] || {
            termux_die "Codex parent path preserved: $current"; return 1;
        }
        [[ $remaining == */* ]] || break
        remaining=${remaining#*/}
    done
}

codex_package_file_matches() {
    local path=$1 hash=$2 bytes=$3 mode=$4 actual_mode
    [[ ! -L $path && -f $path ]] || return 1
    [[ $(wc -c <"$path" | tr -d '[:space:]') == "$bytes" ]] || return 1
    actual_mode=$(stat -c '%a' "$path") || return 1
    [[ 0$actual_mode == "$mode" ]] || return 1
    printf '%s  %s\n' "$hash" "$path" | sha256sum -c - >/dev/null 2>&1
}

codex_package_preflight() {
    local name hash bytes mode path
    CODEX_PACKAGE_COMPLETE=true
    while IFS='|' read -r name hash bytes mode; do
        [[ -n $name && $name != \#* ]] || continue
        codex_package_parents_safe "$name" || return 1
        path="$HOME/.local/$name"
        if [[ -e $path || -L $path ]]; then
            codex_package_file_matches "$path" "$hash" "$bytes" "$mode" || {
                termux_die "Different Codex package file preserved: $path"; return 1;
            }
        else
            CODEX_PACKAGE_COMPLETE=false
        fi
    done <"$CODEX_PACKAGE_REPO/config/codex-package-files.lock"
}

codex_package_verify_archive() {
    local archive=$1 stage=$2 permissions _owner bytes _date _clock name normalized row hash expected_bytes mode
    local seen='|' count=0 expected_permissions
    # Inspect logical archive members before extracting anything. Only fixed
    # regular files and the known package directories are accepted.
    tar -tvzf "$archive" --numeric-owner --full-time --quoting-style=literal >"$stage/archive-members"
    while read -r permissions _owner bytes _date _clock name; do
        [[ -n $permissions && -n $name ]] || { termux_die 'Malformed Codex tar metadata'; return 1; }
        case "$permissions" in
            d*)
                normalized=${name%/}
                case "$normalized" in bin|codex-path|codex-resources|codex-resources/zsh|codex-resources/zsh/bin) ;;
                    *) termux_die "Unexpected Codex archive directory: $name"; return 1;;
                esac
                continue
                ;;
            -*) ;;
            *) termux_die "Non-regular Codex archive member rejected: $name"; return 1 ;;
        esac
        codex_package_member_allowed "$name" || { termux_die "Unexpected Codex archive member: $name"; return 1; }
        case "$seen" in *"|$name|"*) termux_die "Duplicate Codex archive member: $name"; return 1;; esac
        seen+="$name|"
        count=$((count + 1))
        row=$(codex_package_member_row "$name")
        IFS='|' read -r name hash expected_bytes mode <<<"$row"
        [[ $mode == 0755 ]] && expected_permissions=-rwxr-xr-x || expected_permissions=-rw-r--r--
        [[ $bytes == "$expected_bytes" && $permissions == "$expected_permissions" ]] || {
            termux_die "Codex archive member size/mode mismatch: $name"; return 1;
        }
    done <"$stage/archive-members"
    [[ $count == 6 ]] || { termux_die 'Codex archive is missing a required companion'; return 1; }
    while IFS='|' read -r name hash bytes mode; do
        [[ -n $name && $name != \#* ]] || continue
        mkdir -p "$stage/package/$(dirname "$name")"
        # No broad extraction: each fixed file is written through stdout into
        # our private staging directory, never through archive-owned paths.
        tar -xOzf "$archive" --no-wildcards -- "$name" >"$stage/package/$name"
        chmod "$mode" "$stage/package/$name"
        codex_package_file_matches "$stage/package/$name" "$hash" "$bytes" "$mode" || {
            termux_die "Codex archive member checksum mismatch: $name"; return 1;
        }
    done <"$CODEX_PACKAGE_REPO/config/codex-package-files.lock"
}

codex_package_publish_member() {
    local name=$1 stage=$2 row hash bytes mode destination parent candidate
    row=$(codex_package_member_row "$name")
    IFS='|' read -r name hash bytes mode <<<"$row"
    destination="$HOME/.local/$name"
    candidate="$stage/package/$name"
    codex_package_parents_safe "$name" || return 1
    parent=$(dirname "$destination")
    termux_safe_dir "$parent" || return 1
    if [[ -e $destination || -L $destination ]]; then
        codex_package_file_matches "$destination" "$hash" "$bytes" "$mode" || {
            termux_die "Concurrent Codex destination preserved: $destination"; return 1;
        }
        return 0
    fi
    # Android app storage can forbid hard links. GNU mv -nT performs a
    # no-clobber rename on this filesystem and never treats a raced-in dir as
    # a place to put the file. It returns success even when it skips a target.
    mv -nT "$candidate" "$destination" || return 1
    if [[ -e $candidate ]]; then
        codex_package_file_matches "$destination" "$hash" "$bytes" "$mode" || {
            termux_die "Concurrent Codex destination preserved: $destination; rerun after review"; return 1;
        }
    fi
    codex_package_file_matches "$destination" "$hash" "$bytes" "$mode" || {
        termux_die "Published Codex file failed verification: $destination"; return 1;
    }
}

codex_package_record() {
    termux_safe_dir "$TERMUX_STATE/tools"
    [[ ! -L $TERMUX_STATE/tools/codex.status ]] || return 1
    printf '%s\n' "launch-only:$1; verified package companions; sandbox,interactive,network acceptance pending" >"$TERMUX_STATE/tools/codex.status"
}

codex_package_install() (
    set -euo pipefail
    termux_context
    codex_package_load_lock
    local arch row name version url digest format entrypoint bytes extra stage path hash mode
    arch=$(uname -m)
    row=$(awk -F '|' -v arch="$arch" '$1=="codex" && $2==arch {print; exit}' "$CODEX_PACKAGE_REPO/config/assets.lock")
    [[ -n $row ]] || { termux_die "Codex package has no locked candidate for $arch"; return 1; }
    IFS='|' read -r name arch version url digest format entrypoint bytes extra <<<"$row"
    [[ -z $extra && $url == https://* && $digest =~ ^[a-f0-9]{64}$ && $bytes =~ ^[0-9]+$ && $format == tar.gz && $entrypoint == bin/codex ]] || {
        termux_die 'Invalid complete Codex archive lock'; return 1;
    }
    path=$(command -v codex || true)
    if [[ -n $path && $path != "$HOME/.local/bin/codex" ]]; then
        termux_die "External Codex preserved: $path; select the managed package explicitly before installing"; return 1
    fi
    codex_package_preflight
    if [[ $CODEX_PACKAGE_COMPLETE == true ]]; then
        SHELL="$PREFIX/bin/bash" TMPDIR="$PREFIX/tmp" timeout --kill-after=2 15 "$HOME/.local/bin/codex" --version
        codex_package_record "$version"
        termux_say 'Complete Codex package verified; no download needed.'
        return 0
    fi
    termux_safe_dir "$HOME/.local"
    stage=$(mktemp -d "$HOME/.local/.codex-package.XXXXXX")
    trap 'rm -rf "$stage"' EXIT
    curl --fail --location --proto '=https' --tlsv1.2 --retry 2 --connect-timeout 15 \
        --max-time 600 --output "$stage/archive.tar.gz" "$url"
    [[ $(wc -c <"$stage/archive.tar.gz" | tr -d '[:space:]') == "$bytes" ]] || { termux_die 'Codex package archive size mismatch'; return 1; }
    printf '%s  %s\n' "$digest" "$stage/archive.tar.gz" | sha256sum -c - >/dev/null || { termux_die 'Codex package archive SHA-256 mismatch'; return 1; }
    codex_package_verify_archive "$stage/archive.tar.gz" "$stage"
    SHELL="$PREFIX/bin/bash" TMPDIR="$PREFIX/tmp" timeout --kill-after=2 15 "$stage/package/bin/codex" --version
    # Recheck the entire destination before publishing. Existing standalone
    # codex with the exact pinned main-binary bytes is retained during repair.
    codex_package_preflight
    while IFS='|' read -r name hash bytes mode; do
        [[ -n $name && $name != \#* && $name != bin/codex ]] || continue
        codex_package_publish_member "$name" "$stage"
    done <"$CODEX_PACKAGE_REPO/config/codex-package-files.lock"
    codex_package_publish_member bin/codex "$stage"
    codex_package_preflight
    [[ $CODEX_PACKAGE_COMPLETE == true ]] || return 1
    codex_package_record "$version"
    termux_say 'Codex package installed with verified companions; normal sandbox acceptance remains separate.'
)

case "${1:-install}" in
    install) [[ $# -le 1 ]] || { codex_package_help >&2; exit 2; }; codex_package_install ;;
    help|--help|-h) codex_package_help ;;
    *) codex_package_help >&2; exit 2 ;;
esac
