#!/bin/bash
set -e

echo "Waiting for database to be fully ready..."
sleep 30  # Give the database plenty of time to initialize

echo "Running health check..."
if ! python /app/db_health_check.py; then
    echo "Health check failed - exiting"
    exit 1
fi

echo "Health check passed - keeping container running"
exec tail -f /dev/null