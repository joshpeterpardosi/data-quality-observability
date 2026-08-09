#!/usr/bin/env sh
set -e

if [ ! -f data/raw/customers.csv ]; then
    echo "No source data found, generating synthetic CSVs..."
    python scripts/generate_synthetic_data.py
fi

echo "Loading raw data..."
python -m src.ingestion.load_raw

echo "Running validation + curation..."
python -m src.validation.runner

echo "Starting dashboard on :8501..."
exec streamlit run dashboard/app.py --server.address=0.0.0.0 --server.port=8501
