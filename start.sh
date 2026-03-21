#!/bin/bash

# Start Ollama service in the background
ollama serve &

# Wait for Ollama API to be ready
echo "Waiting for Ollama to start..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

echo "Ollama started successfully."

# Pull the specific model
echo "Pulling llama3 model (this may take a while)..."
ollama pull llama3

echo "Model pulled successfully."

# Start the python application
echo "Starting the Python application..."
python3 main.py
