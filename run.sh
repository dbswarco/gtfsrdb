#!/bin/bash

if [ $# -eq 0 ]; then
    >&2 echo "Arguments: [agency] [-t trip feed] [-p vehicle/position feed] [-a alerts feed]"
    exit 1
fi

echo "select 'create database $1'where not exists (select from pg_database where datname = '$1')\gexec" | psql -d ott -h 10.5.0.2 -U ott
python3 src/gtfsrdb/gtfsrdb.py -d postgresql+psycopg2://ott:ott@10.5.0.2/"$1" -c "$2" "$3" "$4"