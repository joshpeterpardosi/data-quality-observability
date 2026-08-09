FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (its own layer) so code edits don't force a reinstall.
COPY pyproject.toml ./
RUN pip install --no-cache-dir "pandas>=2.2" "duckdb>=1.0" "pandera>=0.20" "streamlit>=1.38" "plotly>=5.24"

COPY . .
RUN chmod +x docker/entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["docker/entrypoint.sh"]
