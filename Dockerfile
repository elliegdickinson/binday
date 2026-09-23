FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

EXPOSE 8080
# One worker: the cache is in-process, so extra workers would just multiply
# requests to council sites for no benefit at this size.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
