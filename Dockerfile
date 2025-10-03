FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY test_api.py .

# Create directories for certificates and ensure proper permissions
RUN mkdir -p /app/ca /app/crts /app/private /app/clients /app/requests && \
    chmod 755 /app/ca /app/crts /app/private /app/clients /app/requests

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/', timeout=2)" || exit 1

# Run the application
CMD ["python", "main.py"]