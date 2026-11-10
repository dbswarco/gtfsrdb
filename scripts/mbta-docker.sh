#!/bin/bash

../docker/docker-run.sh mbta -d postgresql+psycopg2://ott:ott@ubuntudocker-vm.t4dlab.home/mbta -w 1 -p https://cdn.mbta.com/realtime/VehiclePositions.pb -t https://cdn.mbta.com/realtime/TripUpdates.pb -v
