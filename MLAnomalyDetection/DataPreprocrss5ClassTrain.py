from preprocessing_pipeline import fit_train_preprocessor


def main():
    fit_train_preprocessor(
        train_txt_path='KDDTrain+.txt',
        output_train_csv='cleaned5Grouped_v2_KddTrain+.csv',
        artifacts_dir='artifacts_preprocess',
    )


if __name__ == '__main__':
    main()
