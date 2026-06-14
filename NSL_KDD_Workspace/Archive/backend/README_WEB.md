# IDS Simulation Website

## What this provides
- Simulate Snort-style alert traffic with fake attack scenarios.
- Run the selected 122-feature FT-Transformer pipeline for detection.
- View prediction summary and sample rows in browser.
- Serve frontend + API from one FastAPI app at `http://localhost:8000`.

## Prerequisites
- Python virtual environment at `/home/ning/Graduation-Thesis/.venv`.
- Trained checkpoint configured in `final/primary_pipeline.json`.

## Install dependencies
```bash
cd /home/ning/Graduation-Thesis
source .venv/bin/activate
pip install -r backend/requirements-web.txt
```

## Run modes

### Development mode (auto reload)
```bash
cd /home/ning/Graduation-Thesis
bash backend/run_dev.sh
```

### Product mode (no reload)
```bash
cd /home/ning/Graduation-Thesis
bash backend/run_prod.sh
```

Open website: `http://localhost:8000`

## End-to-end smoke test
```bash
curl -s http://127.0.0.1:8000/api/health

curl -s -X POST http://127.0.0.1:8000/api/simulate \
	-H 'Content-Type: application/json' \
	-d '{"scenario":"mixed","total_events":60,"benign_ratio":0.35,"window_seconds":2.0,"output_name":"smoke_alerts.csv"}'

curl -s -X POST http://127.0.0.1:8000/api/detect \
	-H 'Content-Type: application/json' \
	-d '{"scenario":"mixed","total_events":60,"benign_ratio":0.35,"window_seconds":2.0}'
```

## Main endpoints
- `GET /api/health`: API liveness.
- `GET /api/config`: runtime configuration and checkpoint presence.
- `POST /api/simulate`: generate simulated alert CSV.
- `POST /api/detect`: run preprocess + FT inference from alert CSV or ad-hoc simulation.
- `GET /api/sessions`: list in-memory recent sessions.
