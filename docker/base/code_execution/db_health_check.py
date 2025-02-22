import pandas as pd
from sqlalchemy import create_engine, text
import os
import time
import sys

def test_db_connection(max_retries=5, retry_delay=5):
    """Test basic connection to the TimescaleDB database"""
    
    # Create database connection parameters
    db_params = {
        'host': os.environ['DB_HOST'],
        'port': os.environ['DB_PORT'],
        'database': os.environ['DB_NAME'],
        'user': os.environ['DB_USER'],
        'password': os.environ['DB_PASSWORD']
    }
    
    print("Attempting to connect to database...")
    
    for attempt in range(max_retries):
        try:
            # Create SQLAlchemy engine
            engine = create_engine(
                f"postgresql://{db_params['user']}:{db_params['password']}@"
                f"{db_params['host']}:{db_params['port']}/{db_params['database']}"
            )
            
            # Just test basic connectivity
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.scalar()
                print("Database connection successful!")
                return True
            
        except Exception as e:
            print(f"\nAttempt {attempt + 1}/{max_retries} failed:")
            print(f"Error: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Database connection failed.")
                return False

if __name__ == "__main__":
    success = test_db_connection()
    if not success:
        sys.exit(1)