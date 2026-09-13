#!/data/data/com.termux/files/usr/bin/bash
# Self-contained first pairing payload; also the common target/SSH library.
# Source this file without executing pairing: source scripts/pair.sh.

termux_die() { printf '[termux] %s\n' "$*" >&2; return 1; }
termux_say() { printf '[termux] %s\n' "$*"; }

termux_context() {
    PREFIX=${PREFIX:-/data/data/com.termux/files/usr}
    TERMUX_TEST_ROOT=''
    if [[ -n ${DOTFILES_TEST_ROOT:-} ]]; then
        [[ ${DOTFILES_TEST_MODE:-} == fixture-only-v1 ]] || { termux_die 'Invalid fixture mode'; return 1; }
        [[ $DOTFILES_TEST_ROOT == /* && $DOTFILES_TEST_ROOT != / && ! -L $DOTFILES_TEST_ROOT && -f $DOTFILES_TEST_ROOT/.fixture && ! -L $DOTFILES_TEST_ROOT/.fixture ]] || { termux_die 'Invalid fixture root'; return 1; }
        [[ $HOME == "$DOTFILES_TEST_ROOT/home" && $PREFIX == "$DOTFILES_TEST_ROOT/prefix" ]] || { termux_die 'Fixture HOME/PREFIX must be isolated'; return 1; }
        [[ ! -L $HOME && ! -L $PREFIX ]] || { termux_die 'Fixture HOME/PREFIX symlinks are forbidden'; return 1; }
        TERMUX_TEST_ROOT=$DOTFILES_TEST_ROOT
    else
        [[ $PREFIX == /data/data/com.termux/files/usr && $HOME == /data/data/com.termux/files/home ]] || { termux_die 'Run inside the native com.termux app, not adb shell, desktop Linux or PRoot'; return 1; }
        [[ $(uname -s) == Linux && $(id -u) -ge 10000 && -x /system/bin/getprop ]] || { termux_die 'Native unprivileged Android/Termux is required'; return 1; }
        [[ -z ${PROOT_TMP_DIR:-}${PROOT_LOADER:-}${PROOT_LOADER_32:-} ]] || { termux_die 'PRoot is not supported'; return 1; }
        [[ -x $PREFIX/bin/pkg && -x $PREFIX/bin/bash && -x $PREFIX/bin/termux-info ]] || { termux_die 'Native Termux packages are missing'; return 1; }
        [[ $(readlink "/proc/$$/exe") == "$PREFIX/bin/bash" ]] || { termux_die 'Use the native Termux Bash interpreter'; return 1; }
    fi
    [[ -d $HOME && -d $PREFIX && -x $PREFIX/bin/bash ]] || { termux_die 'Missing HOME/PREFIX/Bash'; return 1; }
    TERMUX_STATE="$HOME/.local/state/dotfiles-termux"
    TERMUX_CONFIG="$HOME/.config/dotfiles-termux"
    export PREFIX TERMUX_STATE TERMUX_CONFIG TERMUX_TEST_ROOT
    PATH="$PREFIX/bin:$HOME/.local/bin:$PATH"
    export PATH
}

termux_safe_dir() {
    local path=$1 remainder component current=$HOME
    [[ $path == "$HOME"/* ]] || { termux_die 'Runtime directory must be under HOME'; return 1; }
    remainder=${path#"$HOME"/}
    while [[ -n $remainder ]]; do
        component=${remainder%%/*}
        [[ -n $component && $component != . && $component != .. ]] || return 1
        current="$current/$component"
        [[ ! -L $current && ( ! -e $current || -d $current ) ]] || { termux_die "Preserving unsafe runtime path: $current"; return 1; }
        [[ $remainder == */* ]] || break
        remainder=${remainder#*/}
    done
    mkdir -p "$path"
}

termux_read_settings() {
    local key value
    while IFS='=' read -r key value; do
        case "$key" in
            ''|'#'*) ;;
            installSshServer) INSTALL_SSH=$value ;;
            sshMode) SSH_MODE=$value ;;
            sshPort) SSH_PORT=$value ;;
            installTermuxBoot) INSTALL_BOOT=$value ;;
            termuxWakeLock) WAKE_LOCK=$value ;;
            installCodingAgents) INSTALL_AGENTS=$value ;;
            optionalTools) OPTIONAL_TOOLS=$value ;;
            *) termux_die "Unknown saved setting: $key"; return 1 ;;
        esac
    done
}

