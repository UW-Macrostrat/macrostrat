# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy your requirements (adjust if you use poetry or pipenv)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Expose the port uvicorn will run on
EXPOSE 8000

# Run the app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]