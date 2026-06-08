from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Run NSL-KDD FT-Transformer experiment grid.')
    parser.add_argument(
        '--output-root',
        type=Path,
        default=None,
        help='Root directory to store run outputs.',
    )
    parser.add_argument(
        '--runs',
        nargs='*',
        default=None,
        help='Optional explicit run names. If omitted, all runs execute.',
    )
    parser.add_argument('--skip-existing', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument(
        '--extra-args',
        nargs=argparse.REMAINDER,
        default=[],
        help='Extra args forwarded to train_ft_transformer_nslkdd.py.',
    )
    return parser.parse_args()


def build_experiments():
    return [
        {
            'name': 'nslkdd_ft_baseline_seed42',
            'seed': 42,
            'params': {'sampler': 'none', 'focal-alpha': 'class-balanced'},
        },
        {
            'name': 'nslkdd_ft_sampler_weighted_seed42',
            'seed': 42,
            'params': {'sampler': 'weighted', 'focal-alpha': 'class-balanced'},
        },
        {
            'name': 'nslkdd_ft_sampler_weighted_seed52',
            'seed': 52,
            'params': {'sampler': 'weighted', 'focal-alpha': 'class-balanced'},
        },
        {
            'name': 'nslkdd_ft_sampler_weighted_seed62',
            'seed': 62,
            'params': {'sampler': 'weighted', 'focal-alpha': 'class-balanced'},
        },
        {
            'name': 'nslkdd_ft_weighted_scalar025_seed42',
            'seed': 42,
            'params': {'sampler': 'weighted', 'focal-alpha': '0.25'},
        },
        {
            'name': 'nslkdd_ft_weighted_dropout02_seed42',
            'seed': 42,
            'params': {'sampler': 'weighted', 'focal-alpha': 'class-balanced', 'dropout': '0.2'},
        },
        {
            'name': 'nslkdd_ft_overfit_guard_seed42',
            'seed': 42,
            'params': {
                'sampler': 'weighted',
                'focal-alpha': 'class-balanced',
                'mixup-alpha': '0.2',
                'selection-gap-penalty': '0.3',
                'max-train-val-gap': '0.12',
                'gap-patience': '3',
            },
        },
        {
            'name': 'nslkdd_ft_overfit_guard_seed62',
            'seed': 62,
            'params': {
                'sampler': 'weighted',
                'focal-alpha': 'class-balanced',
                'mixup-alpha': '0.2',
                'selection-gap-penalty': '0.3',
                'max-train-val-gap': '0.12',
                'gap-patience': '3',
            },
        },
    ]


def build_command(train_script: Path, run_root: Path, run: dict, extra_args: list[str]):
    save_dir = run_root / 'models'
    results_dir = run_root / 'results'
    command = [
        sys.executable,
        '-u',
        str(train_script),
        '--seed', str(run['seed']),
        '--epochs', '20',
        '--patience', '6',
        '--save-dir', str(save_dir),
        '--results-dir', str(results_dir),
    ]

    for key, value in run['params'].items():
        command.extend([f'--{key}', str(value)])

    command.extend(extra_args)
    return command, results_dir / 'training_summary.csv'


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    train_script = base_dir / 'train_ft_transformer_nslkdd.py'

    output_root = args.output_root or (base_dir / 'outputs' / 'nslkdd_ft_experiments')
    output_root.mkdir(parents=True, exist_ok=True)

    experiments = build_experiments()
    if args.runs:
        requested = set(args.runs)
        experiments = [item for item in experiments if item['name'] in requested]

    if not experiments:
        raise SystemExit('No experiments selected.')

    for run in experiments:
        run_root = output_root / run['name']
        command, summary_path = build_command(train_script, run_root, run, args.extra_args)
        log_path = run_root / f"{run['name']}.log"

        if args.skip_existing and summary_path.exists():
            print(f'[skip] {run["name"]} -> {summary_path}')
            continue

        print(f'\n=== {run["name"]} ===')
        print(' '.join(command))
        print(f'log: {log_path}')

        if args.dry_run:
            continue

        run_root.mkdir(parents=True, exist_ok=True)
        with log_path.open('w', encoding='utf-8') as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end='')
                log_file.write(line)
                log_file.flush()
            return_code = process.wait()

        if return_code != 0:
            raise SystemExit(f'Run failed: {run["name"]} (exit {return_code})')

    print('\nAll selected experiments finished.')


if __name__ == '__main__':
    main()
