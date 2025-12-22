#!/bin/bash

# Start the Elite Armory website

echo "Starting Elite Armory website..."
echo "Server will be available at http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
python3 server.py