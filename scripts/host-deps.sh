#!/bin/sh
# Bootstrap the uv-based host helper without requiring uv, Python or just first.
set -eu

install=false
usb_rules=false
for argument in "$@"; do
    case "$argument" in
        --install) install=true ;;
        --usb-rules) usb_rules=true ;;
        -h|--help)
            echo 'Usage: sh scripts/host-deps.sh [--install] [--usb-rules]'
            echo 'Checks host dependencies; --install installs them. --usb-rules explicitly repairs Debian/Ubuntu USB access.'
            exit 0 ;;
        *) echo "Unknown option: $argument" >&2; exit 2 ;;
    esac
done

system=$(uname -s)
case "$system" in
    Darwin|Linux) ;;
    *) echo 'Host setup currently supports macOS and Linux.' >&2; exit 1 ;;
esac

if "$install"; then
    case "$system" in
        Darwin)
            if ! command -v brew >/dev/null 2>&1; then
                echo 'Install Homebrew from https://brew.sh, then rerun this helper.' >&2
                exit 1
            fi
            command -v uv >/dev/null 2>&1 || brew install uv
            command -v adb >/dev/null 2>&1 || brew install --cask android-platform-tools
            ;;
        Linux)
            if ! command -v apt-get >/dev/null 2>&1; then
                echo 'Automatic Linux installation currently supports Debian/Ubuntu apt.' >&2
                echo 'Install native adb, openssh-client, openssl, curl, and uv with your distribution package manager.' >&2
                exit 1
            fi
            # Explicit --install authorizes native packages, never a root adb server.
            sudo apt-get update
            sudo apt-get install -y adb openssh-client openssl curl ca-certificates
            if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
                uv_installer=$(mktemp)
                trap 'rm -f "$uv_installer"' EXIT HUP INT TERM
                # Audited official versioned installer; its own release manifest
                # selects and verifies the native uv archive.
                curl -fLsS https://astral.sh/uv/0.11.13/install.sh -o "$uv_installer"
                [ "$(wc -c < "$uv_installer" | tr -d ' ')" = 71233 ] || { echo 'uv installer size mismatch' >&2; exit 1; }
                echo "48cd5aca5d5671a3b3d5f61538cc8622e4434af63319115159990d8b0dd02416  $uv_installer" | sha256sum -c -
                UV_NO_MODIFY_PATH=1 sh "$uv_installer"
                rm -f "$uv_installer"
                trap - EXIT HUP INT TERM
            fi
            ;;
    esac
fi

if "$usb_rules"; then
    if [ "$system" != Linux ] || ! command -v apt-get >/dev/null 2>&1; then
        echo '--usb-rules currently supports Debian/Ubuntu only.' >&2
        exit 1
    fi
    sudo apt-get install -y android-sdk-platform-tools-common
    if ! id -nG | tr ' ' '\n' | grep -qx plugdev; then
        sudo usermod -aG plugdev "$(id -un)"
        echo 'Log out and back in to activate plugdev membership, then reconnect the USB device.'
    fi
fi

missing=false
for program in adb ssh ssh-keygen openssl curl; do
    if command -v "$program" >/dev/null 2>&1; then
        echo "$program: $(command -v "$program")"
    else
        echo "$program: missing" >&2
        missing=true
    fi
done
if command -v uv >/dev/null 2>&1; then
    echo "uv: $(command -v uv)"
elif [ -x "$HOME/.local/bin/uv" ]; then
    echo "uv: $HOME/.local/bin/uv (add $HOME/.local/bin to PATH or invoke this absolute path)"
else
    echo 'uv: missing' >&2
    missing=true
fi
if "$missing"; then
    echo 'Run sh scripts/host-deps.sh --install to install supported dependencies.' >&2
    exit 1
fi
echo 'Host dependencies ready. Enable USB debugging, connect/unlock Android, and accept its authorization prompt.'
