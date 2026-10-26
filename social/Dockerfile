FROM python:3.12-slim

# Pango for WeasyPrint (PDF), fonts with Cyrillic.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    fonts-liberation2 fonts-dejavu-core curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# MAX's API certificate is issued by the Russian Trusted Root CA (Минцифры).
RUN mkdir -p /app/certs && ( \
    curl -fsSL https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt; echo; \
    curl -fsSL https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt \
  ) > /app/certs/russian_trusted_ca.pem || echo "Russian CA not downloaded: MAX will be unavailable"

COPY app ./app
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD curl -fs http://127.0.0.1:8000/healthz || exit 1
# One worker: the collector runs inside the app process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