termux_defaults() {
    INSTALL_SSH=true SSH_MODE=lan SSH_PORT=8022 INSTALL_BOOT=true
    WAKE_LOCK=false INSTALL_AGENTS=true OPTIONAL_TOOLS=''
    local path
    for path in "$TERMUX_STATE/settings" "$TERMUX_CONFIG/settings"; do
        [[ ! -L $path ]] || { termux_die "Settings symlink preserved: $path"; return 1; }
        [[ ! -f $path ]] || termux_read_settings <"$path" || return 1
    done
}

termux_validate_settings() {
    local value option
    for value in "$INSTALL_SSH" "$INSTALL_BOOT" "$WAKE_LOCK" "$INSTALL_AGENTS"; do
        [[ $value == true || $value == false ]] || { termux_die 'Boolean choices must be true or false'; return 1; }
    done
    [[ $SSH_MODE == lan || $SSH_MODE == adb ]] || { termux_die 'SSH mode must be lan or adb'; return 1; }
    if [[ ! $SSH_PORT =~ ^[0-9]{1,5}$ ]] || ((10#$SSH_PORT < 1024 || 10#$SSH_PORT > 65535)); then
        termux_die 'SSH port must be 1024..65535'; return 1
    fi
    SSH_PORT=$((10#$SSH_PORT))
    [[ $OPTIONAL_TOOLS != *, && $OPTIONAL_TOOLS != ,* && $OPTIONAL_TOOLS != *,,* ]] || { termux_die 'Invalid optional tool list'; return 1; }
    local old_ifs=$IFS
    IFS=,
    for option in $OPTIONAL_TOOLS; do
        case "$option" in herdr|codex|dev) ;; *) IFS=$old_ifs; termux_die "Unknown optional tool: $option"; return 1;; esac
    done
    IFS=$old_ifs
}

termux_print_settings() {
    printf '%s\n' "installSshServer=$INSTALL_SSH" "sshMode=$SSH_MODE" "sshPort=$SSH_PORT" \
        "installTermuxBoot=$INSTALL_BOOT" "termuxWakeLock=$WAKE_LOCK" \
        "installCodingAgents=$INSTALL_AGENTS" "optionalTools=$OPTIONAL_TOOLS"
}

termux_save_settings() {
    termux_safe_dir "$TERMUX_STATE" || return 1
    [[ ! -L $TERMUX_STATE/settings ]] || return 1
    local staged
    staged=$(mktemp "$TERMUX_STATE/.settings.XXXXXX") || return 1
    termux_print_settings >"$staged"
    chmod 600 "$staged" && mv "$staged" "$TERMUX_STATE/settings"
}

termux_authorize_key() {
    local source=$1 key_type key_blob remainder staged
    [[ -f $source && ! -L $source ]] || { termux_die 'Public key must be a regular file'; return 1; }
    [[ $(awk 'NF {n++} END {print n+0}' "$source") == 1 ]] || { termux_die 'Supply exactly one public key'; return 1; }
    read -r key_type key_blob remainder <"$source" || [[ -n ${key_blob:-} ]]
    case "$key_type" in ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) ;; *) termux_die 'Supply a public key file, never a private key or authorized_keys options'; return 1;; esac
    if [[ ! $key_blob =~ ^[A-Za-z0-9+/=]+$ ]] || ! ssh-keygen -lf "$source" >/dev/null 2>&1; then
        termux_die 'Invalid public key'; return 1
    fi
    termux_safe_dir "$HOME/.ssh" || return 1
    [[ ! -L $HOME/.ssh/authorized_keys && ( ! -e $HOME/.ssh/authorized_keys || -f $HOME/.ssh/authorized_keys ) ]] || { termux_die 'Existing authorized_keys path preserved'; return 1; }
    chmod 700 "$HOME/.ssh"
    [[ -f $HOME/.ssh/authorized_keys ]] || (umask 077; : >"$HOME/.ssh/authorized_keys")
    # A restricted existing occurrence counts too; never add an unrestricted duplicate.
    if awk -v type="$key_type" -v blob="$key_blob" '{for(i=1;i<NF;i++) if($i==type && $(i+1)==blob) found=1} END {exit !found}' "$HOME/.ssh/authorized_keys"; then
        return 0
    fi
    staged=$(mktemp "$HOME/.ssh/.authorized_keys.XXXXXX") || return 1
    cat "$HOME/.ssh/authorized_keys" >"$staged"
    printf '\n%s %s\n' "$key_type" "$key_blob" >>"$staged"
    chmod 600 "$staged" && mv "$staged" "$HOME/.ssh/authorized_keys"
}

termux_has_key() {
    [[ -f $HOME/.ssh/authorized_keys && ! -L $HOME/.ssh/authorized_keys ]] &&
        ssh-keygen -lf "$HOME/.ssh/authorized_keys" >/dev/null 2>&1
}

