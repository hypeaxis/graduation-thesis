from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .schemas import AttackScenario


SNORT_ALERT_COLUMNS = [
    "timestamp",
    "sig_generator",
    "sig_id",
    "sig_rev",
    "msg",
    "proto",
    "src",
    "srcport",
    "dst",
    "dstport",
]


@dataclass
class AlertRow:
    timestamp: str
    sig_generator: str
    sig_id: int
    sig_rev: int
    msg: str
    proto: str
    src: str
    srcport: int
    dst: str
    dstport: int

    def as_list(self) -> list[str]:
        return [
            self.timestamp,
            self.sig_generator,
            str(self.sig_id),
            str(self.sig_rev),
            self.msg,
            self.proto,
            self.src,
            str(self.srcport),
            self.dst,
            str(self.dstport),
        ]


def _snort_timestamp(ts: datetime) -> str:
    return ts.strftime("%m/%d-%H:%M:%S.%f")


def _random_ip(rng: random.Random, private: bool = True) -> str:
    if private:
        return f"192.168.{rng.randint(0, 3)}.{rng.randint(2, 254)}"
    return f"10.10.{rng.randint(0, 3)}.{rng.randint(2, 254)}"


def _normal_row(ts: datetime, rng: random.Random) -> AlertRow:
    proto = rng.choice(["tcp", "udp"])
    dst_port = rng.choice([53, 80, 110, 143, 443])
    return AlertRow(
        timestamp=_snort_timestamp(ts),
        sig_generator="1",
        sig_id=1000001,
        sig_rev=1,
        msg="ET POLICY Normal client flow",
        proto=proto,
        src=_random_ip(rng, private=True),
        srcport=rng.randint(1024, 65535),
        dst=_random_ip(rng, private=False),
        dstport=dst_port,
    )


def _port_scan_row(ts: datetime, rng: random.Random) -> AlertRow:
    return AlertRow(
        timestamp=_snort_timestamp(ts),
        sig_generator="1",
        sig_id=2001219,
        sig_rev=2,
        msg="ET SCAN Nmap Scripting Engine User-Agent Detected",
        proto="tcp",
        src=f"172.16.0.{rng.randint(2, 20)}",
        srcport=rng.randint(30000, 60000),
        dst=f"10.0.0.{rng.randint(5, 15)}",
        dstport=rng.randint(1, 1024),
    )


def _dos_syn_row(ts: datetime, rng: random.Random) -> AlertRow:
    return AlertRow(
        timestamp=_snort_timestamp(ts),
        sig_generator="1",
        sig_id=2010935,
        sig_rev=3,
        msg="ET DOS Possible SYN Flood",
        proto="tcp",
        src=f"203.0.113.{rng.randint(2, 120)}",
        srcport=rng.randint(1024, 65535),
        dst="10.0.1.10",
        dstport=rng.choice([80, 443]),
    )


def _brute_force_row(ts: datetime, rng: random.Random) -> AlertRow:
    return AlertRow(
        timestamp=_snort_timestamp(ts),
        sig_generator="1",
        sig_id=2011967,
        sig_rev=4,
        msg="ET POLICY Possible SSH Brute-Force Attempt",
        proto="tcp",
        src=f"198.51.100.{rng.randint(2, 120)}",
        srcport=rng.randint(1024, 65535),
        dst=f"10.0.2.{rng.randint(20, 35)}",
        dstport=22,
    )


def _scenario_row(scenario: AttackScenario, ts: datetime, rng: random.Random) -> AlertRow:
    if scenario == "normal":
        return _normal_row(ts, rng)
    if scenario == "port_scan":
        return _port_scan_row(ts, rng)
    if scenario == "dos_syn_flood":
        return _dos_syn_row(ts, rng)
    if scenario == "brute_force":
        return _brute_force_row(ts, rng)

    weighted = rng.random()
    if weighted < 0.34:
        return _port_scan_row(ts, rng)
    if weighted < 0.67:
        return _dos_syn_row(ts, rng)
    return _brute_force_row(ts, rng)


def generate_alert_rows(
    scenario: AttackScenario,
    total_events: int,
    benign_ratio: float,
    seed: int | None = None,
) -> list[AlertRow]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc) - timedelta(seconds=total_events)
    rows: list[AlertRow] = []

    for idx in range(total_events):
        ts = now + timedelta(milliseconds=idx * 120)
        if scenario != "normal" and rng.random() < benign_ratio:
            rows.append(_normal_row(ts, rng))
        else:
            rows.append(_scenario_row(scenario, ts, rng))

    return rows


def write_snort_csv(rows: list[AlertRow], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        for row in rows:
            writer.writerow(row.as_list())
