from pathlib import Path

from preprocessing_pipeline import fit_train_preprocessor


def main():
    data_dir = Path(__file__).resolve().parent

    fit_train_preprocessor(
        train_txt_path=str(data_dir / 'KDDTrain+.txt'),
        output_train_csv=str(data_dir / 'cleaned5Grouped_v2_KddTrain+.csv'),
        artifacts_dir=str(data_dir / 'artifacts_preprocess'),
    )


if __name__ == '__main__':
    main()
