#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=scripts/pair.sh
source "$REPO/scripts/pair.sh"
termux_context
if (($#)); then
    [[ $# == 7 ]] || exit 1
    INSTALL_SSH=$1 SSH_MODE=$2 SSH_PORT=$3 INSTALL_BOOT=$4 WAKE_LOCK=$5 INSTALL_AGENTS=$6 OPTIONAL_TOOLS=$7
    termux_validate_settings
fi
