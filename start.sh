#!/bin/bash

# Start FastAPI backend
echo "Starting FastAPI backend..."
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit frontend
echo "Starting Streamlit frontend..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# Wait for background processes
wait
