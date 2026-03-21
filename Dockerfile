# Use an official lightweight Ubuntu image
FROM ubuntu:22.04

# Prevent interactive prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies, Python, and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set the working directory
WORKDIR /app

# Copy python dependencies
COPY requirements.txt .

# Install Python requirements
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure the start script is executable
RUN chmod +x start.sh

# Because we are running a persistent application, define the entrypoint or CMD
CMD ["./start.sh"]
