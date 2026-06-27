"""Hậu xử lý dự đoán — Open/Closed Principle.

Mỗi luật là một `PredictionRule`. Thêm luật mới = thêm 1 lớp, KHÔNG sửa `RulePipeline`
hay các luật cũ. Pipeline áp các luật theo thứ tự.
"""
from __future__ import annotations

from typing import List, Protocol

import numpy as np
import pandas as pd

from .features import col, parse_ts, port_spread


class PredictionRule(Protocol):
    """Nhận (df, preds, confs) → trả preds đã hiệu chỉnh. df còn cột định danh (Src IP, Dst Port, Timestamp)."""
    name: str

    def apply(self, df: pd.DataFrame, preds: list, confs: np.ndarray) -> list:
        ...


class ConfidenceThresholdRule:
    """Phương án A: dự đoán TẤN CÔNG có confidence < ngưỡng → hạ về Benign (giảm false positive)."""
    name = "confidence_threshold"

    def __init__(self, threshold: float, benign_label: str = "Benign"):
        self.threshold = float(threshold)
        self.benign_label = benign_label

    def apply(self, df, preds, confs):
        if self.threshold <= 0:
            return preds
        for i in range(len(preds)):
            if preds[i] != self.benign_label and confs[i] < self.threshold:
                preds[i] = self.benign_label
        return preds


class PortScanRule:
    """Phương án D1: host (src) tiếp xúc > N cổng đích duy nhất trong cửa sổ ngắn → PortScan.
    Chỉ override flow xuất phát từ `scanner_ip` (host đang quét) để không gắn cờ flow phản hồi."""
    name = "portscan_port_spread"
    label = "PortScan"

    def __init__(self, scanner_ip: str, window_sec: float = 2.0, min_unique_ports: int = 15):
        self.scanner_ip = scanner_ip
        self.window_ms = int(window_sec * 1000)
        self.min_ports = int(min_unique_ports)

    def apply(self, df, preds, confs):
        ts = col(df, "Timestamp", "").apply(parse_ts).values.astype(np.float64)
        if (ts > 0).mean() <= 0.5:   # parse timestamp thất bại → bỏ qua (tránh false override)
            return preds
        src = col(df, "Src IP").astype(str).values
        dport = pd.to_numeric(col(df, "Dst Port", 0), errors="coerce").fillna(0).astype(int).values
        intensity = port_spread(src, dport, ts, self.window_ms)
        for i in range(len(preds)):
            if intensity[i] >= self.min_ports and src[i] == self.scanner_ip and preds[i] != self.label:
                preds[i] = self.label
        return preds


class RulePipeline:
    """Áp lần lượt các luật. Thứ tự quan trọng: threshold trước (hạ FP), rồi PortScan override."""

    def __init__(self, rules: List[PredictionRule]):
        self.rules = rules

    def apply(self, df: pd.DataFrame, preds, confs) -> list:
        preds = list(preds)
        for rule in self.rules:
            preds = rule.apply(df, preds, confs)
        return preds
