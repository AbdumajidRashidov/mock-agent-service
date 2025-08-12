FROM python:3.12.3-slim

WORKDIR /app

# Install system dependencies together
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose ports for gRPC (50051) and HTTP health check (8081)
EXPOSE 50051 8081

# Run the application
CMD ["python", "src/main.py"]
