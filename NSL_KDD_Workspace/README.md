# NSL-KDD Intrusion Detection Workspace

This workspace contains the final, deployment-ready product for detecting network anomalies using the NSL-KDD dataset.

## Directory Structure

*   `Final_Product/`: Contains the complete end-to-end deployable system.
    *   `backend/`: FastAPI backend server.
    *   `frontend/`: React-based cyber-dashboard.
    *   `inference/`: Real-time streaming inference using sliding windows.
*   `data/`: Data storage.
    *   `raw/`: Raw NSL-KDD text files (`KDDTrain+.txt`, `KDDTest+.txt`).
    *   `processed/`: Cleaned and grouped CSV files.
*   `src/`: The research and training source code.
    *   `data_processing/`: Feature selection and preprocessing pipelines.
    *   `models/`: FT-Transformer model definition for NSL-KDD.
    *   `training/`: Scripts to train the FT-Transformer model.
*   `models/`: Saved model weights, preprocessing scalers, and selected features.
*   `docs/`: Markdown documentation and planning notes.
*   `archive/`: Legacy Autoencoder, Transformer, and 5-class classification scripts kept for historical reference.

## Usage

1.  To run the production deployment, navigate to `Final_Product/` and execute `./run.sh`.
2.  To train the model from scratch, ensure data is in `data/raw/` and run `python src/training/train_improved.py`.
