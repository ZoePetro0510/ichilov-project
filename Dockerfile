# One image for both the API and the Streamlit UI (docker-compose picks the command).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

# DejaVu has Hebrew glyphs: scripts/make_sample_corpus.py needs it to draw the sample PDFs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch first, so sentence-transformers doesn't pull the multi-GB CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# Run as a non-root user. Switching before the model download (instead of a later
# chown -R) avoids duplicating the ~500 MB model cache in a second layer.
RUN useradd --create-home appuser && chown appuser /app
USER appuser

# Bake the embedding model into the image so the first request doesn't download it.
ARG EMBEDDING_MODEL=intfloat/multilingual-e5-small
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"
# The model is in the image: don't call the Hugging Face Hub at runtime.
ENV HF_HUB_OFFLINE=1

COPY --chown=appuser . .

EXPOSE 8000 8501
CMD ["sh", "docker/start-api.sh"]
