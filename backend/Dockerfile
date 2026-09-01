# backend/Dockerfile - multi-stage: build deps in one layer, keep the
# gcc/libpq-dev build toolchain out of the final runtime image.

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim AS runtime

WORKDIR /app

# ffmpeg is a runtime dependency (video rendering); libpq5 is psycopg2's
# runtime shared library - neither needs the gcc/libpq-dev build toolchain.
# fontconfig + fonts-dejavu-core give ffmpeg's `subtitles` filter (libass)
# a font for Latin text; fonts-noto-core adds coverage for the many other
# scripts (Tamil, Devanagari, Arabic, etc.) source videos may be
# transcribed in - DejaVu alone has zero glyphs outside Latin/Cyrillic/
# Greek, so a non-Latin transcript burns in as near-empty "tofu" boxes
# without this.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libpq5 fontconfig fonts-dejavu-core fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./app ./app
COPY alembic.ini .
COPY ./alembic ./alembic

RUN useradd -m appuser \
    # Pre-create the mount points for the uploads/downloads/renders named
    # volumes (docker-compose.yml) with correct ownership up front: Docker
    # initializes a brand-new named volume by copying whatever already
    # exists in the image at that path, so without this the volume would
    # be created root-owned and every write from the non-root `appuser`
    # process below would fail with "Permission denied".
    && mkdir -p /app/uploads /app/downloads /app/renders \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
