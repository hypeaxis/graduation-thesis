"""ExplainService — Single Responsibility: feature importance theo lớp tấn công.

importance = |mean_attack - mean_benign| / std_benign (chuẩn hoá mềm để bar đều nhìn thấy).
"""
from __future__ import annotations

import numpy as np

from .config import Settings
from .corpus import CorpusLoader
from .features import EXPECTED_FEATURES_80
from .scenarios import ATTACK_KEYS


class ExplainService:
    def __init__(self, settings: Settings, loader: CorpusLoader):
        self.settings = settings
        self.loader = loader
        self._table: dict[str, list] = {}

    def build(self) -> None:
        benign = self.loader.load("benign")
        if benign is None:
            return
        bmean, bstd = benign.feat_mean, benign.feat_std
        denom = np.maximum(bstd, np.median(bstd) + 1e-6)
        for key in ATTACK_KEYS:
            c = self.loader.load(key)
            if c is None:
                continue
            diff = np.abs(c.feat_mean - bmean) / denom
            order = np.argsort(diff)[::-1][:5]
            top = diff[order]
            norm = top / (top.max() + 1e-9)
            self._table[self.settings.label_map[key]] = [
                {"feature": EXPECTED_FEATURES_80[i].replace("_", " "),
                 "importance": round(float(0.25 + 0.75 * norm[r]), 3)}
                for r, i in enumerate(order)
            ]

    def for_class(self, cls: str) -> list:
        return self._table.get(cls, [])

    @property
    def classes(self) -> list:
        return list(self._table.keys())
