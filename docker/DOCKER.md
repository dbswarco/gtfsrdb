# Docker Usage Guide for GTFSrDB

This guide explains how to build and run GTFSrDB using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for running with PostgreSQL)

## Building the Docker Image

### From Project Root

Build the image from the project root directory:

```bash
docker build -f docker/Dockerfile -t gtfsrdb:latest .
```

### From docker/ Directory

Or from within the `docker/` directory:

```bash
cd docker
docker build -f Dockerfile -t gtfsrdb:latest ..
```

## Running with Docker

### Basic Usage

Run a single query:

```bash
docker run --rm gtfsrdb:latest \
  --database=postgresql://user:password@host:5432/gtfs \
  --trip-updates=https://example.com/gtfs-rt/trip-updates \
  --once
```

### Continuous Monitoring

Run continuously with 30-second intervals:

```bash
docker run -d --name gtfsrdb \
  gtfsrdb:latest \
  --database=postgresql://user:password@host:5432/gtfs \
  --trip-updates=https://example.com/gtfs-rt/trip-updates \
  --vehicle-positions=https://example.com/gtfs-rt/vehicle-positions \
  --alerts=https://example.com/gtfs-rt/alerts \
  --wait=30 \
  --create-tables
```

### With API Key Header

If your GTFS-RT feed requires authentication:

```bash
docker run --rm gtfsrdb:latest \
  --database=postgresql://user:password@host:5432/gtfs \
  --trip-updates=https://example.com/gtfs-rt/trip-updates \
  --header='{"Authorization":"Bearer YOUR_API_KEY"}' \
  --once
```

Or with simple key:value format:

```bash
docker run --rm gtfsrdb:latest \
  --database=postgresql://user:password@host:5432/gtfs \
  --trip-updates=https://example.com/gtfs-rt/trip-updates \
  --header='X-API-Key:YOUR_API_KEY' \
  --once
```

### Saving Position Data to CSV

Mount a volume to save CSV output:

```bash
docker run --rm \
  -v $(pwd)/output:/app/data \
  gtfsrdb:latest \
  --database=postgresql://user:password@host:5432/gtfs \
  --vehicle-positions=https://example.com/gtfs-rt/vehicle-positions \
  --print-positions=ROUTE_ID,VEHICLE_ID \
  --once
```

## Using Docker Compose

The included `docker-compose.yml` provides a complete setup with PostgreSQL.

### Configuration

Edit `docker-compose.yml` to set:
- Your GTFS-RT feed URLs
- Database credentials
- Update interval (--wait parameter)
- API headers if needed

### Start Services

From the `docker/` directory:

```bash
cd docker
docker-compose up -d
```

Or from the project root:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

## Environment-Specific Configurations

### Production

For production use, consider:

1. Using Docker secrets for credentials:
   ```yaml
   secrets:
     db_password:
       external: true
   ```

2. Setting resource limits:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 512M
   ```

3. Using a named network for better isolation

### Development

For development, you might want to:

1. Mount the source code as a volume:
   ```bash
   docker run -v $(pwd)/src:/app/src gtfsrdb:latest [options]
   ```

2. Use `--verbose` flag for debugging:
   ```bash
   docker run gtfsrdb:latest --verbose [other options]
   ```

## Supported Databases

GTFSrDB supports any database compatible with SQLAlchemy:

- **PostgreSQL**: `postgresql://user:password@host:5432/dbname`
- **MySQL**: `mysql://user:password@host:3306/dbname`
- **SQLite**: `sqlite:///path/to/database.db`
- **Microsoft SQL Server**: `mssql+pyodbc://user:password@host/dbname?driver=ODBC+Driver+17+for+SQL+Server`

## Command-Line Options

All options from gtfsrdb.py are available:

- `-t, --trip-updates URL` - Trip updates feed URL
- `-a, --alerts URL` - Alerts feed URL
- `-p, --vehicle-positions URL` - Vehicle positions feed URL
- `-d, --database DSN` - Database connection string (required)
- `-o, --discard-old` - Delete old data before inserting new
- `-c, --create-tables` - Create database tables if missing
- `-1, --once` - Run once and exit
- `-w, --wait SECS` - Seconds between requests (default: 1)
- `-k, --kill-after MINS` - Stop after specified minutes
- `-v, --verbose` - Enable verbose logging
- `-q, --quiet` - Suppress warnings and status messages
- `-l, --language LANG` - Preferred language for translations (default: en)
- `--print-positions ROUTES` - Print positions for specific routes
- `-H, --header HEADER` - Add HTTP headers (JSON or Key:Value format)

## Troubleshooting

### Container exits immediately

Check logs:
```bash
docker logs gtfsrdb
```

Common issues:
- Missing required parameters (database, feed URLs)
- Invalid database connection
- Network connectivity issues

### Database connection errors

Ensure:
- Database is accessible from container
- If using `localhost`, use `host.docker.internal` (Docker Desktop) or container name
- Firewall rules allow connection
- Credentials are correct

### Feed parsing errors

- Verify feed URLs are accessible
- Check if API key/headers are required
- Ensure feed is valid GTFS-RT format

## Security Best Practices

1. **Never hardcode credentials** in Dockerfile or docker-compose.yml
2. Use **environment variables** or **Docker secrets**
3. Run as **non-root user** (default in this Dockerfile)
4. Keep base image **updated** for security patches
5. Use **private registries** for production images
6. Scan images for vulnerabilities:
   ```bash
   docker scan gtfsrdb:latest
   ```

## Building for Multiple Architectures

Build for ARM and x86:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t gtfsrdb:latest .
```

## License

See LICENSE file in the project root.
