# Build native dependencies (pyswisseph) in a dedicated compiler stage.
# Runtime does not contain gcc, package manager metadata, or build tools.
FROM python:3.12-slim AS wheel-builder
WORKDIR /build
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
WORKDIR /opt/xuanshu
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=wheel-builder /wheels /wheels
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
COPY app ./app
COPY static ./static
COPY skills ./skills
COPY docs ./docs
COPY LICENSE README.md pyproject.toml ./
RUN addgroup --system xuanshu \
    && adduser --system --ingroup xuanshu xuanshu \
    && chown -R xuanshu:xuanshu /opt/xuanshu
USER xuanshu
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
