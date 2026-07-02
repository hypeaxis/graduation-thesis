"""Cấu hình hệ thống — Single Responsibility: chỉ nạp + giữ config."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    attacker_ip: str
    victim_ip: str
    model_pt: Path
    scaler_pkl: Path
    encoder_pkl: Path
    replay_files: dict          # key -> Path (tuyệt đối)
    label_map: dict             # key -> nhãn lớp
    conf_threshold: float       # Phương án A
    portscan_rule: dict         # cấu hình rule D1
    max_flows: int = 8000       # cap flow/file để demo mượt

    @staticmethod
    def load(config_path: Path, repo_root: Path) -> "Settings":
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
        m = cfg["model"]
        return Settings(
            repo_root=repo_root,
            attacker_ip=cfg["attacker_ip"],
            victim_ip=cfg.get("victim_ip", ""),
            model_pt=repo_root / m["model_pt"],
            scaler_pkl=repo_root / m["scaler_pkl"],
            encoder_pkl=repo_root / m["encoder_pkl"],
            replay_files={k: repo_root / v for k, v in cfg["replay_files"].items()},
            label_map=cfg["label_map"],
            conf_threshold=float(cfg.get("conf_threshold", 0.0)),
            portscan_rule=cfg.get("portscan_rule", {}),
        )
