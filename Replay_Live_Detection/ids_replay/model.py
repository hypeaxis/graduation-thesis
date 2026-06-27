"""Mô hình phân lớp — Dependency Inversion: phần còn lại phụ thuộc interface `Classifier`,
không phụ thuộc FT-Transformer cụ thể. Đổi model = thêm 1 lớp implement Classifier."""
from __future__ import annotations

import sys
from typing import Protocol, Tuple

import numpy as np
import torch
import joblib

from .config import Settings


class Classifier(Protocol):
    """Interface tối thiểu (Interface Segregation): chỉ cần dự đoán."""
    classes_: list

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """X (n, 80) → (labels[str], confidences[float])."""
        ...


class FTTransformerClassifier:
    """Bọc model V8.5 (FT-Transformer 80-feature) + HybridFeatureScaler + encoder."""

    def __init__(self, settings: Settings):
        # các module model/scaler nằm trong repo gốc → thêm vào path
        sys.path.insert(0, str(settings.repo_root / "CIC_IDS_2017_Workspace/src/models"))
        sys.path.insert(0, str(settings.repo_root / "Phase3_4_Retrain/src"))
        from phase2_ft_transformer_v2 import FTTransformer
        from hybrid_feature_scaler import HybridFeatureScaler

        self.encoder = joblib.load(settings.encoder_pkl)
        self.scaler = HybridFeatureScaler.load(str(settings.scaler_pkl))
        self.model = FTTransformer(num_features=80, num_classes=len(self.encoder.classes_),
                                   d_model=128, num_heads=8, num_layers=4, d_ff=512,
                                   dropout=0.15, drop_path_rate=0.15)
        self.model.load_state_dict(
            torch.load(settings.model_pt, map_location="cpu", weights_only=False))
        self.model.eval()

    @property
    def classes_(self) -> list:
        return list(self.encoder.classes_)

    def predict(self, X: np.ndarray):
        Xs = self.scaler.transform(X)
        idxs, confs = [], []
        with torch.no_grad():
            for i in range(0, len(Xs), 1024):
                probs = torch.softmax(self.model(torch.FloatTensor(Xs[i:i + 1024])), dim=1)
                conf, idx = probs.max(dim=1)
                idxs.append(idx.cpu().numpy())
                confs.append(conf.cpu().numpy())
        idxs = np.concatenate(idxs) if idxs else np.array([], dtype=int)
        confs = np.concatenate(confs) if confs else np.array([])
        return self.encoder.inverse_transform(idxs), confs
