from pathlib import Path

from preprocessing_pipeline_41emb import run_schema_sanity_checks_41emb, transform_test_with_preprocessor_41emb


def main() -> None:
    data_dir = Path(__file__).resolve().parent

    transform_test_with_preprocessor_41emb(
        test_txt_path=str(data_dir / 'KDDTest+.txt'),
        output_test_csv=str(data_dir / 'cleaned41emb_KddTest+.csv'),
        artifacts_dir=str(data_dir / 'artifacts_preprocess_41emb'),
    )

    run_schema_sanity_checks_41emb(
        train_csv=str(data_dir / 'cleaned41emb_KddTrain+.csv'),
        test_csv=str(data_dir / 'cleaned41emb_KddTest+.csv'),
    )


if __name__ == '__main__':
    main()