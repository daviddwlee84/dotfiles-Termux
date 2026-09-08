#!/data/data/com.termux/files/usr/bin/bash
# Download this file and invoke `bash bootstrap.sh`; no desktop interpreter path.
set -euo pipefail
for argument in "$@"; do
    if [[ $argument == --help || $argument == -h ]]; then
        printf '%s\n' 'bash bootstrap.sh [setup|apply|update|packages|upgrade|doctor] [--non-interactive] [--dry-run]' \
            '  --install-ssh-server true|false --ssh-mode lan|adb --ssh-port 8022' \
            '  --install-termux-boot true|false --termux-wake-lock true|false' \
            '  --install-coding-agents true|false --with herdr,codex --authorized-key-file FILE' \
            'setup/packages/upgrade synchronize Termux packages; apply/update change configuration only.'
        exit 0
    fi
done
BASE=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
if [[ -f $BASE/scripts/manage.sh && -f $BASE/.chezmoiroot ]]; then
    exec bash "$BASE/scripts/manage.sh" "$@"
fi
for argument in "$@"; do
    case "$argument" in
        --help|-h) printf '%s\n' 'bash bootstrap.sh [--non-interactive] [--ssh-mode lan|adb] [--ssh-port PORT] [--with herdr,codex]'; exit 0 ;;
        --dry-run) printf '%s\n' 'Would validate native Termux, synchronize packages, and obtain dotfiles-Termux.'; exit 0 ;;
    esac
done
validate_arguments() {
    local value
    while (($#)); do
        case "$1" in
            setup|apply|update|packages|upgrade|doctor|--packages|--upgrade|--doctor|--config-only|--non-interactive) shift ;;
            --ssh-mode|--ssh-port|--install-ssh-server|--install-termux-boot|--termux-wake-lock|--install-coding-agents|--with|--authorized-key-file)
                [[ $# -ge 2 ]] || { echo "$1 requires a value" >&2; return 1; }
                value=$2
                case "$1" in
                    --ssh-mode) [[ $value == lan || $value == adb ]] || return 1 ;;
                    --ssh-port) [[ $value =~ ^[0-9]{1,5}$ ]] || return 1; ((10#$value >= 1024 && 10#$value <= 65535)) || return 1 ;;
                    --install-*|--termux-wake-lock) [[ $value == true || $value == false ]] || return 1 ;;
                    --with) [[ -z $value || $value =~ ^(herdr|codex)(,(herdr|codex))*$ ]] || return 1 ;;
                    --authorized-key-file) [[ -f $value && ! -L $value ]] || return 1 ;;
                esac
                shift 2 ;;
            *) echo "Unknown bootstrap argument: $1" >&2; return 1 ;;
        esac
    done
}
validate_arguments "$@"
PREFIX=${PREFIX:-/data/data/com.termux/files/usr}
if [[ -n ${DOTFILES_TEST_ROOT:-} ]]; then
    [[ ${DOTFILES_TEST_MODE:-} == fixture-only-v1 && $DOTFILES_TEST_ROOT == /* && $DOTFILES_TEST_ROOT != / && ! -L $DOTFILES_TEST_ROOT && -f $DOTFILES_TEST_ROOT/.fixture && ! -L $DOTFILES_TEST_ROOT/.fixture && $HOME == "$DOTFILES_TEST_ROOT/home" && $PREFIX == "$DOTFILES_TEST_ROOT/prefix" && ! -L $HOME && ! -L $PREFIX ]] || { echo 'Invalid isolated fixture' >&2; exit 1; }
else
    [[ $PREFIX == /data/data/com.termux/files/usr && $HOME == /data/data/com.termux/files/home && -x /system/bin/getprop && $(id -u) -ge 10000 && $(readlink "/proc/$$/exe") == "$PREFIX/bin/bash" && -z ${PROOT_TMP_DIR:-}${PROOT_LOADER:-}${PROOT_LOADER_32:-} ]] || { echo 'Run bootstrap inside native Termux Bash, not adb shell or PRoot.' >&2; exit 1; }
fi
export PREFIX
PATH="$PREFIX/bin:$PATH"
export PATH
DEST="$HOME/.local/share/dotfiles-Termux"
[[ ! -L $HOME/.local && ! -L $HOME/.local/share ]] || { echo 'Existing source-parent symlink preserved.' >&2; exit 1; }
[[ ! -L $DEST ]] || { echo 'Existing source symlink preserved.' >&2; exit 1; }
if [[ -e $DEST ]]; then
    [[ -d $DEST && -e $DEST/.git && -f $DEST/scripts/manage.sh ]] || { echo 'Unrecognized existing source preserved.' >&2; exit 1; }
    remote=$(git -C "$DEST" remote get-url origin)
    [[ $remote == https://github.com/daviddwlee84/dotfiles-Termux.git || $remote == git@github.com:daviddwlee84/dotfiles-Termux.git ]] || { echo 'Foreign source remote preserved.' >&2; exit 1; }
    exec bash "$DEST/scripts/manage.sh" "$@"
fi
for argument in "$@"; do
    case "$argument" in --config-only|apply|update|--doctor|doctor) echo 'No local source; run initial setup while online.' >&2; exit 1;; esac
done
config=${CHEZMOI_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/chezmoi/chezmoi.toml}
[[ ! -e $config && ! -L $config && ! -e $HOME/.local/share/chezmoi ]] || { echo 'Existing chezmoi state preserved; explicitly migrate it before bootstrapping this source.' >&2; exit 1; }
ref=${DOTFILES_REF:-main}
[[ $ref =~ ^[a-zA-Z0-9._-]+$ ]] || { echo 'DOTFILES_REF must be a simple ref.' >&2; exit 1; }
pkg update -y
pkg upgrade -y
pkg install -y git chezmoi
mkdir -p "$HOME/.local/share"
staged=$(mktemp -d "$HOME/.local/share/.dotfiles-Termux.XXXXXX")
trap 'rm -rf "$staged"' EXIT HUP INT TERM
git clone --origin origin -- https://github.com/daviddwlee84/dotfiles-Termux.git "$staged/source"
if [[ $ref != main ]]; then git -C "$staged/source" checkout --detach "$ref"; fi
[[ -f $staged/source/scripts/manage.sh && -f $staged/source/.chezmoiroot ]] || exit 1
mv "$staged/source" "$DEST"
bash "$DEST/scripts/manage.sh" "$@"
