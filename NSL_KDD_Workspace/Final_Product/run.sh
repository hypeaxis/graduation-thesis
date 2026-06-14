#!/bin/bash

echo "Starting IDS Final Product..."
echo "Setting up virtual environment..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install tensorflow==2.13.1
pip install -r requirements.txt

echo "Starting Backend API and Frontend..."
cd backend
chmod +x run_dev.sh
./run_dev.sh
