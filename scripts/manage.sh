#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=scripts/pair.sh
source "$REPO/scripts/pair.sh"
termux_context
termux_defaults
CONFIG=${CHEZMOI_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/chezmoi/chezmoi.toml}

source_preflight() {
    local source_path default_source="$HOME/.local/share/chezmoi"
    [[ ! -L $CONFIG ]] || { termux_die 'Existing chezmoi config symlink preserved'; return 1; }
    if [[ -f $CONFIG ]]; then
        command -v chezmoi >/dev/null || { termux_die 'Existing chezmoi config requires chezmoi for safe source validation'; return 1; }
        source_path=$(chezmoi --config "$CONFIG" source-path) || return 1
        source_path=$(CDPATH='' cd -- "$source_path" && pwd -P) || return 1
        [[ $source_path == "$REPO" || $source_path == "$REPO/home" ]] || { termux_die "Existing chezmoi source preserved: $source_path"; return 1; }
    elif [[ -e $default_source && $default_source != "$REPO" ]]; then
        [[ -d $default_source && ! -L $default_source && -z $(ls -A "$default_source") ]] || { termux_die 'Existing default chezmoi source preserved'; return 1; }
    fi
}

load_chezmoi_choices() {
    [[ -f $CONFIG ]] || return 0
    local choices
    choices=$(chezmoi --config "$CONFIG" execute-template '{{ if hasKey . "installSshServer" }}installSshServer={{ .installSshServer }}
sshMode={{ .sshMode }}
sshPort={{ .sshPort }}
installTermuxBoot={{ .installTermuxBoot }}
termuxWakeLock={{ .termuxWakeLock }}
installCodingAgents={{ .installCodingAgents }}
optionalTools={{ .optionalTools }}
{{ end }}') || return 1
    termux_read_settings <<<"$choices"
}

source_preflight
load_chezmoi_choices
ACTION=setup DRY_RUN=false KEY_FILE='' CHOICES_CHANGED=false
while (($#)); do
    case "$1" in
        setup|apply|update|pull|packages|upgrade|doctor) ACTION=$1; shift ;;
        --packages) ACTION=packages; shift ;;
        --upgrade) ACTION=upgrade; shift ;;
        --doctor) ACTION=doctor; shift ;;
        --config-only) ACTION=apply; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --non-interactive) shift ;;
        --help|-h)
            printf '%s\n' 'bootstrap.sh [setup|apply|update|packages|upgrade|doctor] [--non-interactive] [--dry-run]' \
                '  --install-ssh-server true|false --ssh-mode lan|adb --ssh-port 8022' \
                '  --install-termux-boot true|false --termux-wake-lock true|false' \
                '  --install-coding-agents true|false --with herdr,codex --authorized-key-file FILE' \
                'setup/packages/upgrade synchronize all Termux packages; apply/update change configuration only.'
            exit 0 ;;
        --authorized-key-file|--ssh-mode|--ssh-port|--install-ssh-server|--install-termux-boot|--termux-wake-lock|--install-coding-agents|--with)
            [[ $# -ge 2 ]] || { termux_die "$1 needs a value"; exit 1; }
            case "$1" in
                --authorized-key-file) KEY_FILE=$2 ;;
                --ssh-mode) SSH_MODE=$2 ;;
                --ssh-port) SSH_PORT=$2 ;;
                --install-ssh-server) INSTALL_SSH=$2 ;;
                --install-termux-boot) INSTALL_BOOT=$2 ;;
                --termux-wake-lock) WAKE_LOCK=$2 ;;
                --install-coding-agents) INSTALL_AGENTS=$2 ;;
                --with) OPTIONAL_TOOLS=$2 ;;
            esac
            [[ $1 == --authorized-key-file ]] || CHOICES_CHANGED=true
            shift 2 ;;
        *) termux_die "Unknown argument: $1"; exit 1 ;;
    esac
done
termux_validate_settings

if [[ $DRY_RUN == true ]]; then
    termux_say "Dry run: $ACTION; source=$REPO"
    termux_print_settings
    [[ $ACTION != setup && $ACTION != packages && $ACTION != upgrade ]] || cat "$REPO/config/packages-base.txt"
    exit 0
fi

