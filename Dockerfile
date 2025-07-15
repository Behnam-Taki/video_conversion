# Use official Python image as base
FROM python:3.12-slim

# Install ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of app
COPY . .

# Run FastAPI with Uvicorn on port 8080 (needed for Railway)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
