#!/usr/bin/env python3
"""
live_replay_server.py — Replay-based Live Detection (FastAPI + WebSocket)
========================================================================
Phát lại các file flow đã thu (CICFlowMeter *_Flow.csv) qua model V8.5 và
đẩy kết quả lên dashboard theo thời gian thực, mô phỏng "live detection".

Kịch bản demo:
  1. Bật benign baseline (chạy nền liên tục)  → dashboard xanh, FP thấp
  2. Tiêm dần từng loại tấn công (PortScan → Brute Force → Web Attack → DoS)
  3. Overlay accuracy: so dự đoán vs nhãn-theo-IP (ground truth)

Model: V8.5 (FT-Transformer 80-feature, 5 lớp: Benign/Brute Force/DoS/PortScan/Web Attack)

Chạy:
  cd Custom_IDS_Testbed/scripts/live_replay
  uvicorn live_replay_server:app --host 0.0.0.0 --port 8000
  # mở http://localhost:8000
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import joblib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

warnings.filterwarnings("ignore")

# ----------------------------------------------------------------------------
# Paths & config
# ----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
# HERE = .../Graduation-Thesis/Replay_Live_Detection
REPO_ROOT = HERE.parents[0]          # .../Graduation-Thesis
CONFIG_PATH = HERE / "replay_config.json"

sys.path.insert(0, str(REPO_ROOT / "CIC_IDS_2017_Workspace/src/models"))
sys.path.insert(0, str(REPO_ROOT / "Phase3_4_Retrain/src"))

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

ATTACKER_IP = CONFIG["attacker_ip"]
LABEL_MAP = CONFIG["label_map"]

EXPECTED_FEATURES_80 = [
    'Flow_Duration','Total_Fwd_Packets','Total_Backward_Packets','Total_Length_of_Fwd_Packets','Total_Length_of_Bwd_Packets','Fwd_Packet_Length_Max','Fwd_Packet_Length_Min','Fwd_Packet_Length_Mean','Fwd_Packet_Length_Std','Bwd_Packet_Length_Max','Bwd_Packet_Length_Min','Bwd_Packet_Length_Mean','Bwd_Packet_Length_Std','Flow_Bytes_s','Flow_Packets_s','Flow_IAT_Mean','Flow_IAT_Std','Flow_IAT_Max','Flow_IAT_Min','Fwd_IAT_Total','Fwd_IAT_Mean','Fwd_IAT_Std','Fwd_IAT_Max','Fwd_IAT_Min','Bwd_IAT_Total','Bwd_IAT_Mean','Bwd_IAT_Std','Bwd_IAT_Max','Bwd_IAT_Min','Fwd_PSH_Flags','Fwd_URG_Flags','Fwd_Header_Length','Bwd_Header_Length','Fwd_Packets_s','Bwd_Packets_s','Min_Packet_Length','Max_Packet_Length','Packet_Length_Mean','Packet_Length_Std','Packet_Length_Variance','FIN_Flag_Count','SYN_Flag_Count','RST_Flag_Count','PSH_Flag_Count','ACK_Flag_Count','URG_Flag_Count','CWE_Flag_Count','ECE_Flag_Count','Down_Up_Ratio','Average_Packet_Size','Avg_Fwd_Segment_Size','Avg_Bwd_Segment_Size','Subflow_Fwd_Packets','Subflow_Fwd_Bytes','Subflow_Bwd_Packets','Subflow_Bwd_Bytes','Init_Win_bytes_forward','Init_Win_bytes_backward','act_data_pkt_fwd','min_seg_size_forward','Active_Mean','Active_Std','Active_Max','Active_Min','Idle_Mean','Idle_Std','Idle_Max','Idle_Min','Port_Is_Web','Port_Is_RemoteAccess','Port_Is_WellKnown','Port_Is_Registered','Port_Is_Ephemeral','Custom_Fwd_Pkt_Rate','Custom_Slow_Index','Custom_Pkt_Var_Ratio','Custom_IAT_Anomaly','Custom_IAT_CV','Custom_Bwd_Pkt_Ratio','Custom_Pkt_Size_Ratio',
]

CICFLOW_MAP = {
    'Dst Port':'Destination_Port','Flow Duration':'Flow_Duration','Total Fwd Packet':'Total_Fwd_Packets','Total Bwd packets':'Total_Backward_Packets','Total Length of Fwd Packet':'Total_Length_of_Fwd_Packets','Total Length of Bwd Packet':'Total_Length_of_Bwd_Packets','Fwd Packet Length Max':'Fwd_Packet_Length_Max','Fwd Packet Length Min':'Fwd_Packet_Length_Min','Fwd Packet Length Mean':'Fwd_Packet_Length_Mean','Fwd Packet Length Std':'Fwd_Packet_Length_Std','Bwd Packet Length Max':'Bwd_Packet_Length_Max','Bwd Packet Length Min':'Bwd_Packet_Length_Min','Bwd Packet Length Mean':'Bwd_Packet_Length_Mean','Bwd Packet Length Std':'Bwd_Packet_Length_Std','Flow Bytes/s':'Flow_Bytes_s','Flow Packets/s':'Flow_Packets_s','Flow IAT Mean':'Flow_IAT_Mean','Flow IAT Std':'Flow_IAT_Std','Flow IAT Max':'Flow_IAT_Max','Flow IAT Min':'Flow_IAT_Min','Fwd IAT Total':'Fwd_IAT_Total','Fwd IAT Mean':'Fwd_IAT_Mean','Fwd IAT Std':'Fwd_IAT_Std','Fwd IAT Max':'Fwd_IAT_Max','Fwd IAT Min':'Fwd_IAT_Min','Bwd IAT Total':'Bwd_IAT_Total','Bwd IAT Mean':'Bwd_IAT_Mean','Bwd IAT Std':'Bwd_IAT_Std','Bwd IAT Max':'Bwd_IAT_Max','Bwd IAT Min':'Bwd_IAT_Min','Fwd PSH Flags':'Fwd_PSH_Flags','Fwd URG Flags':'Fwd_URG_Flags','Fwd Header Length':'Fwd_Header_Length','Bwd Header Length':'Bwd_Header_Length','Fwd Packets/s':'Fwd_Packets_s','Bwd Packets/s':'Bwd_Packets_s','Packet Length Min':'Min_Packet_Length','Packet Length Max':'Max_Packet_Length','Packet Length Mean':'Packet_Length_Mean','Packet Length Std':'Packet_Length_Std','Packet Length Variance':'Packet_Length_Variance','FIN Flag Count':'FIN_Flag_Count','SYN Flag Count':'SYN_Flag_Count','RST Flag Count':'RST_Flag_Count','PSH Flag Count':'PSH_Flag_Count','ACK Flag Count':'ACK_Flag_Count','URG Flag Count':'URG_Flag_Count','CWR Flag Count':'CWE_Flag_Count','ECE Flag Count':'ECE_Flag_Count','Down/Up Ratio':'Down_Up_Ratio','Average Packet Size':'Average_Packet_Size','Fwd Segment Size Avg':'Avg_Fwd_Segment_Size','Bwd Segment Size Avg':'Avg_Bwd_Segment_Size','Subflow Fwd Packets':'Subflow_Fwd_Packets','Subflow Fwd Bytes':'Subflow_Fwd_Bytes','Subflow Bwd Packets':'Subflow_Bwd_Packets','Subflow Bwd Bytes':'Subflow_Bwd_Bytes','FWD Init Win Bytes':'Init_Win_bytes_forward','Bwd Init Win Bytes':'Init_Win_bytes_backward','Fwd Act Data Pkts':'act_data_pkt_fwd','Fwd Seg Size Min':'min_seg_size_forward','Active Mean':'Active_Mean','Active Std':'Active_Std','Active Max':'Active_Max','Active Min':'Active_Min','Idle Mean':'Idle_Mean','Idle Std':'Idle_Std','Idle Max':'Idle_Max','Idle Min':'Idle_Min',
}


def build_features(df: pd.DataFrame) -> np.ndarray:
    """Raw CICFlowMeter columns → 80-feature matrix (giống dataset_builder_v2 / V8.5)."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    df.rename(columns=CICFLOW_MAP, inplace=True)
    p = df['Destination_Port'].astype(int)
    df['Port_Is_Web'] = p.isin([80, 443, 8080, 8443, 8888]).astype(int)
    df['Port_Is_RemoteAccess'] = p.isin([21, 22, 23, 2222, 3389]).astype(int)
    df['Port_Is_WellKnown'] = (p <= 1023).astype(int)
    df['Port_Is_Registered'] = ((p > 1023) & (p <= 49151)).astype(int)
    df['Port_Is_Ephemeral'] = (p > 49151).astype(int)
    fd = df['Flow_Duration'].astype(float).replace(0, 1)
    df['Custom_Fwd_Pkt_Rate'] = (df['Total_Fwd_Packets'].astype(float) / (fd / 1e6)).fillna(0)
    df['Custom_Slow_Index'] = (fd / df['Flow_IAT_Max'].astype(float).replace(0, 1)).fillna(0)
    df['Custom_Pkt_Var_Ratio'] = (df['Packet_Length_Variance'].astype(float).replace(0, 1) /
                                  df['Average_Packet_Size'].astype(float).replace(0, 1)).fillna(0)
    df['Custom_IAT_Anomaly'] = (df['Flow_IAT_Max'].astype(float) /
                                df['Fwd_IAT_Std'].astype(float).replace(0, 1)).fillna(0)
    df['Custom_IAT_CV'] = (df['Flow_IAT_Std'].astype(float) /
                           (df['Flow_IAT_Mean'].astype(float) + 1e-6)).fillna(0)
    df['Custom_Bwd_Pkt_Ratio'] = (df['Total_Backward_Packets'].astype(float) /
                                  (df['Total_Fwd_Packets'].astype(float) + 1e-6)).fillna(0)
    df['Custom_Pkt_Size_Ratio'] = (df['Min_Packet_Length'].astype(float) /
                                   (df['Max_Packet_Length'].astype(float) + 1e-6)).fillna(0)
    for c in EXPECTED_FEATURES_80:
        if c not in df.columns:
            df[c] = 0
    X = df[EXPECTED_FEATURES_80].values.astype(np.float32)
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


