#!/bin/bash
set -e

# Run the database health check
echo "Running database health check..."
python /app/db_health_check.py

# Keep the container running
tail -f /dev/null