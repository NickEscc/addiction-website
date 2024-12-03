# Use Python base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the project into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default command to run (overridden by docker-compose)
CMD ["python", "manage.py", "runserver"]
