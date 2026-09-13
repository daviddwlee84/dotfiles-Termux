#!/data/data/com.termux/files/usr/bin/bash
# Native optional tools. Run through Bash; never run Linux artifacts on the host.
set -euo pipefail
TOOLS_REPO=$(CDPATH='' cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
# shellcheck source=scripts/pair.sh
source "$TOOLS_REPO/scripts/pair.sh"

tool_help() {
    printf '%s\n' 'Usage: bash scripts/tools.sh install pi,herdr,codex,dev | doctor | probe herdr|codex|pi' \
        'Existing tools are preserved. Herdr/Codex/dev downloads are ARM64 native experiments.' \
        'Probes use isolated temporary state; full SSH/reconnect/auth acceptance remains separate.'
}

tool_record() {
    local tool=$1 status=$2
    termux_safe_dir "$TERMUX_STATE/tools"
    [[ ! -L $TERMUX_STATE/tools/$tool.status ]] || return 1
    printf '%s\n' "$status" >"$TERMUX_STATE/tools/$tool.status"
}

tool_install() (
    set -euo pipefail
    local tool=$1 arch row _name version url digest format member bytes destination temp
    if [[ $tool == codex ]]; then
        bash "$TOOLS_REPO/scripts/codex-package.sh" install
        return
    fi
    if command -v "$tool" >/dev/null 2>&1; then
        termux_say "$tool already installed; preserving $(command -v "$tool")"
        return 0
    fi
    arch=$(uname -m)
    row=$(awk -F '|' -v name="$tool" -v arch="$arch" '$1==name && ($2==arch || $2=="any") {print; exit}' "$TOOLS_REPO/config/assets.lock")
    if [[ -z $row ]]; then
        tool_record "$tool" "unsupported-architecture:$arch"
        termux_die "$tool has no locked native candidate for $arch; baseline remains usable"
        return 1
    fi
    IFS='|' read -r _name arch version url digest format member bytes <<<"$row"
    [[ $digest =~ ^[a-f0-9]{64}$ && $bytes =~ ^[0-9]+$ && $url == https://* ]] || { termux_die 'Invalid asset lock'; return 1; }
    termux_safe_dir "$HOME/.local/bin"
    destination="$HOME/.local/bin/$tool"
    [[ ! -e $destination && ! -L $destination ]] || { termux_die "Existing $destination preserved"; return 1; }
    temp=$(mktemp -d "$PREFIX/tmp/dotfiles-tool.XXXXXX")
    trap 'rm -rf "$temp"' EXIT
    curl --fail --location --proto '=https' --tlsv1.2 --retry 2 --connect-timeout 15 \
        --max-time 600 --output "$temp/download" "$url"
    [[ $(wc -c <"$temp/download" | tr -d ' ') == "$bytes" ]] || { termux_die "$tool size mismatch"; return 1; }
    printf '%s  %s\n' "$digest" "$temp/download" | sha256sum -c - >/dev/null || { termux_die "$tool SHA-256 mismatch"; return 1; }
    if [[ $format == npm ]]; then
        [[ $tool == pi ]] || return 1
        command -v npm >/dev/null || { termux_die 'Install native nodejs-lts and npm first'; return 1; }
        node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22 || (a===22 && b>=19) ? 0 : 1)' || { termux_die 'Pi needs Node >=22.19'; return 1; }
        # Pi upstream's Termux path intentionally omits optional native postinstall builds.
        cp "$temp/download" "$temp/pi-coding-agent-$version.tgz"
        npm install --global --ignore-scripts "$temp/pi-coding-agent-$version.tgz"
        timeout --kill-after=2 15 pi --version
    else
        case "$format" in
            raw) cp "$temp/download" "$temp/candidate" ;;
            tar.gz) tar -xOf "$temp/download" "$member" >"$temp/candidate" ;;
            *) termux_die 'Unknown asset format'; return 1 ;;
        esac
        [[ -s $temp/candidate ]] || return 1
        chmod 700 "$temp/candidate"
        if ! SHELL="$PREFIX/bin/bash" TMPDIR="$PREFIX/tmp" timeout --kill-after=2 10 "$temp/candidate" --version; then
            tool_record "$tool" "native-launch-failed:$version"
            termux_die "$tool could not start in this Android environment; see docs/tools.md"
            return 1
        fi
        # Atomic same-filesystem copy; no existing binary or running server is replaced.
        local staged
        staged=$(mktemp "$HOME/.local/bin/.$tool.XXXXXX")
        cp "$temp/candidate" "$staged" && chmod 755 "$staged"
        # Android app storage can deny hard links. GNU mv's no-clobber rename
        # preserves a destination created concurrently, including symlinks/dirs.
        if ! mv -nT "$staged" "$destination"; then rm -f "$staged"; return 1; fi
        # mv -n reports success when it skips an existing target; don't report
        # installation success unless our staged file was actually moved.
        if [[ -e $staged ]]; then
            rm -f "$staged"
            termux_die "Concurrent destination preserved: $destination"
            return 1
        fi
    fi
    tool_record "$tool" "launch-only:$version; interactive,network,PTY,sandbox acceptance pending"
    termux_say "$tool installed ($version); run the explicit probe and device acceptance guide"
)