# ----------------------------------------------------------------------------
# Model wrapper (load V8.5 once)
# ----------------------------------------------------------------------------
class Detector:
    def __init__(self):
        from phase2_ft_transformer_v2 import FTTransformer
        from hybrid_feature_scaler import HybridFeatureScaler
        m = CONFIG["model"]
        self.encoder = joblib.load(REPO_ROOT / m["encoder_pkl"])
        self.scaler = HybridFeatureScaler.load(str(REPO_ROOT / m["scaler_pkl"]))
        self.model = FTTransformer(num_features=80, num_classes=len(self.encoder.classes_),
                                   d_model=128, num_heads=8, num_layers=4, d_ff=512,
                                   dropout=0.15, drop_path_rate=0.15)
        self.model.load_state_dict(
            torch.load(REPO_ROOT / m["model_pt"], map_location="cpu", weights_only=False))
        self.model.eval()

    def predict(self, X: np.ndarray):
        Xs = self.scaler.transform(X)
        out = []
        with torch.no_grad():
            for i in range(0, len(Xs), 1024):
                logits = self.model(torch.FloatTensor(Xs[i:i + 1024]))
                probs = torch.softmax(logits, dim=1)
                conf, idx = probs.max(dim=1)
                out.append((idx.cpu().numpy(), conf.cpu().numpy()))
        idxs = np.concatenate([o[0] for o in out])
        confs = np.concatenate([o[1] for o in out])
        labels = self.encoder.inverse_transform(idxs)
        return labels, confs


