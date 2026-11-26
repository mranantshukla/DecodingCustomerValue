# syntax=docker/dockerfile:1
# Container for the Streamlit dashboard (also runs the pipeline on first launch).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip && pip install -e ".[dashboard]"

# Copy the project.
COPY . .

# Build the analytics artefacts at image-build time so the app starts instantly.
RUN python -m src.pipeline

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "src/dashboard/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
