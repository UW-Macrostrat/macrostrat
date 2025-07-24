# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (to leverage Docker cache)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app’s code
COPY . .

# Expose port 8000
EXPOSE 8000

# Command to run your app — change this to your actual run command
CMD ["python", "app.py"]