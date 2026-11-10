#!/bin/bash

if [[ -z "$1" ]]; then
  echo "missing argument: agency name"
  echo "help: docker-run.sh <agency name> <run arguments -v, -p, -t, -H, etc.>"
  exit 1
fi
if [[ -z "$2" ]]; then
  echo "missing run arguments"
  echo "help: docker-run.sh <agency name> <run arguments -v, -p, -t, -H, etc.>"
  exit 1
fi

agency="$1"
shift

image="gtfsrdb:latest"

docker run --name gtfsrdb-"$agency" "$image" --database=postgresql+psycopg2://ott:ott@ubuntudocker-vm.t4dlab.home:5432/"$agency" --wait=1 --verbose --create-tables "$@"
