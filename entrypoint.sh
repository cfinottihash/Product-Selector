#!/bin/bash

# Fallback: If PORT is missing, default to 8080
PORT="${PORT:-8080}"

echo "Starting Streamlit on port $PORT..."

# Run the app using the detected port
streamlit run app/product_selector_app.py --server.port=$PORT --server.address=0.0.0.0