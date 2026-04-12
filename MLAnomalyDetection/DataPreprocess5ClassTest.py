from preprocessing_pipeline import run_schema_sanity_checks, transform_test_with_preprocessor


def main():
    transform_test_with_preprocessor(
        test_txt_path='KDDTest+.txt',
        output_test_csv='cleaned5Grouped_v2_KddTest+.csv',
        artifacts_dir='artifacts_preprocess',
    )

    run_schema_sanity_checks(
        train_csv='cleaned5Grouped_v2_KddTrain+.csv',
        test_csv='cleaned5Grouped_v2_KddTest+.csv',
    )


if __name__ == '__main__':
    main()
