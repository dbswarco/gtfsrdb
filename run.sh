#!/bin/bash

if [ $# -eq 0 ]; then
    >&2 echo "Arguments: [agency] [-t trip feed] [-p vehicle/position feed] [-a alerts feed]"
    exit 1
fi

psql -d ott -h 127.0.0.1 -U ott -c "create database $1;"
./gtfsrdb.py -d postgresql+psycopg2://ott:ott@10.1.110.195/"$1" -c "$2" "$3" "$4"