pull_source() {
    [[ -e $REPO/.git && ! -L $REPO/.git ]] || { termux_die 'Source is not a Git checkout; run bootstrap once'; return 1; }
    git -C "$REPO" symbolic-ref -q HEAD >/dev/null || { termux_die 'Pinned/detached source: select a tracking branch before updating'; return 1; }
    [[ -z $(git -C "$REPO" status --porcelain) ]] || { termux_die 'Source has local changes; preserve and resolve them before updating'; return 1; }
    git -C "$REPO" pull --ff-only
}

install_packages() {
    local package selected_tools=$OPTIONAL_TOOLS
    local -a packages=()
    while IFS= read -r package; do
        [[ -z $package || $package == \#* ]] || packages+=("$package")
    done <"$REPO/config/packages-base.txt"
    if [[ $INSTALL_AGENTS == true ]]; then
        while IFS= read -r package; do
            [[ -z $package || $package == \#* ]] || packages+=("$package")
        done <"$REPO/config/packages-agents.txt"
        selected_tools="pi${selected_tools:+,$selected_tools}"
    fi
    pkg update -y || return 1
    pkg upgrade -y || return 1
    pkg install -y "${packages[@]}" || return 1
    ssh-keygen -A || return 1
    BASELINE_READY=true
    if [[ -n $selected_tools ]]; then bash "$REPO/scripts/tools.sh" install "$selected_tools"; fi
}

initialize_config() {
    source_preflight
    local backup=''
    if [[ -f $CONFIG ]]; then
        termux_safe_dir "$TERMUX_STATE" || return 1
        backup=$(mktemp "$TERMUX_STATE/chezmoi.before-init.XXXXXX")
        cp "$CONFIG" "$backup" && chmod 600 "$backup"
    fi
    # All bootstrap paths write the same chezmoi data. Direct `chezmoi init`
    # uses the native prompts instead; its newly saved data wins on apply.
    export DOTFILES_INIT_SSH=$INSTALL_SSH DOTFILES_INIT_MODE=$SSH_MODE DOTFILES_INIT_PORT=$SSH_PORT
    export DOTFILES_INIT_BOOT=$INSTALL_BOOT DOTFILES_INIT_WAKE=$WAKE_LOCK DOTFILES_INIT_AGENTS=$INSTALL_AGENTS
    export DOTFILES_INIT_TOOLS=$OPTIONAL_TOOLS DOTFILES_INIT_FROM_BOOTSTRAP=true
    if ! chezmoi --config "$CONFIG" --source "$REPO" --destination "$HOME" init; then
        [[ -z $backup ]] || cp "$backup" "$CONFIG"
        return 1
    fi
    unset DOTFILES_INIT_SSH DOTFILES_INIT_MODE DOTFILES_INIT_PORT DOTFILES_INIT_BOOT
    unset DOTFILES_INIT_WAKE DOTFILES_INIT_AGENTS DOTFILES_INIT_TOOLS DOTFILES_INIT_FROM_BOOTSTRAP
    CHOICES_CHANGED=false
}

apply_configuration() {
    if [[ ! -f $CONFIG || $CHOICES_CHANGED == true ]]; then initialize_config; fi
    [[ -z $KEY_FILE ]] || termux_authorize_key "$KEY_FILE"
    chezmoi --config "$CONFIG" --source "$REPO" --destination "$HOME" apply
}

case "$ACTION" in
    doctor)
        termux_say "Native Termux prefix=$PREFIX source=$REPO"
        termux_print_settings
        bash "$REPO/scripts/ssh.sh" doctor
        [[ ! -f $REPO/scripts/tools.sh ]] || bash "$REPO/scripts/tools.sh" doctor ;;
    pull) pull_source ;;
    update) pull_source; apply_configuration ;;
    apply) apply_configuration ;;
    setup|packages|upgrade)
        # Baseline package failure stops before home deployment. Optional tool
        # failure is reported after preserving a configured baseline.
        optional_status=0 BASELINE_READY=false
        install_packages || optional_status=$?
        if ((optional_status != 0)); then
            [[ $BASELINE_READY == true ]] || exit "$optional_status"
            termux_say 'An installation stage failed; preserving its status after baseline configuration.'
        fi
        initialize_config
        termux_save_settings
        apply_configuration
        termux_say 'Ready. Daily commands: chezmoi diff, chezmoi apply, chezmoi update.'
        exit "$optional_status" ;;
esac
