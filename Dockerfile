# Use a slim Python image for minimal overhead
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some Python libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure the start script is executable
RUN chmod +x start.sh

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000
EXPOSE 8501

# Set environment variables (placeholders - user should provide real values in GCP)
ENV PYTHONUNBUFFERED=1

# Run the start script
CMD ["./start.sh"]
