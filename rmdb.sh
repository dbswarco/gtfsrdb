#!/bin/bash

if [ $# -eq 0 ]; then
    >&2 echo "Arguments: [agency database to remove]"
    exit 1
fi

psql -d ott -h 10.5.0.2 -U ott -c "drop database $1;"
