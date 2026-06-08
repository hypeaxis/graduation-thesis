# Session Log - 2026-05-30 (session-01)

## Goal
- Lock official direction to 122-feature pipeline.
- Clean remaining 41-feature leftovers from today's work.
- Track current training status for 122-feature FT experiments.

## Actions Completed
1. Verified current repository state and identified 41-feature leftovers created/modified today.
2. Removed 41-feature experiment script created during today session.
3. Restored 41-feature trainer file to committed version.
4. Removed related 41-feature Python cache artifacts.
5. Verified working tree is clean after cleanup.
6. Verified 122-feature FT experiment status from output folders.

## Files Cleaned Today
- Removed: MLAnomalyDetection/run_nslkdd_41emb_experiments.py
- Restored to HEAD: MLAnomalyDetection/train_tabular_transformer_41emb.py
- Removed cache:
  - MLAnomalyDetection/__pycache__/run_nslkdd_41emb_experiments.cpython-38.pyc
  - MLAnomalyDetection/__pycache__/train_tabular_transformer_41emb.cpython-38.pyc

## 122-Feature Experiment Status
Output root: MLAnomalyDetection/outputs/nslkdd_ft_experiments

- DONE: nslkdd_ft_baseline_seed42
- DONE: nslkdd_ft_sampler_weighted_seed42
- DONE: nslkdd_ft_sampler_weighted_seed52
- DONE: nslkdd_ft_sampler_weighted_seed62
- INCOMPLETE: nslkdd_ft_weighted_scalar025_seed42
- INCOMPLETE: nslkdd_ft_weighted_dropout02_seed42

## Current Commit Snapshot
- 60925e2 checkpoint: stop tuning and keep best current results

## Next Step
- Resume the 2 incomplete 122-feature runs to finalize the full 6-run experiment grid.
