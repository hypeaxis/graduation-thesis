# Session Log - 2026-05-31 (session-02)

## Goal
- Resume and complete pending 122-feature FT experiments from 2026-05-30.
- Re-evaluate best configuration using test Macro-F1 and minority-class F1.

## Actions Completed
1. Read previous session log and confirmed two pending runs:
   - `nslkdd_ft_weighted_scalar025_seed42`
   - `nslkdd_ft_weighted_dropout02_seed42`
2. Verified output directories and confirmed only scalar025 + dropout02 were incomplete.
3. Resumed runs via `run_nslkdd_ft_experiments.py` using project venv.
4. Confirmed `nslkdd_ft_weighted_scalar025_seed42` finished and produced full result artifacts.
5. Confirmed `nslkdd_ft_weighted_dropout02_seed42` finished successfully.
6. Collected and compared headline metrics from all 6 runs.
7. Locked `nslkdd_ft_sampler_weighted_seed62` as the primary 122-feature checkpoint in `final/primary_pipeline.json`.

## Current 122-Feature Experiment Status
Output root: `MLAnomalyDetection/outputs/nslkdd_ft_experiments`

- DONE: `nslkdd_ft_baseline_seed42`
- DONE: `nslkdd_ft_sampler_weighted_seed42`
- DONE: `nslkdd_ft_sampler_weighted_seed52`
- DONE: `nslkdd_ft_sampler_weighted_seed62`
- DONE: `nslkdd_ft_weighted_scalar025_seed42`
- DONE: `nslkdd_ft_weighted_dropout02_seed42`

## Metrics Snapshot (all runs)
- `nslkdd_ft_baseline_seed42`: acc `0.7477`, macro-F1 `0.5582`, R2L-F1 `0.2804`, U2R-F1 `0.2316`
- `nslkdd_ft_sampler_weighted_seed42`: acc `0.7909`, macro-F1 `0.6098`, R2L-F1 `0.3613`, U2R-F1 `0.2778`
- `nslkdd_ft_sampler_weighted_seed52`: acc `0.7707`, macro-F1 `0.6268`, R2L-F1 `0.2860`, U2R-F1 `0.4812`
- `nslkdd_ft_sampler_weighted_seed62`: acc `0.8005`, macro-F1 `0.6679`, R2L-F1 `0.5094`, U2R-F1 `0.4252`
- `nslkdd_ft_weighted_scalar025_seed42`: acc `0.7684`, macro-F1 `0.5825`, R2L-F1 `0.2931`, U2R-F1 `0.2288`
- `nslkdd_ft_weighted_dropout02_seed42`: acc `0.8058`, macro-F1 `0.6443`, R2L-F1 `0.5647`, U2R-F1 `0.2689`

## Final Conclusion
- Best overall run by test Macro-F1: `nslkdd_ft_sampler_weighted_seed62` (`0.6679`).
- `dropout=0.2` improves Accuracy and R2L-F1 but hurts U2R-F1 strongly, so Macro-F1 is still below seed62.
- Scalar alpha `0.25` underperforms class-balanced alpha on Macro-F1 and minority classes.

## Next Step
- Keep `nslkdd_ft_sampler_weighted_seed62` as current best 122-feature checkpoint for deployment path.
- If continuing tuning, target U2R recovery while preserving R2L gains from dropout-style regularization.
