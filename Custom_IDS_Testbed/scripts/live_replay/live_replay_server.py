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
# HERE = .../Graduation-Thesis/Custom_IDS_Testbed/scripts/live_replay
REPO_ROOT = HERE.parents[2]          # .../Graduation-Thesis
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


class Corpus:
    """Một file flow đã nạp + dự đoán sẵn (predict-on-load → replay loop khỏi gọi torch)."""
    def __init__(self, key: str, path: Path, detector: Detector):
        self.key = key
        self.true_label = LABEL_MAP.get(key, "Benign")
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        X = build_features(df)
        preds, confs = detector.predict(X)
        src = _col(df, "Src IP").astype(str).values
        dst = _col(df, "Dst IP").astype(str).values
        dport = _col(df, "Dst Port", 0).astype(str).values
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

    def benign_only(self):
        """Các flow benign (không từ attacker) — fallback cho baseline nếu thiếu file benign."""
        return [e for e in self.events if e["true"] == "Benign"]


# ----------------------------------------------------------------------------
# App state
# ----------------------------------------------------------------------------
class State:
    def __init__(self):
        self.detector: Detector | None = None
        self.corpus: dict[str, Corpus] = {}
        self.clients: set[WebSocket] = set()
        self.baseline_task: asyncio.Task | None = None
        self.attack_task: asyncio.Task | None = None
        self.attack_stats = {"attack": None, "total": 0, "correct": 0, "by_pred": {}}

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


async def stream_loop(events, rate: float, stream: str, loop: bool, attack_key: str | None):
    """Phát events ở tốc độ `rate` flows/giây; loop=True thì lặp vô hạn (baseline)."""
    delay = 1.0 / max(rate, 0.1)
    i = 0
    n = len(events)
    if n == 0:
        return
    try:
        while True:
            e = events[i % n]
            await broadcast({"type": "flow", "stream": stream, "ts": time.time(), **e})
            if stream == "attack" and attack_key:
                s = ST.attack_stats
                s["total"] += 1
                if e["pred"] == e["true"]:
                    s["correct"] += 1
                s["by_pred"][e["pred"]] = s["by_pred"].get(e["pred"], 0) + 1
                if s["total"] % 10 == 0 or (i + 1) == n:
                    await broadcast({"type": "stats", **s})
            i += 1
            if not loop and i >= n:
                break
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        pass
    if stream == "attack":
        await broadcast({"type": "attack_done", "attack": attack_key, **ST.attack_stats})


# ----------------------------------------------------------------------------
# REST API
# ----------------------------------------------------------------------------
class BaselineReq(BaseModel):
    on: bool = True
    rate: float = 8.0


class AttackReq(BaseModel):
    attack: str
    rate: float = 20.0
    loop: bool = False


@app.get("/api/files")
def api_files():
    out = {}
    for key in CONFIG["replay_files"]:
        path = ST.file_for(key)
        out[key] = {"label": LABEL_MAP.get(key, key),
                    "available": path is not None,
                    "path": str(path) if path else CONFIG["replay_files"][key]}
    return {"files": out, "attacker_ip": ATTACKER_IP, "classes": list(ST.detector.encoder.classes_)}


@app.post("/api/baseline")
async def api_baseline(req: BaselineReq):
    if ST.baseline_task:
        ST.baseline_task.cancel()
        ST.baseline_task = None
    if not req.on:
        await broadcast({"type": "baseline", "on": False})
        return {"ok": True, "on": False}
    # Ưu tiên file benign; nếu thiếu, lấy benign-only từ portscan (run11) làm fallback
    corp = ST.get_corpus("benign")
    events = corp.events if corp else None
    if not events:
        ps = ST.get_corpus("portscan")
        events = ps.benign_only() if ps else []
    if not events:
        return JSONResponse({"ok": False, "error": "Không có dữ liệu benign để chạy baseline"}, 400)
    ST.baseline_task = asyncio.create_task(
        stream_loop(events, req.rate, "baseline", loop=True, attack_key=None))
    await broadcast({"type": "baseline", "on": True, "rate": req.rate, "count": len(events)})
    return {"ok": True, "on": True, "count": len(events)}


@app.post("/api/attack")
async def api_attack(req: AttackReq):
    corp = ST.get_corpus(req.attack)
    if corp is None:
        return JSONResponse(
            {"ok": False, "error": f"Chưa có file cho '{req.attack}'. Hãy thu bằng collect_isolated.sh."}, 404)
    if ST.attack_task:
        ST.attack_task.cancel()
    ST.attack_stats = {"attack": req.attack, "total": 0, "correct": 0, "by_pred": {}}
    await broadcast({"type": "attack_start", "attack": req.attack,
                     "label": corp.true_label, "rate": req.rate, "count": corp.n})
    ST.attack_task = asyncio.create_task(
        stream_loop(corp.events, req.rate, "attack", loop=req.loop, attack_key=req.attack))
    return {"ok": True, "attack": req.attack, "count": corp.n}


@app.post("/api/attack/stop")
async def api_attack_stop():
    if ST.attack_task:
        ST.attack_task.cancel()
        ST.attack_task = None
    await broadcast({"type": "attack_stop"})
    return {"ok": True}


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


@app.on_event("startup")
def _startup():
    print("[*] Nạp model V8.5 ...")
    ST.detector = Detector()
    print(f"[*] Sẵn sàng. Classes: {list(ST.detector.encoder.classes_)}")
    avail = [k for k in CONFIG["replay_files"] if ST.file_for(k)]
    print(f"[*] File replay sẵn có: {avail or '(chưa có — hãy thu bằng collect_isolated.sh)'}")