tool_probe_codex() (
    set -euo pipefail
    local tool temp
    tool=$(command -v codex) || { termux_die 'Codex is missing'; return 1; }
    # Codex deliberately rejects helper aliases under the system temp directory.
    # Isolate its config under our private state, without loading account state.
    termux_safe_dir "$TERMUX_STATE/probes"
    temp=$(mktemp -d "$TERMUX_STATE/probes/codex.XXXXXX")
    trap 'rm -rf "$temp"' EXIT
    mkdir -p "$temp/config" "$temp/project"
    cd "$temp/project"
    # Empty app config uses Codex's normal restrictive sandbox. No bypass/profile
    # override: system-managed restrictions continue to apply.
    CODEX_HOME="$temp/config" timeout --kill-after=2 30 "$tool" sandbox -- \
        "$PREFIX/bin/bash" --noprofile --norc -c 'printf sandbox-command-ran' >"$temp/allow.log" 2>&1 || {
        cat "$temp/allow.log"; termux_die 'Codex sandbox could not execute a normal command'; return 1;
    }
    grep -q sandbox-command-ran "$temp/allow.log" || return 1
    CODEX_HOME="$temp/config" timeout --kill-after=2 30 "$tool" sandbox -- \
        "$PREFIX/bin/bash" --noprofile --norc -c \
        'if printf test > denied-write 2>/dev/null; then exit 1; else printf sandbox-denied-write; fi' \
        >"$temp/deny.log" 2>&1 || { cat "$temp/deny.log"; termux_die 'Codex write-denial check failed'; return 1; }
    if [[ -e denied-write ]] || ! grep -q sandbox-denied-write "$temp/deny.log"; then
        termux_die 'Sandbox did not enforce read-only writes'; return 1
    fi
    termux_say 'Codex local read-only sandbox probe passed; authentication/network/interactive checks remain pending.'
)

