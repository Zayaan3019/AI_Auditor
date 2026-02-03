FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y build-essential git curl && rm -rf /var/lib/apt/lists/*
WORKDIR /src

# Install poetry and project dependencies in the builder stage
COPY pyproject.toml poetry.lock* /src/
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

FROM python:3.11-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . /app

ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
