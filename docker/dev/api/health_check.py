import os
import sys
import time
from sqlalchemy import create_engine, text

def check_health(max_retries=5, retry_delay=5):
    """Check if the database and dependencies are accessible"""
    db_params = {
        'host': os.environ['DB_HOST'],
        'port': os.environ['DB_PORT'],
        'database': os.environ['DB_NAME'],
        'user': os.environ['DB_USER'],
        'password': os.environ['DB_PASSWORD']
    }
    
    print("Checking database connection...")
    
    for attempt in range(max_retries):
        try:
            # Create SQLAlchemy engine
            engine = create_engine(
                f"postgresql://{db_params['user']}:{db_params['password']}@"
                f"{db_params['host']}:{db_params['port']}/{db_params['database']}"
            )
            
            # Test basic database connectivity
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.scalar()
            
            # Check if required environment variables are set
            required_vars = ['ANTHROPIC_API_KEY', 'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
            missing_vars = [var for var in required_vars if not os.environ.get(var)]
            if missing_vars:
                raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            # Check if required directories exist
            if not os.path.exists('/app/cache'):
                raise Exception("Cache directory not found")
            
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