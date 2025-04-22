#!/bin/bash

if [ $# -eq 0 ]; then
    >&2 echo "Arguments: [agency database to remove]"
    exit 1
fi

psql -d ott -h 127.0.0.1 -U ott -c "drop database $1;"
