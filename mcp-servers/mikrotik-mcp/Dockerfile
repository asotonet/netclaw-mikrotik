FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Default command: run with devices.json
CMD ["python", "mikrotik_mcp_server.py", "-f", "devices.json"]
