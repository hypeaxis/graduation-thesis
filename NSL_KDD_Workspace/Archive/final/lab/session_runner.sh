#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_ROOT="$SCRIPT_DIR/sessions"

source "$SCRIPT_DIR/scenarios.sh"

SCENARIO="icmp_echo"
TARGET_HOST="127.0.0.1"
ITERATIONS=12
INTERFACE="lo"
CAPTURE_FILTER=""
PRE_SECONDS=2
POST_SECONDS=2
NO_CAPTURE=0
SESSION_TAG=""

usage() {
    cat <<'EOF'
Usage:
  bash final/lab/session_runner.sh [options]

Options:
  --scenario <name>           Scenario name (default: icmp_echo)
  --target-host <ip-or-host>  Target host for traffic generation (default: 127.0.0.1)
  --iterations <n>            Number of packets/attempts (default: 12)
  --interface <ifname>        Capture interface (default: lo)
  --filter <bpf>              tcpdump BPF filter (default: none)
  --pre-seconds <n>           Seconds to wait before scenario starts (default: 2)
  --post-seconds <n>          Seconds to keep capture after scenario (default: 2)
  --session-tag <text>        Optional tag appended to session id
  --no-capture                Skip tcpdump capture (metadata only)
  -h, --help                  Show help

Supported scenarios:
  benign_baseline
  icmp_echo
  tcp_connect_burst
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --scenario)
            SCENARIO="$2"
            shift 2
            ;;
        --target-host)
            TARGET_HOST="$2"
            shift 2
            ;;
        --iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        --interface)
            INTERFACE="$2"
            shift 2
            ;;
        --filter)
            CAPTURE_FILTER="$2"
            shift 2
            ;;
        --pre-seconds)
            PRE_SECONDS="$2"
            shift 2
            ;;
        --post-seconds)
            POST_SECONDS="$2"
            shift 2
            ;;
        --session-tag)
            SESSION_TAG="$2"
            shift 2
            ;;
        --no-capture)
            NO_CAPTURE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

RUN_TS="$(date -u +%Y%m%d_%H%M%S)"
if [[ -n "$SESSION_TAG" ]]; then
    SESSION_ID="${RUN_TS}_${SCENARIO}_${SESSION_TAG}"
else
    SESSION_ID="${RUN_TS}_${SCENARIO}"
fi

SESSION_DIR="$OUTPUT_ROOT/$SESSION_ID"
mkdir -p "$SESSION_DIR"
PCAP_PATH="$SESSION_DIR/${SESSION_ID}.pcap"
META_PATH="$SESSION_DIR/${SESSION_ID}.metadata.json"

CAPTURE_STARTED=0
CAP_PID=""

cleanup_capture() {
    if [[ "$CAPTURE_STARTED" -eq 1 && -n "$CAP_PID" ]]; then
        # Stop tcpdump by matching this exact output file path to avoid hanging on sudo wrapper wait.
        if [[ "$EUID" -eq 0 ]]; then
            pkill -INT -f "tcpdump .* -w ${PCAP_PATH}" >/dev/null 2>&1 || true
        else
            sudo pkill -INT -f "tcpdump .* -w ${PCAP_PATH}" >/dev/null 2>&1 || true
        fi

        # Also stop the wrapper process if it is still around.
        kill -INT "$CAP_PID" >/dev/null 2>&1 || true
        wait "$CAP_PID" >/dev/null 2>&1 || true
    fi
}

trap cleanup_capture EXIT

START_EPOCH="$(date -u +%s)"
START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ "$NO_CAPTURE" -eq 0 ]]; then
    if [[ "$EUID" -eq 0 ]]; then
        SUDO_CMD=""
    elif sudo -n true 2>/dev/null; then
        SUDO_CMD="sudo"
    else
        echo "Capture requires root privileges for tcpdump." >&2
        echo "Run this command once to authenticate, then rerun session runner:" >&2
        echo "  sudo -v" >&2
        exit 3
    fi

    if [[ -n "$CAPTURE_FILTER" ]]; then
        $SUDO_CMD tcpdump -i "$INTERFACE" -s 0 -n -U -w "$PCAP_PATH" "$CAPTURE_FILTER" >/dev/null 2>&1 &
    else
        $SUDO_CMD tcpdump -i "$INTERFACE" -s 0 -n -U -w "$PCAP_PATH" >/dev/null 2>&1 &
    fi
    CAP_PID="$!"
    CAPTURE_STARTED=1

    sleep "$PRE_SECONDS"
fi

run_scenario "$SCENARIO" "$TARGET_HOST" "$ITERATIONS"

if [[ "$NO_CAPTURE" -eq 0 ]]; then
    sleep "$POST_SECONDS"
    cleanup_capture
    CAPTURE_STARTED=0
fi

END_EPOCH="$(date -u +%s)"
END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION="$((END_EPOCH - START_EPOCH))"

cat > "$META_PATH" <<EOF
{
  "session_id": "$SESSION_ID",
  "scenario": "$SCENARIO",
  "target_host": "$TARGET_HOST",
  "iterations": $ITERATIONS,
  "capture_enabled": $((1 - NO_CAPTURE)),
  "interface": "$INTERFACE",
  "capture_filter": "$CAPTURE_FILTER",
  "start_time_utc": "$START_ISO",
  "end_time_utc": "$END_ISO",
  "duration_seconds": $DURATION,
  "host": "$(hostname)",
  "project_root": "$PROJECT_ROOT",
  "notes": "Authorized defensive lab session"
}
EOF

if [[ "$NO_CAPTURE" -eq 0 ]]; then
    sha256sum "$PCAP_PATH" > "$PCAP_PATH.sha256"
fi
sha256sum "$META_PATH" > "$META_PATH.sha256"

echo "Session completed"
echo "Session directory: $SESSION_DIR"
if [[ "$NO_CAPTURE" -eq 0 ]]; then
    echo "PCAP: $PCAP_PATH"
    echo "PCAP hash: $PCAP_PATH.sha256"
fi
echo "Metadata: $META_PATH"
echo "Metadata hash: $META_PATH.sha256"
