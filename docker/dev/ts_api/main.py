from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg2
from datetime import datetime, timedelta
import os
import logging
from typing import Optional, List, Dict
from pydantic import BaseModel

# Set up logging with more detailed information
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Time Series API",
    description="API for time series data from sensors",
    version="1.0.0"
)

# Configure CORS with specific origins and detailed logging
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://ec2-54-206-50-237.ap-southeast-2.compute.amazonaws.com:3000",
        "*",  # Temporarily allow all origins for debugging
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise

def get_db_connection():
    """Create a connection to the database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        logger.info("Database connection successful")
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

class SensorData(BaseModel):
    time: str
    temperature: float
    humidity: float

class SensorResponse(BaseModel):
    sensor_id: int
    data: List[SensorData]

@app.get("/sensors", response_model=List[int])
async def list_sensors():
    """Get a list of all sensor IDs."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT sensor_id FROM sensor_data ORDER BY sensor_id;")
                sensors = [row[0] for row in cur.fetchall()]
                return sensors
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensors/data", response_model=Dict[str, List[SensorData]])
async def get_sensor_data(
    hours: Optional[int] = 24,
    interval: Optional[str] = '1 hour'
):
    """
    Get sensor data for all sensors.
    - hours: Number of hours of data to return (default 24)
    - interval: Time bucket interval for aggregation (default '1 hour')
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    WITH buckets AS (
                        SELECT 
                            sensor_id,
                            time_bucket(%s, time) AS bucket,
                            AVG(temperature) as avg_temp,
                            AVG(humidity) as avg_humidity
                        FROM sensor_data
                        WHERE time >= NOW() - INTERVAL %s
                        GROUP BY sensor_id, bucket
                        ORDER BY bucket ASC
                    )
                    SELECT 
                        sensor_id,
                        bucket as time,
                        avg_temp,
                        avg_humidity
                    FROM buckets
                    ORDER BY bucket ASC;
                """
                cur.execute(query, (interval, f'{hours} hours'))
                rows = cur.fetchall()

                # Process the data into the format needed by the charts
                sensor_data: Dict[str, List[SensorData]] = {}
                for row in rows:
                    sensor_id, time, temp, humidity = row
                    sensor_key = f"sensor{sensor_id}"
                    
                    if sensor_key not in sensor_data:
                        sensor_data[sensor_key] = []
                    
                    sensor_data[sensor_key].append(SensorData(
                        time=time.strftime("%H:%M"),
                        temperature=float(temp),
                        humidity=float(humidity)
                    ))

                return sensor_data

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensors/{sensor_id}/data", response_model=List[SensorData])
async def get_single_sensor_data(
    sensor_id: int,
    hours: Optional[int] = 24,
    interval: Optional[str] = '1 hour'
):
    """
    Get data for a specific sensor.
    - sensor_id: ID of the sensor
    - hours: Number of hours of data to return (default 24)
    - interval: Time bucket interval for aggregation (default '1 hour')
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        time_bucket(%s, time) AS bucket,
                        AVG(temperature) as avg_temp,
                        AVG(humidity) as avg_humidity
                    FROM sensor_data
                    WHERE 
                        sensor_id = %s AND
                        time >= NOW() - INTERVAL %s
                    GROUP BY bucket
                    ORDER BY bucket ASC;
                """
                cur.execute(query, (interval, sensor_id, f'{hours} hours'))
                rows = cur.fetchall()

                return [
                    SensorData(
                        time=time.strftime("%H:%M"),
                        temperature=float(temp),
                        humidity=float(humidity)
                    )
                    for time, temp, humidity in rows
                ]

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"} 