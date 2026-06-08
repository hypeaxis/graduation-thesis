#!/usr/bin/env bash
set -euo pipefail

# Local traffic scenarios for IDS data collection in an authorized lab.
# These scenarios are intentionally limited to defensive testing patterns.

run_scenario() {
    local scenario="$1"
    local target_host="$2"
    local iterations="$3"

    case "$scenario" in
        benign_baseline)
            scenario_benign_baseline "$target_host" "$iterations"
            ;;
        icmp_echo)
            scenario_icmp_echo "$target_host" "$iterations"
            ;;
        tcp_connect_burst)
            scenario_tcp_connect_burst "$target_host" "$iterations"
            ;;
        *)
            echo "Unsupported scenario: $scenario" >&2
            echo "Supported scenarios: benign_baseline, icmp_echo, tcp_connect_burst" >&2
            return 2
            ;;
    esac
}

scenario_benign_baseline() {
    local target_host="$1"
    local iterations="$2"

    ping -c "$iterations" "$target_host" >/dev/null 2>&1 || true

    # Optional local web health request if backend is running.
    curl -m 2 -s "http://${target_host}:8000/api/health" >/dev/null 2>&1 || true
}

scenario_icmp_echo() {
    local target_host="$1"
    local iterations="$2"

    ping -i 0.2 -c "$iterations" "$target_host" >/dev/null
}

scenario_tcp_connect_burst() {
    local target_host="$1"
    local iterations="$2"
    local i

    for i in $(seq 1 "$iterations"); do
        timeout 1 bash -c "echo > /dev/tcp/${target_host}/22" >/dev/null 2>&1 || true
    done
}
