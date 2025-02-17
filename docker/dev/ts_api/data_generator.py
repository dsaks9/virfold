import psycopg2
import os
from datetime import datetime, timedelta
import time
import math
import random
import logging
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a connection to the database."""
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def generate_sensor_reading(timestamp):
    """Generate realistic sensor readings based on time of day."""
    hour = timestamp.hour
    # Temperature varies between 20-30°C with daily pattern
    temp_base = 25  # Base temperature
    temp_amplitude = 5  # Temperature variation
    temp = temp_base + temp_amplitude * math.sin((hour / 24) * 2 * math.pi)
    temp += random.uniform(-1, 1)  # Add some noise
    
    # Humidity varies between 50-80% with daily pattern
    humidity_base = 65  # Base humidity
    humidity_amplitude = 15  # Humidity variation
    humidity = humidity_base + humidity_amplitude * math.sin((hour / 24) * 2 * math.pi)
    humidity += random.uniform(-2.5, 2.5)  # Add some noise
    
    return temp, humidity

def cleanup_old_data(conn, cutoff_date):
    """Remove data older than the cutoff date."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM sensor_data WHERE time < %s", (cutoff_date,))
        deleted_count = cur.rowcount
        conn.commit()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old records")

def insert_new_data(conn, start_time, end_time):
    """Insert new sensor readings for the specified time period."""
    with conn.cursor() as cur:
        current_time = start_time
        while current_time <= end_time:
            for sensor_id in range(1, 4):  # 3 sensors
                temp, humidity = generate_sensor_reading(current_time)
                cur.execute(
                    "INSERT INTO sensor_data (time, sensor_id, temperature, humidity) VALUES (%s, %s, %s, %s)",
                    (current_time, sensor_id, temp, humidity)
                )
            current_time += timedelta(minutes=5)  # 5-minute intervals
        conn.commit()
        logger.info(f"Inserted new data from {start_time} to {end_time}")

def main():
    """Main function to run the data generation process."""
    while True:
        try:
            with get_db_connection() as conn:
                # Find the most recent data point
                with conn.cursor() as cur:
                    cur.execute("SELECT MAX(time) FROM sensor_data")
                    last_time = cur.fetchone()[0]
                
                # Use UTC for all datetime operations
                now = datetime.now(pytz.UTC)
                cutoff_date = now - timedelta(days=7)
                
                # Clean up old data
                cleanup_old_data(conn, cutoff_date)
                
                # If no data exists or last data point is old, generate last 7 days of data
                if last_time is None:
                    insert_new_data(conn, cutoff_date, now)
                elif (now - last_time) > timedelta(minutes=5):
                    # Generate data from last recorded time to now
                    insert_new_data(conn, last_time + timedelta(minutes=5), now)
                
        except Exception as e:
            logger.error(f"Error in data generation: {str(e)}")
        
        # Wait for 5 minutes before next iteration
        time.sleep(300)

if __name__ == "__main__":
    main() 