tool_probe_herdr() (
    set -euo pipefail
    local tool temp server_pid='' pane workspace _attempt
    tool=$(command -v herdr) || { termux_die 'Herdr is missing'; return 1; }
    # Short private path also avoids UNIX socket path-length limits on Android.
    temp=$(mktemp -d "$PREFIX/tmp/hp.XXXXXX")
    mkdir -p "$temp/home" "$temp/tmp" "$temp/runtime"
    export HOME="$temp/home" XDG_CONFIG_HOME="$temp/home/.config" TMPDIR="$temp/tmp"
    export XDG_STATE_HOME="$temp/state" XDG_DATA_HOME="$temp/data" XDG_CACHE_HOME="$temp/cache" XDG_RUNTIME_DIR="$temp/runtime"
    export SHELL="$PREFIX/bin/bash" HERDR_CONFIG_PATH="$temp/config.toml" HERDR_SOCKET_PATH="$temp/api.sock"
    unset HERDR_SESSION HERDR_ENV HERDR_PANE_ID HERDR_CLIENT_SOCKET_PATH HERDR_STARTUP_CWD BASH_ENV ENV
    cd "$temp/home"
    printf 'onboarding = false\n[terminal]\ndefault_shell = "%s"\nshell_mode = "non_login"\n' "$PREFIX/bin/bash" >"$HERDR_CONFIG_PATH"
    # shellcheck disable=SC2329,SC2317 # Invoked by EXIT trap (diagnostic varies by version).
    cleanup_herdr_probe() {
        timeout --kill-after=1 4 "$tool" server stop >/dev/null 2>&1 || true
        if [[ -n $server_pid ]]; then kill -TERM "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true; fi
        rm -rf "$temp"
    }
    trap cleanup_herdr_probe EXIT
    timeout --kill-after=2 45 "$tool" server >"$temp/server.log" 2>&1 &
    server_pid=$!
    for _attempt in {1..20}; do
        if timeout --kill-after=1 2 "$tool" pane list >"$temp/panes.json" 2>/dev/null; then break; fi
        sleep 0.25
    done
    # Fresh headless servers intentionally start with no workspaces or panes.
    if ! timeout --kill-after=1 10 "$tool" workspace create --cwd "$temp/home" \
        --label termux-probe --no-focus >"$temp/create.json" 2>"$temp/create.err"; then
        cat "$temp/create.json" "$temp/create.err" "$temp/server.log"
        termux_die 'Herdr workspace/PTY creation failed'; return 1
    fi
    pane=$(jq -er 'select(.result.type == "workspace_created") | .result.root_pane.pane_id | select(type == "string" and length > 0)' "$temp/create.json") || {
        cat "$temp/create.json" "$temp/create.err" "$temp/server.log"
        termux_die 'Herdr workspace result did not contain a pane'; return 1
    }
    workspace=$(jq -er '.result.workspace.workspace_id | select(type == "string" and length > 0)' "$temp/create.json") || return 1
    timeout --kill-after=1 5 "$tool" pane run "$pane" 'printf "termux-herdr-%s\n" "probe"' >/dev/null
    for _attempt in {1..20}; do
        timeout --kill-after=1 3 "$tool" pane read "$pane" --format text >"$temp/read.txt"
        grep -q termux-herdr-probe "$temp/read.txt" && break
        sleep 0.25
    done
    grep -q termux-herdr-probe "$temp/read.txt" || { termux_die 'Herdr shell command/output check failed'; return 1; }
    timeout --kill-after=1 5 "$tool" pane split "$pane" --direction right >/dev/null
    timeout --kill-after=1 5 "$tool" pane list --workspace "$workspace" | jq -e '.result.panes | length >= 2' >/dev/null
    termux_say 'Herdr headless PTY/run/read/split probe passed; interactive SSH/resize/reconnect checks remain pending.'
)

tool_main() {
    local action=${1:-help} tool failed=0 options
    case "$action" in help|--help|-h) tool_help; return ;; install|doctor|probe) ;; *) tool_help >&2; return 2;; esac
    termux_context
    case "$action" in
        install)
            options=${2:-}
            [[ -n $options && $options != ,* && $options != *, && $options != *,,* ]] || return 2
            local -a requested
            IFS=, read -r -a requested <<<"$options"
            for tool in "${requested[@]}"; do case "$tool" in pi|herdr|codex|dev) ;; *) termux_die "Unknown tool: $tool"; return 2;; esac; done
            for tool in "${requested[@]}"; do
                # A child Bash keeps errexit active even when the caller catches optional failures.
                if ! bash "$TOOLS_REPO/scripts/tools.sh" _install-one "$tool"; then failed=1; fi
            done
            return "$failed"
            ;;
        doctor)
            for tool in pi herdr codex dev; do
                if command -v "$tool" >/dev/null 2>&1; then
                    printf '%s: installed (%s); ' "$tool" "$(command -v "$tool")"
                    if [[ -r $TERMUX_STATE/tools/$tool.status ]]; then cat "$TERMUX_STATE/tools/$tool.status"; else printf 'unverified external installation\n'; fi
                else printf '%s: missing (optional)\n' "$tool"; fi
            done
            printf 'claude: native installer unavailable; see the PRoot/remote guide\n'
            ;;
        probe)
            case "${2:-}" in
                herdr) tool_probe_herdr ;;
                codex) tool_probe_codex ;;
                pi) timeout --kill-after=2 15 pi --version; termux_say 'Pi launch passed; login and scratch-project exercise remain manual.' ;;
                *) tool_help; return 2;;
            esac
            ;;
    esac
}

if [[ ${1:-} == _install-one ]]; then
    termux_context
    case ${2:-} in pi|herdr|codex|dev) tool_install "$2";; *) exit 2;; esac
else
    tool_main "$@"
fi
