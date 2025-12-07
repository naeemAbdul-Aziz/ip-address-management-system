FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (for building psycopg2)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Command is overridden by docker-compose, but good to have a default
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
