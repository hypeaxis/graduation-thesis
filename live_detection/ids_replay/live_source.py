"""Nguồn dữ liệu LIVE — quét thư mục drop (CSV do cfm/CICFlowMeter V4 xuất ở WSL),
biến mỗi file mới thành danh sách event đã dự đoán.

Single Responsibility: chỉ lo "CSV mới trong drop_dir -> events". Dùng lại
FeatureExtractor + Classifier + RulePipeline y hệt luồng replay -> parity tuyệt đối.
Khác replay: dữ liệu tới liên tục theo thời gian thực, và KHÔNG biết nhãn thật (truth).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import Settings
from .features import FeatureExtractor, col
from .model import Classifier
from .postprocess import RulePipeline


class LiveFlowSource:
    """Quét drop_dir tìm *.csv mới, trích đặc trưng + dự đoán, trả events.

    File đã xử lý được chuyển sang drop_dir/processed/ để không đọc lại.
    """

    def __init__(self, settings: Settings, extractor: FeatureExtractor,
                 classifier: Classifier, pipeline: RulePipeline, drop_dir: Path):
        self.settings = settings
        self.extractor = extractor
        self.classifier = classifier
        self.pipeline = pipeline
        self.drop_dir = Path(drop_dir)
        self.processed_dir = self.drop_dir / "processed"
        self.drop_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def reset(self) -> None:
        """Dọn các CSV cũ còn tồn trong drop_dir về processed/ (bắt đầu phiên live sạch)."""
        for p in self.drop_dir.glob("*.csv"):
            self._archive(p)

    def _new_files(self) -> list[Path]:
        # bỏ qua file .part (đang ghi dở); sắp theo thời gian tạo để giữ đúng thứ tự
        files = [p for p in self.drop_dir.glob("*.csv") if not p.name.endswith(".part")]
        return sorted(files, key=lambda p: p.stat().st_mtime)

    def _archive(self, path: Path) -> None:
        try:
            path.replace(self.processed_dir / path.name)
        except Exception:
            # nếu không di chuyển được thì xoá để tránh xử lý lại
            try:
                path.unlink()
            except Exception:
                pass

    def poll_new(self) -> list[dict]:
        """Trả về events từ mọi CSV mới (rỗng nếu chưa có file mới). Gọi trong thread."""
        events: list[dict] = []
        for path in self._new_files():
            try:
                events.extend(self._file_to_events(path))
            except Exception as exc:  # 1 file lỗi không được làm chết vòng live
                print(f"[live_source] loi doc {path.name}: {exc}")
            finally:
                self._archive(path)
        return events

    def _file_to_events(self, path: Path) -> list[dict]:
        df = pd.read_csv(path, low_memory=False)
        df.columns = df.columns.str.strip()
        if df.empty:
            return []
        X = self.extractor.build(df)
        preds, confs = self.classifier.predict(X)
        preds = self.pipeline.apply(df, preds, confs)   # Phương án A + PortScanRule (D1)

        src = col(df, "Src IP").astype(str).values
        dst = col(df, "Dst IP").astype(str).values
        dport = col(df, "Dst Port", 0).astype(str).values
        out = []
        for i in range(len(df)):
            out.append({
                "src": src[i], "dst": dst[i], "dst_port": dport[i],
                "pred": str(preds[i]), "conf": round(float(confs[i]), 3),
                "true": "",  # LIVE: không có nhãn thật
            })
        return out