termux_write_owned() {
    local destination=$1 snapshot=$2 candidate=$3
    [[ ! -L $destination && ! -L $snapshot && ( ! -e $snapshot || -f $snapshot ) ]] || { termux_die 'Owned-file symlink or non-file preserved'; return 1; }
    if [[ -e $destination ]] && ! cmp -s "$destination" "$candidate"; then
        if [[ ! -f $snapshot ]] || ! cmp -s "$destination" "$snapshot"; then
            termux_die "Local edit preserved: $destination"; return 1
        fi
    fi
    chmod 600 "$candidate" && mv "$candidate" "$destination" && cp "$destination" "$snapshot"
}

termux_ssh_configure() {
    termux_safe_dir "$TERMUX_CONFIG" && termux_safe_dir "$TERMUX_STATE" || return 1
    local staged address
    staged=$(mktemp "$TERMUX_CONFIG/.sshd_config.XXXXXX") || return 1
    if [[ $SSH_MODE == lan ]]; then address=0.0.0.0; else address=127.0.0.1; fi
    # Deliberately one IPv4 listener: ADB forwarding and LAN address reporting agree.
    cat >"$staged" <<EOF
# Managed by dotfiles-Termux; unrelated package sshd_config is untouched.
Port $SSH_PORT
AddressFamily inet
ListenAddress $address
HostKey $PREFIX/etc/ssh/ssh_host_ed25519_key
PidFile $TERMUX_STATE/sshd.pid
AuthorizedKeysFile $HOME/.ssh/authorized_keys
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
PrintMotd no
Subsystem sftp $PREFIX/libexec/sftp-server
EOF
    if ! sshd -t -f "$staged"; then rm -f "$staged"; termux_die 'sshd configuration validation failed'; return 1; fi
    termux_write_owned "$TERMUX_CONFIG/sshd_config" "$TERMUX_STATE/sshd_config.last" "$staged" || { rm -f "$staged"; return 1; }
}

termux_ssh_pid() {
    local pid command_line executable proc_root=${TERMUX_TEST_ROOT:-}
    [[ -f $TERMUX_STATE/sshd.pid && ! -L $TERMUX_STATE/sshd.pid ]] || return 1
    read -r pid <"$TERMUX_STATE/sshd.pid"
    [[ $pid =~ ^[0-9]+$ && $pid -gt 1 ]] && kill -0 "$pid" 2>/dev/null || return 1
    command_line=$(tr '\0' ' ' <"$proc_root/proc/$pid/cmdline" 2>/dev/null) || return 1
    executable=$(readlink "$proc_root/proc/$pid/exe") || return 1
    [[ $executable == "$PREFIX/bin/sshd" ]] || return 1
    [[ $command_line == *"$PREFIX/bin/sshd"* && $command_line == *"-f $TERMUX_CONFIG/sshd_config"* ]] || return 1
    printf '%s\n' "$pid"
}

termux_port_busy() {
    # shellcheck disable=SC2016
    timeout 2 "$PREFIX/bin/bash" -c 'exec 3<>/dev/tcp/127.0.0.1/"$1"' _ "$SSH_PORT" >/dev/null 2>&1
}

termux_ssh_stop() {
    local pid
    if pid=$(termux_ssh_pid); then
        kill -TERM "$pid" || return 1
        termux_say 'Stopped the managed SSH listener; existing sessions remain separate.'
    elif [[ -f $TERMUX_STATE/sshd.pid ]]; then
        termux_say 'No owned SSH master found; no process was stopped.'
    fi
}

