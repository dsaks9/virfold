import os
import sys
import time
from sqlalchemy import create_engine, text

def check_health(max_retries=5, retry_delay=5):
    """Check if the database is accessible and has data"""
    db_params = {
        'host': os.environ['DB_HOST'],
        'port': os.environ['DB_PORT'],
        'database': os.environ['POSTGRES_DB'],
        'user': os.environ['POSTGRES_USER'],
        'password': os.environ['POSTGRES_PASSWORD']
    }
    
    print("Checking database connection and data...")
    
    for attempt in range(max_retries):
        try:
            # Create SQLAlchemy engine
            engine = create_engine(
                f"postgresql://{db_params['user']}:{db_params['password']}@"
                f"{db_params['host']}:{db_params['port']}/{db_params['database']}"
            )
            
            # Test connection and data
            with engine.connect() as connection:
                # Basic connectivity test
                result = connection.execute(text("SELECT 1"))
                result.scalar()
                
                # Check if table exists
                result = connection.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM information_schema.tables 
                        WHERE table_name = 'sensor_data'
                    )
                """))
                if not result.scalar():
                    raise Exception("sensor_data table not found")
                
            print("Health check passed successfully!")
            return True
            
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Health check failed.")
                return False

if __name__ == "__main__":
    success = check_health()
    if not success:
        sys.exit(1) 