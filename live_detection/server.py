"""Composition root — nơi DUY NHẤT khởi tạo + wire mọi dependency (Dependency Injection).

Chạy:  uvicorn server:app --host 0.0.0.0 --port 8000   (từ thư mục live_detection/)
"""
import os
from pathlib import Path

from ids_replay.config import Settings
from ids_replay.features import FeatureExtractor
from ids_replay.model import FTTransformerClassifier
from ids_replay.postprocess import ConfidenceThresholdRule, PortScanRule, RulePipeline
from ids_replay.corpus import CorpusLoader
from ids_replay.scenarios import ScenarioService, ALL_KEYS
from ids_replay.explain import ExplainService
from ids_replay.streaming import ConnectionManager, LiveEngine, ReplayEngine
from ids_replay.live_source import LiveFlowSource
from ids_replay.api import create_app

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE                       # bản độc lập: mọi tài nguyên nằm trong live_detection/

# --- nạp cấu hình ---
settings = Settings.load(HERE / "replay_config.json", REPO_ROOT)

# --- khởi tạo từng thành phần (mỗi cái 1 trách nhiệm) ---
print("[*] Nạp model V8.5 ...")
extractor = FeatureExtractor()
classifier = FTTransformerClassifier(settings)

# --- pipeline hậu xử lý: thêm/bớt luật chỉ ở đây (Open/Closed) ---
rules = []
if settings.conf_threshold > 0:
    rules.append(ConfidenceThresholdRule(settings.conf_threshold))
if settings.portscan_rule.get("enabled"):
    rules.append(PortScanRule(settings.attacker_ip,
                              settings.portscan_rule.get("window_sec", 2.0),
                              settings.portscan_rule.get("min_unique_ports", 15)))
pipeline = RulePipeline(rules)

# --- wire các service ---
loader = CorpusLoader(settings, extractor, classifier, pipeline)
scenarios = ScenarioService(loader)
explain = ExplainService(settings, loader)
manager = ConnectionManager()
engine = ReplayEngine(scenarios, manager)

# --- nguồn LIVE: quét thư mục drop (CSV do cfm ở WSL đẩy sang) ---
# Mặc định = data/live của chính bản repo này. Nếu server và script WSL chạy ở 2 bản repo
# khác nhau (vd server ở /home/ning, capture ghi sang /mnt/d), đặt biến LIVE_DROP_DIR cho khớp.
LIVE_DROP_DIR = Path(os.environ.get("LIVE_DROP_DIR", HERE / "data" / "live"))
print(f"[*] Live drop dir: {LIVE_DROP_DIR}")
live_source = LiveFlowSource(settings, extractor, classifier, pipeline, LIVE_DROP_DIR)
live_engine = LiveEngine(live_source, manager)

app = create_app(scenarios=scenarios, explain=explain, engine=engine,
                 manager=manager, classifier=classifier,
                 dashboard_path=HERE / "dashboard.html",
                 live_engine=live_engine)


@app.on_event("startup")
def _startup():
    print(f"[*] Classes: {classifier.classes_}")
    print(f"[*] Pipeline hậu xử lý: {[r.name for r in rules] or '(không có)'}")
    print("[*] Tiền nạp corpus (predict-on-load, ~30-60s)...")
    for k in ALL_KEYS:
        if loader.available(k):
            c = loader.load(k)
            print(f"    {k:<11}: {c.n} flows")
    explain.build()
    print(f"[*] Explainability: {explain.classes}")
    print("[*] Sẵn sàng. Mở http://localhost:8000")
