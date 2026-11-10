# GTFSrDB — Agent Reference

## Project Overview

GTFSrDB is a Python tool that polls GTFS-realtime (GTFSr) feeds and persists the data into a SQL database using SQLAlchemy. It is designed to work alongside static GTFS data loaded by [gtfsdb](https://github.com/OpenTransitTools/gtfsdb), but operates independently.

**License:** Apache 2.0  
**Entry point:** `gtfsrdb = "gtfsrdb.gtfsrdb:main"` (defined in `pyproject.toml`)  
**Install:** `pip install -e .`  

---

## Repository Layout

```
gtfsrdb/
├── src/gtfsrdb/
│   ├── gtfsrdb.py          # Main application logic and CLI entry point
│   ├── model.py            # SQLAlchemy ORM models for all GTFSr tables
│   ├── gtfs_realtime_pb2.py# Generated protobuf bindings for GTFS-realtime
│   └── __init__.py
├── docker/
│   ├── docker-compose.yml  # Spins up PostGIS + Adminer for local dev
│   └── docker-run.sh       # Helper to run a gtfsrdb Docker container
├── scripts/
│   ├── run.sh              # Bash helper: creates Postgres DB and runs gtfsrdb
│   ├── rmdb.sh             # Drops a named Postgres database
│   └── .env                # DB_HOST, DB, DB_USER, DB_PASS (not committed)
├── gtfs-realtime.proto     # Source protobuf schema (reference only)
├── pyproject.toml          # Build metadata and dependencies
└── README.md
```

---

## Core Source Files

### `src/gtfsrdb/model.py`
Defines the SQLAlchemy ORM tables written to the database:

| Class | Table | Purpose |
|---|---|---|
| `TripUpdate` | `trip_updates` | One row per GTFSr trip update entity |
| `StopTimeUpdate` | `stop_time_updates` | FK → `trip_updates.oid`; arrival/departure predictions |
| `Alert` | `alerts` | Service alerts with cause, effect, URL, text |
| `EntitySelector` | `entity_selectors` | FK → `alerts.oid`; which routes/stops/trips an alert affects |
| `VehiclePosition` | `vehicle_positions` | Real-time vehicle location, status, occupancy |

`AllClasses` tuple is used to clear all tables when `-o` (discard-old) is active.

Several GTFSr nested messages are **flattened into columns** on their parent table (e.g., `TripDescriptor` → `trip_id`, `route_id`, etc.; `Position` → `position_latitude`, `position_longitude`, etc.).

### `src/gtfsrdb/gtfsrdb.py`
Main application. Key functions:

| Function | Description |
|---|---|
| `parse_options()` | Builds and returns the CLI option parser |
| `setup_logger(opts)` | Configures logging level (quiet/info/debug) and validates required options |
| `delete_old(session)` | Deletes all rows from all GTFSr tables (used with `-o`) |
| `get_translation(string, lang)` | Extracts a single string from a GTFSr `TranslatedString` |
| `parse_headers(header_string)` | Parses HTTP header option (JSON or `Key:Value` format) |
| `process_trip_updates(fm, opts, session)` | Fetches and inserts trip update entities |
| `process_alerts(fm, opts, session)` | Fetches and inserts alert entities |
| `process_vehicle_positions(fm, opts, session)` | Fetches and inserts vehicle position entities; optionally prints/logs to CSV |
| `commit(ses)` | Commits the SQLAlchemy session |
| `main()` | CLI entry: parses options, connects DB, creates tables if needed, runs the polling loop |

---

## CLI Options

| Flag | Long form | Default | Description |
|---|---|---|---|
| `-t URL` | `--trip-updates` | None | GTFS-RT TripUpdates feed URL |
| `-a URL` | `--alerts` | None | GTFS-RT Service Alerts feed URL |
| `-p URL` | `--vehicle-positions` | None | GTFS-RT VehiclePositions feed URL |
| `-d DSN` | `--database` | **required** | SQLAlchemy database URL |
| `-o` | `--discard-old` | False | Delete all old data each iteration (live-current mode) |
| `-c` | `--create-tables` | False | Auto-create tables if missing |
| `-1` | `--once` | False | Fetch once and exit |
| `-w SECS` | `--wait` | 1 | Seconds to wait between polling iterations |
| `-k MINS` | `--kill-after` | 0 | Exit after N minutes (0 = run forever) |
| `-v` | `--verbose` | False | Debug logging (also echoes SQL via SQLAlchemy) |
| `-q` | `--quiet` | False | Only log errors |
| `-l LANG` | `--language` | `en` | Language preference for TranslatedStrings |
| `--print-positions ROUTE,VEH` | | None | Print/CSV-log positions matching route+vehicle ID pair |
| `-H HEADER` | `--header` | None | HTTP header(s); JSON `{"Key":"Val"}` or `Key:Value` |

---

## Dependencies

Defined in `pyproject.toml`:

- `sqlalchemy` — ORM and DB engine abstraction
- `protobuf~=5.28.3` — Protocol Buffers runtime for GTFSr parsing

Optional (for PostgreSQL):
- `psycopg2-binary` — install separately

---

## Database Support

GTFSrDB uses SQLAlchemy and works with any supported backend. Tested with:

- **SQLite** — `sqlite:///test.db`
- **PostgreSQL** — `postgresql+psycopg2://user:pass@host/dbname`
- **Microsoft SQL Server**

The `docker/docker-compose.yml` provides a local **PostGIS** + **Adminer** stack for development:
- PostgreSQL on port `5432` (user/pass/db: `ott`)
- Adminer web UI on port `8080`

---

## Helper Scripts

### `scripts/run.sh`
Reads `scripts/.env` for DB credentials, creates the named Postgres database if absent, activates `.venv`, and runs `gtfsrdb.py` directly.

```sh
# Usage: ./run.sh <agency_name> [gtfsrdb options]
./run.sh tampa -t http://api.tampa.onebusaway.org:8088/trip-updates

# Or use an input file with feed URLs:
./run.sh stanrta -I stanrta.txt
```

`scripts/.env` format:
```
DB_HOST="localhost"
DB="gtfs"
DB_USER="gtfs"
DB_PASS="gtfs"
```

### `scripts/rmdb.sh`
Drops a named PostgreSQL database.

### `docker/docker-run.sh`
Runs a `gtfsrdb` Docker image container with pre-wired Postgres connection. Takes agency name as first argument followed by gtfsrdb flags.

---

## Development Notes

- The virtual environment lives at `.venv/`. Activate with `source .venv/bin/activate`.
- `scripts/run.sh` invokes `python gtfsrdb.py` directly from `src/gtfsrdb/` (not via the installed `gtfsrdb` entry point).
- `gtfs_realtime_pb2.py` is a pre-generated protobuf file. The source schema is `gtfs-realtime.proto`. Regenerate with `protoc` if the proto is updated.
- The `--discard-old` (`-o`) flag **deletes every row** in all GTFSr tables each cycle — including data inserted before the current session. Use it only when you want a perpetually current (not historical) database.
- `--print-positions` matches on a comma-separated list where **both** a `route_id` and a `vehicle_id` must appear; it logs to stdout and appends to `print_positions.csv` in the working directory.
- No duplicate detection is implemented; running without `-o` accumulates data indefinitely.
- Run `VACUUM ANALYZE` on PostgreSQL frequently due to high insert/delete churn.
