#!/bin/bash

source env.sh

if [ $# -eq 0 ]; then
    >&2 echo "Arguments: [agency] [-t trip feed] [-p vehicle/position feed] [-a alerts feed]"
    exit 1
fi

DB_NAME="$1"
shift

if [[ "$1" == "-I" ]]; then
  gtfsrdb_args=$(cat "$2")
  shift 2
  optional_args=$*
else
  gtfsrdb_args=$*
  optional_args=''
fi

echo "select 'create database $DB_NAME' where not exists (select from pg_database where datname = '$DB_NAME')\gexec" | \
  psql -d "$DB" -h "$DB_HOST" -U "$DB_USER"
# Uncomment to debug commands sent to gtfsrdb.py.
# set -x
python3 "$PROJECT_DIR"/src/gtfsrdb/gtfsrdb.py -d postgresql+psycopg2://"$DB_USER":"$DB_PASS"@"$DB_HOST"/"$DB_NAME" -c \
  $gtfsrdb_args $optional_args