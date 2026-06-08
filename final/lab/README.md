# Lab Session Runner (Local)

This folder provides a reproducible workflow for IDS data collection:

- 1 session
- 1 traffic scenario
- 1 PCAP
- 1 metadata JSON
- SHA256 hashes for integrity

## Important scope

Use only in an authorized defensive lab environment.

## Files

- `session_runner.sh`: main orchestrator script.
- `scenarios.sh`: local traffic scenarios.
- `sessions/`: generated outputs.

## Quick start

```bash
cd /home/ning/Graduation-Thesis
chmod +x final/lab/session_runner.sh final/lab/scenarios.sh

# Step 1: authenticate sudo once for tcpdump capture
sudo -v

# Step 2: run one session
bash final/lab/session_runner.sh \
  --scenario icmp_echo \
  --target-host 127.0.0.1 \
  --iterations 20 \
  --interface lo \
  --session-tag run01
```

Output folder pattern:

```text
final/lab/sessions/YYYYMMDD_HHMMSS_<scenario>_<tag>/
```

Each folder contains:

- `<session_id>.pcap`
- `<session_id>.pcap.sha256`
- `<session_id>.metadata.json`
- `<session_id>.metadata.json.sha256`

## Metadata fields

Metadata records scenario, timestamps, interface, capture filter, target host, and run duration.

## Supported scenarios

- `benign_baseline`
- `icmp_echo`
- `tcp_connect_burst`

## Notes for 3-VM expansion

This runner is local-first. For a full 3-VM setup (attacker/capture/victim), keep this session naming and metadata schema, then execute scenario traffic remotely on the attacker VM while keeping capture on the capture VM.
