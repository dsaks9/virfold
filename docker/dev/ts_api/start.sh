#!/bin/bash

# Start the data generator in the background
python data_generator.py &

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port 8001 --reload 