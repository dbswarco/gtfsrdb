# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy project files (paths relative to build context root)
COPY pyproject.toml LICENSE ./
COPY src/ ./src/

# Install the package and its dependencies
RUN pip install --upgrade pip && \
    pip install .

# Create a non-root user to run the application
RUN useradd -m -u 1000 gtfsrdb && \
    chown -R gtfsrdb:gtfsrdb /app

# Switch to non-root user
USER gtfsrdb

# Set the entrypoint to the gtfsrdb command
ENTRYPOINT ["gtfsrdb"]

# Default command shows help
CMD ["--help"]
