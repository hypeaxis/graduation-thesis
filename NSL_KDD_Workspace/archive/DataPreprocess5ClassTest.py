from pathlib import Path

from preprocessing_pipeline import run_schema_sanity_checks, transform_test_with_preprocessor


def main():
    data_dir = Path(__file__).resolve().parent

    transform_test_with_preprocessor(
        test_txt_path=str(data_dir / 'KDDTest+.txt'),
        output_test_csv=str(data_dir / 'cleaned5Grouped_v2_KddTest+.csv'),
        artifacts_dir=str(data_dir / 'artifacts_preprocess'),
    )

    run_schema_sanity_checks(
        train_csv=str(data_dir / 'cleaned5Grouped_v2_KddTrain+.csv'),
        test_csv=str(data_dir / 'cleaned5Grouped_v2_KddTest+.csv'),
    )


if __name__ == '__main__':
    main()
