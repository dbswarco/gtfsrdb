# GTFSrDB container image
#
# Build context must be the repository root, e.g.:
#   docker build -f docker/Dockerfile -t gtfsrdb:latest .
# (or use docker/docker-build.sh)
#
# Arguments passed to `docker run <image> ...` are forwarded to gtfsrdb.py,
# e.g. --database=... -t <url> -p <url> -c -v

FROM python:3.12-slim

ARG VERSION=latest
LABEL org.opencontainers.image.title="gtfsrdb" \
      org.opencontainers.image.description="GTFSrDB loads GTFS-realtime data to a database." \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime dependencies (mirrors pyproject.toml)
RUN pip install \
        "sqlalchemy" \
        "protobuf~=5.28.3" \
        "psycopg2-binary~=2.9.13"

# gtfsrdb.py uses flat (non-package) imports, so run it from its own directory
WORKDIR /app
COPY src/gtfsrdb/*.py /app/

# Run as an unprivileged user; /data is the working dir for any output files
# (e.g. print_positions.csv written by --print-positions)
RUN useradd --create-home --uid 1000 gtfsrdb \
    && mkdir -p /data \
    && chown gtfsrdb:gtfsrdb /data
USER gtfsrdb
WORKDIR /data

ENTRYPOINT ["python", "/app/gtfsrdb.py"]
CMD ["--help"]
