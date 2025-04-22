#!/bin/bash

if [ $# -eq 0 ]; then
    >&2 echo "Arguments: [agency] [-t trip feed] [-p vehicle/position feed] [-a alerts feed]"
    exit 1
fi

psql -d ott -h 10.5.0.2 -U ott -c "create database $1;"
python3 gtfsrdb.py -d postgresql+psycopg2://ott:ott@10.5.0.2/"$1" -c "$2" "$3" "$4"

