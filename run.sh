#!/bin/bash
# SmugMug Client Selection Tool Runner

echo "SmugMug Client Selection Tool"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "src/smugmug-client.py" ]; then
    echo "Error: Please run this script from the SmugMug-Client-Selection-Tool directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if dependencies are installed
if ! python3 -c "import requests, requests_oauthlib, dotenv" 2>/dev/null; then
    echo "Installing dependencies..."
    if [ -d "venv" ]; then
        pip install -r requirements.txt
    else
        echo "Virtual environment not found. Creating one..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    fi
fi

# Run the main script
python3 src/smugmug-client.py
