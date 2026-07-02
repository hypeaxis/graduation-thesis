"""ScenarioService — Single Responsibility: quản lý kịch bản replay (gồm 'mixed')."""
from __future__ import annotations

import random

from .corpus import CorpusLoader

ATTACK_KEYS = ["portscan", "bruteforce", "webattack", "dos"]
ALL_KEYS = ["benign"] + ATTACK_KEYS
SCENARIOS = ["mixed"] + ALL_KEYS
SCENARIO_LABEL = {
    "mixed": "Mixed (tất cả)", "benign": "Benign", "portscan": "PortScan",
    "bruteforce": "Brute Force", "webattack": "Web Attack", "dos": "DoS",
}
MIXED_MAX = 4000


class ScenarioService:
    def __init__(self, loader: CorpusLoader):
        self.loader = loader

    def list(self) -> list:
        out = []
        for s in SCENARIOS:
            if s == "mixed":
                avail = any(self.loader.available(k) for k in ALL_KEYS)
            else:
                avail = self.loader.available(s)
            out.append({"key": s, "label": SCENARIO_LABEL[s], "available": avail})
        return out

    def label(self, scenario: str) -> str:
        return SCENARIO_LABEL.get(scenario, scenario)

    def events(self, scenario: str) -> list:
        """Trả events cho 1 kịch bản (đồng bộ — gọi trong thread). 'mixed' = trộn tất cả file."""
        if scenario == "mixed":
            merged = []
            for k in ALL_KEYS:
                c = self.loader.load(k)
                if c:
                    merged.extend(c.events)
            random.Random(42).shuffle(merged)
            return merged[:MIXED_MAX]
        c = self.loader.load(scenario)
        return list(c.events) if c else []
