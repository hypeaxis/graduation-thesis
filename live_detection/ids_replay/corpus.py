"""Corpus — Single Responsibility: 1 file flow → danh sách events đã dự đoán + gán nhãn.

CorpusLoader phụ thuộc abstraction (Classifier, RulePipeline) qua DI, không tự tạo chúng.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import Settings
from .features import FeatureExtractor, col
from .model import Classifier
from .postprocess import RulePipeline


class Corpus:
    """Kết quả nạp 1 kịch bản: events (dự đoán sẵn) + thống kê feature cho explainability."""

    def __init__(self, key: str, true_label: str, events: list,
                 feat_mean: np.ndarray, feat_std: np.ndarray):
        self.key = key
        self.true_label = true_label
        self.events = events
        self.n = len(events)
        self.feat_mean = feat_mean
        self.feat_std = feat_std

    def benign_events(self) -> list:
        return [e for e in self.events if e["true"] == "Benign"]


class CorpusLoader:
    """Nạp + cache corpus. predict-on-load: dự đoán hết 1 lần để replay không gọi model."""

    def __init__(self, settings: Settings, extractor: FeatureExtractor,
                 classifier: Classifier, pipeline: RulePipeline):
        self.settings = settings
        self.extractor = extractor
        self.classifier = classifier
        self.pipeline = pipeline
        self._cache: dict[str, Corpus] = {}

    def path_for(self, key: str) -> Path | None:
        p = self.settings.replay_files.get(key)
        return p if (p and p.exists()) else None

    def available(self, key: str) -> bool:
        return self.path_for(key) is not None

    def load(self, key: str) -> Corpus | None:
        if key in self._cache:
            return self._cache[key]
        path = self.path_for(key)
        if path is None:
            return None
        self._cache[key] = self._build(key, path)
        return self._cache[key]

    def _build(self, key: str, path: Path) -> Corpus:
        s = self.settings
        true_label = s.label_map.get(key, "Benign")
        df = pd.read_csv(path, low_memory=False)
        df.columns = df.columns.str.strip()
        if len(df) > s.max_flows:
            df = df.sample(s.max_flows, random_state=42).reset_index(drop=True)

        X = self.extractor.build(df)
        preds, confs = self.classifier.predict(X)
        preds = self.pipeline.apply(df, preds, confs)   # Phương án A + D1

        src = col(df, "Src IP").astype(str).values
        dst = col(df, "Dst IP").astype(str).values
        dport = col(df, "Dst Port", 0).astype(str).values
        events = []
        for i in range(len(df)):
            true = "Benign" if key == "benign" else (true_label if src[i] == s.attacker_ip else "Benign")
            events.append({
                "src": src[i], "dst": dst[i], "dst_port": dport[i],
                "pred": str(preds[i]), "conf": round(float(confs[i]), 3), "true": true,
            })

        mask = (src == s.attacker_ip) if key != "benign" else np.ones(len(df), dtype=bool)
        feat_mean = X[mask].mean(axis=0) if mask.any() else X.mean(axis=0)
        return Corpus(key, true_label, events, feat_mean, X.std(axis=0))
