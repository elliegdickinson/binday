FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Chromium for the ~90 councils UKBinCollectionData drives through Selenium.
# chromium-driver comes from the same Debian release, so browser and driver
# versions always match - no runtime download, no version drift.
# Selenium looks for google-chrome; Debian ships chromium, hence the symlink.
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-liberation \
        ca-certificates \
    && ln -sf /usr/bin/chromium /usr/bin/google-chrome \
    && rm -rf /var/lib/apt/lists/*

ENV CHROMEDRIVER=/usr/bin/chromedriver \
    CHROME_BIN=/usr/bin/chromium

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

EXPOSE 8080
# One worker: the cache is in-process, and Chrome is memory-hungry enough that
# a second worker would fight this one for RAM rather than add throughput.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
