-- Create a sample time-series table for sensor data
CREATE TABLE sensor_data (
    time        TIMESTAMPTZ NOT NULL,
    sensor_id   INTEGER,
    temperature DOUBLE PRECISION,
    humidity    DOUBLE PRECISION
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('sensor_data', 'time');

-- Insert some sample data
INSERT INTO sensor_data (time, sensor_id, temperature, humidity)
SELECT
    generate_series(
        NOW() - INTERVAL '24 hours',
        NOW(),
        INTERVAL '1 hour'
    ) as time,
    sensor_id,
    20 + random() * 10 as temperature,  -- Random temperature between 20-30°C
    50 + random() * 30 as humidity      -- Random humidity between 50-80%
FROM generate_series(1, 3) as sensor_id;

-- Create an index on sensor_id for faster queries
CREATE INDEX ON sensor_data (sensor_id, time DESC);

-- Grant permissions to our user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tsuser; 