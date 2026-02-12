FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for face_recognition
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p temp/uploads temp/processed temp/faces instance models

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "main.py"]