from pathlib import Path

from preprocessing_pipeline_41emb import fit_train_preprocessor_41emb


def main() -> None:
    data_dir = Path(__file__).resolve().parent

    fit_train_preprocessor_41emb(
        train_txt_path=str(data_dir / 'KDDTrain+.txt'),
        output_train_csv=str(data_dir / 'cleaned41emb_KddTrain+.csv'),
        artifacts_dir=str(data_dir / 'artifacts_preprocess_41emb'),
    )


if __name__ == '__main__':
    main()