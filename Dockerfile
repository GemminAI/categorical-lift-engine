# Categorical Lift Engine (CLE) -- Runtime Boundary only.
#
# Exposes the existing, unmodified `cle.api.app:app` FastAPI application
# over HTTP. No Grounding, Categorical Lift, or API contract code is
# touched by this file -- it only builds the existing package and runs it
# with uvicorn.
#
# Container listens on 0.0.0.0:8000 internally, matching CLE's own
# measured GCP deployment (independent of NVS-Kernel, which is a
# separate service on its own :8100 -- this file does not touch that
# port or that service).

# ---------- stage 1: build ----------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip setuptools wheel \
    && pip install .

# ---------- stage 2: runtime ----------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Categorical Lift Engine" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.description="Semantic Grounding + Categorical Lift, exposed over HTTP (unmodified engine)" \
      org.opencontainers.image.licenses="Proprietary"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0

RUN groupadd --gid 10001 cle \
    && useradd --uid 10001 --gid cle --no-create-home --shell /usr/sbin/nologin cle

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200 else 1)"]

CMD ["python", "-m", "uvicorn", "cle.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
