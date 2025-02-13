-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create a sample time-series table for sensor data if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'sensor_data') THEN
        CREATE TABLE sensor_data (
            time        TIMESTAMPTZ NOT NULL,
            sensor_id   INTEGER,
            temperature DOUBLE PRECISION,
            humidity    DOUBLE PRECISION
        );

        -- Convert to TimescaleDB hypertable
        PERFORM create_hypertable('sensor_data', 'time');

        -- Insert a week's worth of sample data
        WITH time_series AS (
            SELECT ts as time
            FROM generate_series(
                NOW() - INTERVAL '7 days',
                NOW(),
                INTERVAL '5 minutes'
            ) as ts
        ),
        sensor_series AS (
            SELECT generate_series(1, 3) as sensor_id
        )
        INSERT INTO sensor_data (time, sensor_id, temperature, humidity)
        SELECT
            t.time,
            s.sensor_id,
            -- More realistic temperature variations using sine wave pattern
            25 + 5 * sin((EXTRACT(EPOCH FROM t.time) / 3600)::numeric * (2*pi()/24)) + (random() * 2 - 1) as temperature,
            -- More realistic humidity variations
            65 + 15 * sin((EXTRACT(EPOCH FROM t.time) / 3600)::numeric * (2*pi()/24)) + (random() * 5 - 2.5) as humidity
        FROM time_series t
        CROSS JOIN sensor_series s;

        -- Create an index on sensor_id for faster queries
        CREATE INDEX ON sensor_data (sensor_id, time DESC);
    END IF;
END $$;

-- Ensure permissions are granted (this is safe to run multiple times)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tsuser; 