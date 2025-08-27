# Use an official Python runtime as a parent image
FROM python:alpine

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY src/ src/

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["uvicorn", "saunafs_monitoring.main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8000"]
