FROM python:3.11-slim

# Set metadata
LABEL maintainer="SSH Tunnel Auto-Tester Contributors"
LABEL description="Comprehensive SSH tunneling tool for restricted networks"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    stunnel4 \
    corkscrew \
    netcat-openbsd \
    curl \
    jq \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -s /bin/bash tunneluser && \
    chown -R tunneluser:tunneluser /app

# Switch to non-root user
USER tunneluser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["python", "tunnel_tester.py", "--help"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Entry point allows passing arguments
ENTRYPOINT ["python", "tunnel_tester.py"]
