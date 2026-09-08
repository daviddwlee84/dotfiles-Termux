#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=scripts/pair.sh
source "$REPO/scripts/pair.sh"
termux_context
termux_defaults
termux_validate_settings
ACTION=${1:-doctor}
case "$ACTION" in
    authorize)
        [[ $# == 2 ]] || { termux_die 'Usage: termux-ssh authorize PUBLIC_KEY_FILE'; exit 1; }
        termux_authorize_key "$2"
        termux_ssh_configure
        termux_ssh_start ;;
    configure|start)
        if [[ $INSTALL_SSH != true ]]; then termux_ssh_stop; exit 0; fi
        command -v sshd >/dev/null || { termux_say 'SSH pending-package: run just packages'; exit 0; }
        termux_ssh_configure
        termux_ssh_start ;;
    boot)
        [[ $INSTALL_BOOT == true && $INSTALL_SSH == true ]] || exit 0
        [[ $WAKE_LOCK != true ]] || termux-wake-lock
        command -v sshd >/dev/null || { termux_say 'SSH pending-package'; exit 0; }
        termux_ssh_configure
        termux_ssh_start ;;
    stop) termux_ssh_stop ;;
    doctor|status)
        if [[ $INSTALL_SSH != true ]]; then termux_say 'SSH disabled'
        elif ! command -v sshd >/dev/null; then termux_say 'SSH pending-package'
        elif ! termux_has_key; then termux_say 'SSH pending-key'
        elif pid=$(termux_ssh_pid); then termux_say "SSH managed master=$pid mode=$SSH_MODE port=$SSH_PORT"
        elif termux_port_busy; then termux_say "SSH port-conflict=$SSH_PORT (foreign listener preserved)"
        else termux_say 'SSH configured/stopped'; fi
        if [[ $INSTALL_BOOT == true ]]; then
            if [[ -f $HOME/.termux/boot/50-dotfiles-termux ]]; then
                termux_say 'Boot hook configured; install matching Termux:Boot and open its icon once.'
            else termux_say 'Boot pending-hook: run chezmoi apply'; fi
        else termux_say 'Boot disabled'; fi
        termux_say "Boot wake-lock=$WAKE_LOCK" ;;
    *) termux_die 'Usage: termux-ssh configure|start|stop|status|doctor|boot|authorize PUBLIC_KEY_FILE'; exit 1 ;;
esac