# ----------------------------------------------------------------------------
# Replay corpus: load file -> predict all -> cache list of events
# ----------------------------------------------------------------------------
def _col(df, name, default=""):
    return df[name] if name in df.columns else pd.Series([default] * len(df))


def parse_ts(s):
    """Parse Timestamp CICFlowMeter → ms epoch (0 nếu lỗi)."""
    from datetime import datetime as _dt
    s = str(s).strip()
    for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return _dt.strptime(s, fmt).timestamp() * 1000.0
        except Exception:
            pass
    return 0.0


def port_spread(src_arr, dport_arr, ts_arr, window_ms):
    """Số cổng đích DUY NHẤT theo (src, bucket thời gian window_ms) — đặc trưng PortScan."""
    from collections import defaultdict
    n = len(src_arr)
    bucket = (ts_arr // max(window_ms, 1)).astype(np.int64)
    ports = defaultdict(set)
    for i in range(n):
        ports[(src_arr[i], bucket[i])].add(int(dport_arr[i]))
    return np.array([len(ports[(src_arr[i], bucket[i])]) for i in range(n)], dtype=np.int32)


MAX_FLOWS = 8000   # giới hạn flow nạp/file → predict-on-load nhanh, demo không treo


class Corpus:
    """Một file flow đã nạp + dự đoán sẵn (predict-on-load → replay loop khỏi gọi torch)."""
    def __init__(self, key: str, path: Path, detector: Detector):
        self.key = key
        self.true_label = LABEL_MAP.get(key, "Benign")
        df = pd.read_csv(path, low_memory=False)
        df.columns = df.columns.str.strip()
        if len(df) > MAX_FLOWS:                      # cap file lớn (vd bruteforce 200k) → mượt
            df = df.sample(MAX_FLOWS, random_state=42).reset_index(drop=True)
        X = build_features(df)
        preds, confs = detector.predict(X)
        src = _col(df, "Src IP").astype(str).values
        dst = _col(df, "Dst IP").astype(str).values
        dport = _col(df, "Dst Port", 0).astype(str).values
        preds = list(preds)
        # --- Confidence threshold (Phương án A): attack conf thấp → Benign (giảm FP) ---
        conf_thr = float(CONFIG.get("conf_threshold", 0.0))
        if conf_thr > 0:
            for i in range(len(preds)):
                if preds[i] != "Benign" and confs[i] < conf_thr:
                    preds[i] = "Benign"
        # --- Hybrid PortScan rule (D1): port-spread cao → override nhãn = PortScan ---
        self.ps_override = 0
        rule = CONFIG.get("portscan_rule", {})
        if rule.get("enabled"):
            ts = _col(df, "Timestamp", "").apply(parse_ts).values.astype(np.float64)
            if (ts > 0).mean() > 0.5:   # chỉ áp dụng khi parse được timestamp (tránh false override)
                dpi = pd.to_numeric(_col(df, "Dst Port", 0), errors="coerce").fillna(0).astype(int).values
                inten = port_spread(src, dpi, ts, int(rule.get("window_sec", 2.0) * 1000))
                thr = int(rule.get("min_unique_ports", 15))
                for i in range(len(preds)):
                    if inten[i] >= thr and preds[i] != "PortScan":
                        preds[i] = "PortScan"
                        self.ps_override += 1
        self.events = []
        for i in range(len(df)):
            # nhãn-theo-IP: file attack → flow xuất phát từ attacker mới là attack
            if key == "benign":
                true = "Benign"
            else:
                true = self.true_label if src[i] == ATTACKER_IP else "Benign"
            self.events.append({
                "src": src[i], "dst": dst[i], "dst_port": dport[i],
                "pred": str(preds[i]), "conf": round(float(confs[i]), 3), "true": true,
            })
        self.n = len(self.events)
        # Feature mean/std (raw, chưa scale) cho explainability — lấy theo flow tấn công
        mask = (src == ATTACKER_IP) if key != "benign" else np.ones(len(df), dtype=bool)
        self.feat_mean = X[mask].mean(axis=0) if mask.any() else X.mean(axis=0)
        self.feat_std = X.std(axis=0)

    def benign_only(self):
        """Các flow benign (không từ attacker) — fallback cho baseline nếu thiếu file benign."""
        return [e for e in self.events if e["true"] == "Benign"]


# ----------------------------------------------------------------------------
# App state & scenario
# ----------------------------------------------------------------------------
import random

CLASSES = ["Benign", "Brute Force", "DoS", "PortScan", "Web Attack"]
SCENARIOS = ["mixed", "benign", "portscan", "bruteforce", "webattack", "dos"]
SCENARIO_LABEL = {"mixed": "Mixed (tất cả)", "benign": "Benign", "portscan": "PortScan",
                  "bruteforce": "Brute Force", "webattack": "Web Attack", "dos": "DoS"}
BASE_RATE = 6.0      # flows/giây ở tốc độ 1× (speed là hệ số nhân)
MIXED_MAX = 4000     # giới hạn số flow cho kịch bản 'mixed'


class State:
    def __init__(self):
        self.detector: Detector | None = None
        self.corpus: dict[str, Corpus] = {}
        self.clients: set[WebSocket] = set()
        self.play_task: asyncio.Task | None = None
        self.paused: bool = False
        self.speed: float = 2.0
        self.scenario: str | None = None
        self.explain: dict = {}

    def file_for(self, key: str) -> Path | None:
        rel = CONFIG["replay_files"].get(key)
        if not rel:
            return None
        p = REPO_ROOT / rel
        return p if p.exists() else None

    def get_corpus(self, key: str) -> Corpus | None:
        if key in self.corpus:
            return self.corpus[key]
        path = self.file_for(key)
        if path is None:
            return None
        self.corpus[key] = Corpus(key, path, self.detector)
        return self.corpus[key]

    def scenario_events(self, scenario: str) -> list:
        """Danh sách events cho 1 kịch bản. 'mixed' = trộn tất cả file (xen kẽ)."""
        if scenario == "mixed":
            merged = []
            for k in ["benign", "portscan", "bruteforce", "webattack", "dos"]:
                c = self.get_corpus(k)
                if c:
                    merged.extend(c.events)
            random.Random(42).shuffle(merged)
            return merged[:MIXED_MAX]
        c = self.get_corpus(scenario)
        return list(c.events) if c else []


ST = State()
app = FastAPI(title="Replay-based Live Detection (V8.5)")


async def broadcast(msg: dict):
    dead = []
    data = json.dumps(msg)
    for ws in list(ST.clients):
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ST.clients.discard(ws)


async def in_thread(fn, *args):
    """Chạy hàm đồng bộ trong thread, không chặn event loop.
    Tương thích Python 3.8 (thay cho asyncio.to_thread vốn chỉ có từ 3.9)."""
    return await asyncio.get_event_loop().run_in_executor(None, fn, *args)


async def play_loop(events: list, scenario: str):
    """Phát từng flow của kịch bản; hỗ trợ pause + speed (hệ số nhân). Client tự tính metric."""
    n = len(events)
    await broadcast({"type": "play", "scenario": scenario,
                     "label": SCENARIO_LABEL.get(scenario, scenario), "n": n})
    i = 0
    try:
        while i < n:
            if ST.paused:
                await asyncio.sleep(0.1)
                continue
            e = events[i]
            await broadcast({"type": "flow", "idx": i,
                             "src": e["src"], "dst": e["dst"], "dst_port": e["dst_port"],
                             "truth": e["true"], "pred": e["pred"], "conf": e["conf"]})
            i += 1
            if i % 20 == 0 or i == n:
                await broadcast({"type": "progress", "i": i, "n": n})
            await asyncio.sleep((1.0 / BASE_RATE) / max(ST.speed, 0.1))
        await broadcast({"type": "done", "i": i, "n": n})
    except asyncio.CancelledError:
        pass


# ----------------------------------------------------------------------------
# REST API
# ----------------------------------------------------------------------------
class PlayReq(BaseModel):
    scenario: str = "mixed"
    speed: float = 2.0


class SpeedReq(BaseModel):
    speed: float = 2.0


@app.get("/api/scenarios")
def api_scenarios():
    out = []
    for s in SCENARIOS:
        if s == "mixed":
            avail = any(ST.file_for(k) for k in ["benign", "portscan", "bruteforce", "webattack", "dos"])
        else:
            avail = ST.file_for(s) is not None
        out.append({"key": s, "label": SCENARIO_LABEL[s], "available": avail})
    return {"scenarios": out, "classes": CLASSES, "attacker_ip": ATTACKER_IP}


@app.get("/api/explain/{cls}")
def api_explain(cls: str):
    return {"cls": cls, "features": ST.explain.get(cls, [])}


@app.post("/api/play")
async def api_play(req: PlayReq):
    if req.scenario not in SCENARIOS:
        return JSONResponse({"ok": False, "error": f"Kịch bản không hợp lệ: {req.scenario}"}, 400)
    if ST.play_task:
        ST.play_task.cancel()
        ST.play_task = None
    ST.paused = False
    ST.speed = req.speed
    ST.scenario = req.scenario
    await broadcast({"type": "loading", "what": SCENARIO_LABEL.get(req.scenario, req.scenario)})
    events = await in_thread(ST.scenario_events, req.scenario)
    if not events:
        return JSONResponse({"ok": False, "error": f"Không có dữ liệu cho '{req.scenario}'."}, 404)
    await broadcast({"type": "reset"})
    ST.play_task = asyncio.create_task(play_loop(events, req.scenario))
    return {"ok": True, "scenario": req.scenario, "count": len(events)}


@app.post("/api/pause")
async def api_pause():
    ST.paused = True
    await broadcast({"type": "paused", "paused": True})
    return {"ok": True}


@app.post("/api/resume")
async def api_resume():
    ST.paused = False
    await broadcast({"type": "paused", "paused": False})
    return {"ok": True}


@app.post("/api/reset")
async def api_reset():
    if ST.play_task:
        ST.play_task.cancel()
        ST.play_task = None
    ST.paused = False
    await broadcast({"type": "reset"})
    return {"ok": True}


@app.post("/api/speed")
async def api_speed(req: SpeedReq):
    ST.speed = max(0.25, min(req.speed, 16.0))
    return {"ok": True, "speed": ST.speed}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ST.clients.add(ws)
    try:
        while True:
            await ws.receive_text()   # client không cần gửi gì; giữ kết nối
    except WebSocketDisconnect:
        ST.clients.discard(ws)
    except Exception:
        ST.clients.discard(ws)


@app.get("/")
def index():
    return HTMLResponse((HERE / "dashboard.html").read_text(encoding="utf-8"))


def compute_explain() -> dict:
    """Feature importance per attack class = |mean_attack - mean_benign| / std_benign."""
    benign = ST.get_corpus("benign")
    if benign is None:
        return {}
    bmean, bstd = benign.feat_mean, benign.feat_std
    denom = np.maximum(bstd, np.median(bstd) + 1e-6)   # chặn std quá nhỏ gây bùng nổ z-score
    out = {}
    for key in ["portscan", "bruteforce", "webattack", "dos"]:
        c = ST.get_corpus(key)
        if c is None:
            continue
        diff = np.abs(c.feat_mean - bmean) / denom
        order = np.argsort(diff)[::-1][:5]
        top = diff[order]
        norm = top / (top.max() + 1e-9)                # chuẩn hóa mềm: bar nhỏ nhất vẫn thấy
        out[LABEL_MAP[key]] = [
            {"feature": EXPECTED_FEATURES_80[i].replace("_", " "),
             "importance": round(float(0.25 + 0.75 * norm[r]), 3)}
            for r, i in enumerate(order)
        ]
    return out


@app.on_event("startup")
def _startup():
    print("[*] Nạp model V8.5 ...")
    ST.detector = Detector()
    print(f"[*] Classes: {list(ST.detector.encoder.classes_)}")
    print("[*] Tiền nạp corpus (predict-on-load, có thể mất ~30-60s)...")
    for k in ["benign", "portscan", "bruteforce", "webattack", "dos"]:
        if ST.file_for(k):
            c = ST.get_corpus(k)
            print(f"    {k:<11}: {c.n} flows")
    ST.explain = compute_explain()
    print(f"[*] Explainability sẵn sàng: {list(ST.explain.keys())}")
    print("[*] Sẵn sàng. Mở http://localhost:8000")
