import argparse
import json
import pickle
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Tuple

import pandas as pd


# Đường dẫn portable theo gói: file này nằm ở 01_NSL_KDD/src/inference_product/
_PKG_ROOT = Path(__file__).resolve().parents[2]   # -> 01_NSL_KDD/
_MODELS_DIR = _PKG_ROOT / "models"
_LOG_DIR = _PKG_ROOT / "log"

SNORT_CSV_COLUMNS = [
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

BASIC_NUMERIC_DEFAULTS = {
    "duration": 0.0,
    "src_bytes": 0.0,
    "dst_bytes": 0.0,
    "land": 0.0,
    "wrong_fragment": 0.0,
    "urgent": 0.0,
    "hot": 0.0,
    "num_failed_logins": 0.0,
    "logged_in": 0.0,
    "num_compromised": 0.0,
    "root_shell": 0.0,
    "su_attempted": 0.0,
    "num_root": 0.0,
    "num_file_creations": 0.0,
    "num_shells": 0.0,
    "num_access_files": 0.0,
    "num_outbound_cmds": 0.0,
    "is_host_login": 0.0,
    "is_guest_login": 0.0,
    "count": 0.0,
    "srv_count": 0.0,
    "serror_rate": 0.0,
    "srv_serror_rate": 0.0,
    "rerror_rate": 0.0,
    "srv_rerror_rate": 0.0,
    "same_srv_rate": 0.0,
    "diff_srv_rate": 0.0,
    "srv_diff_host_rate": 0.0,
    "dst_host_count": 0.0,
    "dst_host_srv_count": 0.0,
    "dst_host_same_srv_rate": 0.0,
    "dst_host_diff_srv_rate": 0.0,
    "dst_host_same_src_port_rate": 0.0,
    "dst_host_srv_diff_host_rate": 0.0,
    "dst_host_serror_rate": 0.0,
    "dst_host_srv_serror_rate": 0.0,
    "dst_host_rerror_rate": 0.0,
    "dst_host_srv_rerror_rate": 0.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Snort CSV alerts into 122-feature model-ready vectors."
    )
    parser.add_argument(
        "--input",
        default=str(_LOG_DIR / "alert.csv"),
        help="Path to Snort alert CSV (mặc định: 01_NSL_KDD/log/alert.csv).",
    )
    parser.add_argument(
        "--feature-columns",
        default=str(_MODELS_DIR / "feature_columns.json"),
        help="Path to feature_columns.json (mặc định: 01_NSL_KDD/models/).",
    )
    parser.add_argument(
        "--scaler",
        default=str(_MODELS_DIR / "scaler.pkl"),
        help="Path to scaler.pkl fit from train pipeline (mặc định: 01_NSL_KDD/models/).",
    )
    parser.add_argument(
        "--output",
        default=str(_LOG_DIR / "snort_features_122.csv"),
        help="Output CSV path for model-ready vectors (mặc định: 01_NSL_KDD/log/).",
    )
    parser.add_argument(
        "--window-seconds",
        type=float,
        default=2.0,
        help="Sliding window size in seconds for time-based statistics.",
    )
    return parser.parse_args()


def parse_timestamp(raw: str) -> datetime:
    # Snort alert_csv uses format like: MM/DD-HH:MM:SS.uuuuuu (no year).
    raw = str(raw).strip()
    year = datetime.utcnow().year
    return datetime.strptime(f"{year}/{raw}", "%Y/%m/%d-%H:%M:%S.%f")


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def normalize_protocol(proto: object) -> str:
    p = str(proto).strip().lower()
    if p in {"tcp", "udp", "icmp"}:
        return p
    return "tcp"


def infer_service(dst_port: int, proto: str) -> str:
    port_map_tcp = {
        20: "ftp_data",
        21: "ftp",
        22: "ssh",
        23: "telnet",
        25: "smtp",
        53: "domain",
        79: "finger",
        80: "http",
        109: "pop_2",
        110: "pop_3",
        111: "sunrpc",
        119: "nntp",
        123: "ntp_u",
        143: "imap4",
        179: "bgp",
        443: "http_443",
        513: "login",
        514: "shell",
    }
    port_map_udp = {
        53: "domain_u",
        69: "tftp_u",
        123: "ntp_u",
    }
    if proto == "udp":
        return port_map_udp.get(dst_port, "other")
    if proto == "icmp":
        return "eco_i"
    return port_map_tcp.get(dst_port, "other")


def infer_flag(msg: object, proto: str) -> str:
    m = str(msg).upper()
    if proto != "tcp":
        return "SF"
    if "REJ" in m:
        return "REJ"
    if "RST" in m:
        return "RSTR"
    if "SYN" in m:
        return "S0"
    return "SF"


def load_snort_alerts(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, header=None, names=SNORT_CSV_COLUMNS)
    if df.empty:
        raise ValueError("Snort alert CSV is empty.")

    df["ts"] = df["timestamp"].apply(parse_timestamp)
    df["proto_norm"] = df["proto"].apply(normalize_protocol)
    df["srcport_i"] = df["srcport"].apply(safe_int)
    df["dstport_i"] = df["dstport"].apply(safe_int)
    df["service_norm"] = [
        infer_service(dst, proto)
        for dst, proto in zip(df["dstport_i"], df["proto_norm"])
    ]
    df["flag_norm"] = [infer_flag(msg, proto) for msg, proto in zip(df["msg"], df["proto_norm"])]
    df = df.sort_values("ts").reset_index(drop=True)
    return df


def build_feature_rows(df: pd.DataFrame, window_seconds: float) -> pd.DataFrame:
    rows: List[Dict[str, float]] = []
    recent_window: Deque[Dict] = deque()
    recent_100: Deque[Dict] = deque(maxlen=100)
    recent_60: Deque[Dict] = deque()
    last_seen_flow: Dict[Tuple[str, str, str, str], datetime] = {}

    for _, event in df.iterrows():
        now = event["ts"]
        src_ip = str(event["src"])
        dst_ip = str(event["dst"])
        src_port = int(event["srcport_i"])
        service = str(event["service_norm"])
        proto = str(event["proto_norm"])

        while recent_window and (now - recent_window[0]["ts"]).total_seconds() > window_seconds:
            recent_window.popleft()
        while recent_60 and (now - recent_60[0]["ts"]).total_seconds() > 60.0:
            recent_60.popleft()

        win = list(recent_window)
        same_host = [x for x in win if x["dst"] == dst_ip]
        same_service = [x for x in win if x["service"] == service]
        same_host_service = [x for x in same_host if x["service"] == service]
        same_service_diff_host = [x for x in same_service if x["dst"] != dst_ip]

        hist = list(recent_100)
        hist_same_host = [x for x in hist if x["dst"] == dst_ip]
        hist_same_host_service = [x for x in hist_same_host if x["service"] == service]
        hist_same_host_same_src_port = [x for x in hist_same_host if x["srcport"] == src_port]
        hist_same_service = [x for x in hist if x["service"] == service]
        hist_same_service_diff_host = [x for x in hist_same_service if x["dst"] != dst_ip]
        src_recent_60 = [x for x in recent_60 if x["src"] == src_ip]
        src_dst_recent_60 = [x for x in src_recent_60 if x["dst"] == dst_ip]

        flow_key = (src_ip, dst_ip, service, proto)
        prev_ts = last_seen_flow.get(flow_key)
        flow_inter_arrival_sec = (now - prev_ts).total_seconds() if prev_ts else window_seconds

        src_conn_count_60s = float(len(src_recent_60))
        src_unique_dst_ports_60s = float(len({x["dstport"] for x in src_dst_recent_60}))

        interval_component = min(flow_inter_arrival_sec / 3.0, 1.0)
        persistence_component = min(len(src_dst_recent_60) / 15.0, 1.0)
        spread_component = min(src_unique_dst_ports_60s / 20.0, 1.0)
        burst_component = 1.0 - min(len(same_host) / 20.0, 1.0)
        slow_attack_score = (
            0.35 * interval_component
            + 0.25 * persistence_component
            + 0.2 * spread_component
            + 0.2 * burst_component
        )
        slow_attack_flag = 1.0 if slow_attack_score >= 0.65 and src_conn_count_60s >= 8 else 0.0

        base = dict(BASIC_NUMERIC_DEFAULTS)
        base["land"] = 1.0 if src_ip == dst_ip and src_port == int(event["dstport_i"]) else 0.0
        base["count"] = float(len(same_host))
        base["srv_count"] = float(len(same_service))

        if len(same_host) > 0:
            base["same_srv_rate"] = len(same_host_service) / len(same_host)
            base["diff_srv_rate"] = 1.0 - base["same_srv_rate"]

        if len(same_service) > 0:
            base["srv_diff_host_rate"] = len(same_service_diff_host) / len(same_service)

        base["dst_host_count"] = float(len(hist_same_host))
        base["dst_host_srv_count"] = float(len(hist_same_host_service))

        if len(hist_same_host) > 0:
            base["dst_host_same_srv_rate"] = len(hist_same_host_service) / len(hist_same_host)
            base["dst_host_diff_srv_rate"] = 1.0 - base["dst_host_same_srv_rate"]
            base["dst_host_same_src_port_rate"] = len(hist_same_host_same_src_port) / len(hist_same_host)

        if len(hist_same_service) > 0:
            base["dst_host_srv_diff_host_rate"] = len(hist_same_service_diff_host) / len(hist_same_service)

        # Meta-features for slow-and-low attack behavior; these are for diagnostics and
        # rule-based overlays, not part of the 122 model input tensor.
        base["flow_inter_arrival_sec"] = float(max(flow_inter_arrival_sec, 0.0))
        base["src_conn_count_60s"] = src_conn_count_60s
        base["src_unique_dst_ports_60s"] = src_unique_dst_ports_60s
        base["slow_attack_score"] = float(slow_attack_score)
        base["slow_attack_flag"] = float(slow_attack_flag)

        base["_protocol"] = proto
        base["_service"] = service
        base["_flag"] = str(event["flag_norm"])
        rows.append(base)

        event_state = {
            "ts": now,
            "src": src_ip,
            "dst": dst_ip,
            "srcport": src_port,
            "dstport": int(event["dstport_i"]),
            "service": service,
        }
        recent_window.append(event_state)
        recent_100.append(event_state)
        recent_60.append(event_state)
        last_seen_flow[flow_key] = now

    return pd.DataFrame(rows)


def align_to_122_features(feature_df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
    out = pd.DataFrame(0.0, index=feature_df.index, columns=feature_columns)

    for col in BASIC_NUMERIC_DEFAULTS.keys():
        if col in out.columns:
            out[col] = feature_df[col].astype(float)

    protocol_cols = [c for c in out.columns if c.startswith("protocol_type_")]
    service_cols = [c for c in out.columns if c.startswith("service_")]
    flag_cols = [c for c in out.columns if c.startswith("flag_")]

    for i, row in feature_df.iterrows():
        p_col = f"protocol_type_{row['_protocol']}"
        s_col = f"service_{row['_service']}"
        f_col = f"flag_{row['_flag']}"

        if p_col in protocol_cols:
            out.at[i, p_col] = 1.0
        if s_col in service_cols:
            out.at[i, s_col] = 1.0
        if f_col in flag_cols:
            out.at[i, f_col] = 1.0

    return out


def maybe_scale(features: pd.DataFrame, scaler_path: Path, strict: bool = False) -> pd.DataFrame:
    if not scaler_path.exists():
        if strict:
            raise FileNotFoundError(f"Missing scaler artifact: {scaler_path}")
        return features

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    scaled = scaler.transform(features)
    return pd.DataFrame(scaled, columns=features.columns)


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    feature_cols_path = Path(args.feature_columns)
    scaler_path = Path(args.scaler)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input Snort CSV not found: {input_path}")
    if not feature_cols_path.exists():
        raise FileNotFoundError(f"Feature schema not found: {feature_cols_path}")

    with open(feature_cols_path, "r", encoding="utf-8") as f:
        feature_columns = json.load(f)

    raw_df = load_snort_alerts(input_path)
    feature_df = build_feature_rows(raw_df, window_seconds=args.window_seconds)
    aligned = align_to_122_features(feature_df, feature_columns)
    model_ready = maybe_scale(aligned, scaler_path, strict=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_ready.to_csv(output_path, index=False)

    print(f"Snort input rows: {len(raw_df)}")
    print(f"Output vectors: {len(model_ready)}")
    print(f"Feature dimension: {model_ready.shape[1]}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
