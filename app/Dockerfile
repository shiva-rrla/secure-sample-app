# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Secure Sample Application – Hardened Container Image
# ---------------------------------------------------------------------------

# --- Stage 1: Builder ------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies (if any native wheels are needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a local user directory
COPY requirements.txt .
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# --- Stage 2: Runtime ------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Remove setuid/setgid binaries to reduce attack surface
RUN find / -perm /6000 -type f -exec chmod a-s {} \; 2>/dev/null || true

# Create nonroot user/group (65532:65532)
RUN groupadd --gid 65532 nonroot && \
    useradd --uid 65532 --gid nonroot --shell /usr/sbin/nologin \
        --home-dir ${APP_HOME} --create-home nonroot

# Copy only the installed packages from builder
COPY --from=builder /root/.local /home/nonroot/.local
COPY main.py ${APP_HOME}/

# Ensure file ownership and permissions
RUN chown -R nonroot:nonroot /home/nonroot/.local ${APP_HOME} && \
    chmod -R 555 ${APP_HOME} && \
    chmod 644 ${APP_HOME}/main.py

ENV PATH=/home/nonroot/.local/bin:${PATH}

# Run as nonroot
USER nonroot:nonroot

EXPOSE 8080

# Healthcheck (kubelet will also use the /healthz endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" \
    || exit 1

ENTRYPOINT ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
