"""
RobustLogScaler — tiền xử lý Bước 4 (log-transform + robust scale + clip).

Thay cho HybridFeatureScaler (PowerTransformer) trong thí nghiệm Bước 4:
  1) log1p các feature đuôi nặng, không âm (byte-count / duration / rate / IAT) — 4.1
  2) robust scale bằng median / IQR (thay standard/power scale) — 4.2
  3) clip z-score về [-CLIP, CLIP] để chặn ngoại suy — 4.2

Thiết kế PARITY: toàn bộ phép biến đổi nằm TRONG class này. Train và live cùng load 1 file
đã fit -> áp y hệt. FeatureExtractor giữ nguyên (chỉ tạo 80 feature thô); mọi scaling ở đây.

Interface trùng HybridFeatureScaler (transform / save / load) để dễ thay thế.
"""
from __future__ import annotations
import joblib
import numpy as np

# Feature đuôi nặng, KHÔNG âm -> log1p an toàn (theo chẩn đoán Bước 1).
LOG_FEATURES = [
    "Flow_Duration", "Total_Length_of_Fwd_Packets", "Total_Length_of_Bwd_Packets",
    "Flow_Bytes_s", "Flow_Packets_s", "Fwd_Packets_s", "Bwd_Packets_s",
    "Flow_IAT_Mean", "Flow_IAT_Std", "Flow_IAT_Max", "Flow_IAT_Min",
    "Fwd_IAT_Total", "Fwd_IAT_Mean", "Fwd_IAT_Std", "Fwd_IAT_Max", "Fwd_IAT_Min",
    "Bwd_IAT_Total", "Bwd_IAT_Mean", "Bwd_IAT_Std", "Bwd_IAT_Max", "Bwd_IAT_Min",
    "Fwd_Header_Length", "Bwd_Header_Length", "Subflow_Fwd_Bytes", "Subflow_Bwd_Bytes",
    "Packet_Length_Variance", "Init_Win_bytes_forward", "Init_Win_bytes_backward",
    "Active_Mean", "Active_Max", "Active_Min", "Idle_Mean", "Idle_Max", "Idle_Min",
    "Custom_Fwd_Pkt_Rate", "Custom_IAT_Anomaly",
]


class RobustLogScaler:
    version = "robust-log-v1"

    def __init__(self, feature_names=None, clip=5.0):
        self.feature_names = list(feature_names) if feature_names is not None else None
        self.clip = float(clip)
        self.log_idx = None
        self.center_ = None   # median (sau log)
        self.scale_ = None    # IQR   (sau log)

    def _resolve_log_idx(self):
        if self.feature_names is None:
            raise ValueError("Cần feature_names để xác định cột log.")
        name_to_i = {n: i for i, n in enumerate(self.feature_names)}
        self.log_idx = np.array([name_to_i[n] for n in LOG_FEATURES if n in name_to_i], dtype=int)

    def _apply_log(self, X):
        Xc = X.astype(np.float64, copy=True)
        if len(self.log_idx):
            Xc[:, self.log_idx] = np.log1p(np.clip(Xc[:, self.log_idx], 0.0, None))
        return Xc

    def fit(self, X):
        self._resolve_log_idx()
        Xc = self._apply_log(np.asarray(X))
        self.center_ = np.median(Xc, axis=0)
        q75, q25 = np.percentile(Xc, [75, 25], axis=0)
        iqr = q75 - q25
        iqr[iqr == 0] = 1.0                    # tránh chia 0 (feature hằng)
        self.scale_ = iqr
        return self

    def transform(self, X):
        if self.center_ is None:
            raise ValueError("Chưa fit RobustLogScaler.")
        Xc = self._apply_log(np.asarray(X))
        Z = (Xc - self.center_) / self.scale_
        return np.clip(Z, -self.clip, self.clip).astype(np.float32)

    def fit_transform(self, X):
        return self.fit(X).transform(X)

    def save(self, path):
        joblib.dump({
            "feature_names": self.feature_names, "clip": self.clip, "log_idx": self.log_idx,
            "center_": self.center_, "scale_": self.scale_, "version": self.version,
        }, path)

    @classmethod
    def load(cls, path):
        d = joblib.load(path)
        obj = cls(feature_names=d["feature_names"], clip=d["clip"])
        obj.log_idx = d["log_idx"]; obj.center_ = d["center_"]; obj.scale_ = d["scale_"]
        return obj
