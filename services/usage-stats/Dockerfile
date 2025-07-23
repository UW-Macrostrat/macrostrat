# Use an official Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy your code into the container
COPY . .

# Install dependencies if requirements.txt exists
RUN pip install --no-cache-dir -r requirements.txt || true

# Run the script
CMD ["python", "get-data.py"]
