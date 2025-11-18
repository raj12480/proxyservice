# Use an official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

ENV PYTHONUNBUFFERED=1


# Copy the requirements file first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Make startup script executable
RUN chmod +x start-server.sh

# Expose the port used by Gunicorn
EXPOSE 5000

# Run the startup script
ENTRYPOINT ["./start-server.sh"]
