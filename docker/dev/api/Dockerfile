FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt sqlalchemy psycopg2-binary

# Create necessary directories
RUN mkdir -p routers /app/cache

# Copy health check script
COPY health_check.py .

# Copy application code
COPY main.py .
COPY routers/ routers/

# Add app directory to Python path
ENV PYTHONPATH=/app:/app/cache

# Expose port
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=3 \
    CMD python health_check.py

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 