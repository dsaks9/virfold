FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt sqlalchemy psycopg2-binary

# Copy health check script
COPY health_check.py .

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8001

# Add health check
HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=3 \
    CMD python health_check.py

# Run the start script
CMD ["./start.sh"] 