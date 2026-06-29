"""ids_replay — Replay-based Live Detection (kiến trúc SOLID).

Mỗi module một trách nhiệm:
  config       — nạp cấu hình (Settings)
  features     — trích đặc trưng 80-feature + tiện ích flow (FeatureExtractor)
  model        — interface Classifier + FTTransformerClassifier (Dependency Inversion)
  postprocess  — PredictionRule (Open/Closed): ConfidenceThresholdRule, PortScanRule, RulePipeline
  corpus       — Corpus + CorpusLoader (CSV → events đã dự đoán)
  scenarios    — ScenarioService (danh sách kịch bản + mixed)
  explain      — ExplainService (feature importance)
  streaming    — ConnectionManager + ReplayEngine (play/pause/reset/speed)
  api          — create_app() (FastAPI, phụ thuộc abstraction qua DI)
"""
