FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies globally
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libffi-dev \
    libssl-dev \
    sqlite3 \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python site-packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create necessary directories first
RUN mkdir -p /data/roms /app/instance \
    && chmod -R 755 /data /app/instance

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /data
USER appuser

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Copy only necessary application files (exclude large data directories)
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser requirements.txt .
COPY --chown=appuser:appuser extensions.py .
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser models/ ./models/
COPY --chown=appuser:appuser routes/ ./routes/
COPY --chown=appuser:appuser services/ ./services/
COPY --chown=appuser:appuser static/ ./static/
COPY --chown=appuser:appuser templates/ ./templates/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser docker-entrypoint.sh .

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]