termux_ssh_start() {
    local pid previous_port _attempt existing_pid
    if [[ $INSTALL_SSH != true ]]; then termux_ssh_stop; termux_say 'SSH disabled'; return 0; fi
    if ! termux_has_key; then termux_ssh_stop; termux_say 'SSH pending-key: add a host public key with termux-ssh authorize FILE'; return 0; fi
    [[ ! -L $TERMUX_STATE/sshd_config.running && ( ! -e $TERMUX_STATE/sshd_config.running || -f $TERMUX_STATE/sshd_config.running ) ]] || { termux_die 'Existing running-config path preserved'; return 1; }
    sshd -t -f "$TERMUX_CONFIG/sshd_config" || return 1
    if pid=$(termux_ssh_pid); then
        if ! cmp -s "$TERMUX_CONFIG/sshd_config" "$TERMUX_STATE/sshd_config.running"; then
            previous_port=$(awk '$1=="Port" {print $2; exit}' "$TERMUX_STATE/sshd_config.running" 2>/dev/null || true)
            if [[ $previous_port != "$SSH_PORT" ]] && termux_port_busy; then
                termux_die "Requested port $SSH_PORT is occupied; existing managed listener was preserved"; return 1
            fi
            kill -HUP "$pid" || return 1
            for _attempt in 1 2 3 4 5; do
                if termux_port_busy && termux_ssh_pid >/dev/null; then break; fi
                sleep 0.2
            done
            if ! termux_port_busy || ! termux_ssh_pid >/dev/null; then
                termux_die 'Managed SSH reload did not become ready; inspect private sshd.log'; return 1
            fi
            cp "$TERMUX_CONFIG/sshd_config" "$TERMUX_STATE/sshd_config.running" || return 1
            termux_say 'Reloaded the managed SSH listener.'
        fi
        return 0
    fi
    if [[ -f $TERMUX_STATE/sshd.pid ]]; then
        read -r existing_pid <"$TERMUX_STATE/sshd.pid"
        if [[ $existing_pid =~ ^[0-9]+$ && $existing_pid -gt 1 ]] && kill -0 "$existing_pid" 2>/dev/null; then
            termux_die 'Existing PID belongs to an unrecognized process; preserving it'; return 1
        fi
    fi
    if termux_port_busy; then termux_die "Port $SSH_PORT is already occupied; preserve that listener or choose --ssh-port"; return 1; fi
    [[ ! -L $TERMUX_STATE/sshd.pid && ! -L $TERMUX_STATE/sshd.log ]] || return 1
    "$PREFIX/bin/sshd" -f "$TERMUX_CONFIG/sshd_config" -E "$TERMUX_STATE/sshd.log" || { termux_die 'Managed sshd failed; inspect the private sshd.log'; return 1; }
    for _attempt in 1 2 3 4 5; do
        if termux_port_busy && termux_ssh_pid >/dev/null; then break; fi
        sleep 0.2
    done
    if ! termux_port_busy || ! termux_ssh_pid >/dev/null; then
        termux_die 'Managed SSH did not become ready; inspect private sshd.log'; return 1
    fi
    cp "$TERMUX_CONFIG/sshd_config" "$TERMUX_STATE/sshd_config.running"
    termux_say "SSH listening in $SSH_MODE mode on port $SSH_PORT (public key only)."
}

termux_pair_callback() {
    local status=$1 user host_key json
    [[ -n ${PAIR_CALLBACK:-} ]] || return 0
    if [[ $status == ready ]]; then
        user=$(id -un)
        host_key=$(awk 'NR==1 {print $1 " " $2}' "$PREFIX/etc/ssh/ssh_host_ed25519_key.pub")
        [[ $user =~ ^[a-zA-Z0-9_-]+$ && $host_key =~ ^ssh-ed25519\ [A-Za-z0-9+/=]+$ ]] || return 1
        printf -v json '{"status":"ready","user":"%s","ssh_port":%s,"host_key":"%s"}' "$user" "$SSH_PORT" "$host_key"
    else json='{"status":"error","message":"pairing failed; inspect the Termux terminal"}'; fi
    curl -fsS --connect-timeout 5 --max-time 20 -H 'Content-Type: application/json' --data-binary "$json" "$PAIR_CALLBACK" >/dev/null
}

termux_pair_main() {
    set -Eeuo pipefail
    termux_context
    termux_defaults
    local key_file=''
    PAIR_CALLBACK=''
    while (($#)); do
        [[ $# -ge 2 ]] || { termux_die 'Pairing options require values'; return 1; }
        case "$1" in
            --authorized-key-file) key_file=$2 ;;
            --ssh-mode) SSH_MODE=$2 ;;
            --ssh-port) SSH_PORT=$2 ;;
            --callback-url) PAIR_CALLBACK=$2 ;;
            *) termux_die "Unknown pairing flag: $1"; return 1 ;;
        esac
        shift 2
    done
    [[ -z $PAIR_CALLBACK || $PAIR_CALLBACK =~ ^http://(127\.0\.0\.1|localhost):[0-9]+/[a-zA-Z0-9/_-]+$ ]] || { termux_die 'Pairing callback must use the local ADB reverse tunnel'; return 1; }
    trap 'termux_pair_callback error || true' ERR
    termux_validate_settings
    [[ -n $key_file ]] || { termux_die 'Pairing requires --authorized-key-file'; return 1; }
    pkg update -y
    pkg upgrade -y
    pkg install -y openssh curl
    ssh-keygen -A
    termux_authorize_key "$key_file"
    INSTALL_SSH=true
    termux_save_settings
    termux_ssh_configure
    termux_ssh_start
    termux_pair_callback ready
    trap - ERR
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then termux_pair_main "$@"; fi
