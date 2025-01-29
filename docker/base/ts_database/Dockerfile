# Use the official TimescaleDB image
FROM timescale/timescaledb:latest-pg14

# Copy initialization scripts
COPY ./init.sql /docker-entrypoint-initdb.d/

# Expose the PostgreSQL port
EXPOSE 5432 