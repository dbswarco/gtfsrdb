#!/bin/bash

source env.sh

if [ $# -eq 0 ]; then
    >&2 echo "Arguments: [agency] [-t trip feed] [-p vehicle/position feed] [-a alerts feed]"
    exit 1
fi

DB_NAME="$1"
shift

echo "select 'create database $1' where not exists (select from pg_database where datname = '$DB_NAME')\gexec" | \
  psql -d "$DB" -h "$DB_HOST" -U "$DB_USER"
python3 "$PROJECT_DIR"/src/gtfsrdb/gtfsrdb.py -d postgresql+psycopg2://"$DB_USER":"$DB_PASS"@"$DB_HOST"/"$DB_NAME" -c "$@"