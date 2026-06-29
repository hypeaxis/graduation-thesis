"""Composition root — nơi DUY NHẤT khởi tạo + wire mọi dependency (Dependency Injection).

Chạy:  uvicorn server:app --host 0.0.0.0 --port 8000   (từ thư mục Replay_Live_Detection/)
"""
from pathlib import Path

from ids_replay.config import Settings
from ids_replay.features import FeatureExtractor
from ids_replay.model import FTTransformerClassifier
from ids_replay.postprocess import ConfidenceThresholdRule, PortScanRule, RulePipeline
from ids_replay.corpus import CorpusLoader
from ids_replay.scenarios import ScenarioService, ALL_KEYS
from ids_replay.explain import ExplainService
from ids_replay.streaming import ConnectionManager, ReplayEngine
from ids_replay.api import create_app

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[0]            # .../Graduation-Thesis

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

app = create_app(scenarios=scenarios, explain=explain, engine=engine,
                 manager=manager, classifier=classifier,
                 dashboard_path=HERE / "dashboard.html")


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
