# Model Package: FT122 Seed62 Best Epoch19

## Package Summary
- Pipeline: 122-feature FT-Transformer
- Run ID: nslkdd_ft_sampler_weighted_seed62
- Checkpoint: best_model.pt
- Best epoch: 19
- Packaged at: 2026-06-02

## Key Metrics
- best_val_macro_f1: 0.754424549657926
- test_accuracy: 0.8005057226510514
- test_macro_f1: 0.667941788896857
- test_weighted_f1: 0.7932070500673704
- test_macro_precision: 0.7009864630657903
- test_macro_recall: 0.6540225683348279

## Included Content
- models/: checkpoint + inference_config
- results/: training summary + report + confusion matrix
- artifacts/: feature schema + scaler + label mapping
- pipeline/: snapshot of primary_pipeline.json
- scripts/: snort preprocess + inference scripts
- checksums.sha256: integrity list for all files

## Verify Integrity
Run from this package folder:

sha256sum -c checksums.sha256

## Inference Quick Start
From project root:

source .venv/bin/activate
python final/snort_ft_transformer_inference.py \
  --checkpoint MLAnomalyDetection/outputs/nslkdd_ft_experiments/nslkdd_ft_sampler_weighted_seed62/models/best_model.pt \
  --inference-config MLAnomalyDetection/outputs/nslkdd_ft_experiments/nslkdd_ft_sampler_weighted_seed62/models/inference_config.json \
  --input-features final/snort_features_122.csv \
  --output final/snort_ft_transformer_predictions.csv
