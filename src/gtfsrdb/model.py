# gtfsrdb.py: load gtfs-realtime data to a database
# recommended to have the (static) GTFS data for the agency you are connecting
# to already loaded.

# Copyright 2011 Matt Conway

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Authors:
# Matt Conway: main code

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, Text, DateTime, Float
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

# Collapsed types:
# TripUpdate.trip
# TripUpdate.vehicle
# StopTimeUpdate.arrival
# StopTimeUpdate.departure
# Alert.active_period
# Position.latitude
# Position.longitude
# Position.bearing
# Position.speed
# VehicleDescriptor.id
# VehicleDescriptor.label
# VehicleDescriptor.license_plate

# The oid is called oid because several of the GTFSr types have string ids
# TODO: add sequences


class TripUpdate(Base):
    __tablename__ = 'trip_updates'
    oid = Column(Integer, primary_key=True)

    # This replaces the TripDescriptor message
    # TODO: figure out the relations
    trip_id = Column(Text)
    route_id = Column(Text)
    trip_start_time = Column(Text)
    trip_start_date = Column(Text)
    # Put in the string value not the enum
    # TODO: add a domain
    schedule_relationship = Column(Text)

    # Collapsed VehicleDescriptor
    vehicle_id = Column(Text)
    vehicle_label = Column(Text)
    vehicle_license_plate = Column(Text)

    # moved from the header, and reformatted as datetime
    timestamp = Column(DateTime)

    StopTimeUpdates = relationship('StopTimeUpdate', backref='TripUpdate')


class StopTimeUpdate(Base):
    __tablename__ = 'stop_time_updates'
    oid = Column(Integer, primary_key=True)

    # TODO: Fill one from the other
    stop_sequence = Column(Integer)
    stop_id = Column(Text)

    # Collapsed StopTimeEvent
    arrival_delay = Column(Integer)
    arrival_time = Column(Integer)
    arrival_uncertainty = Column(Integer)

    # Collapsed StopTimeEvent
    departure_delay = Column(Integer)
    departure_time = Column(Integer)
    departure_uncertainty = Column(Integer)

    # TODO: Add domain
    schedule_relationship = Column(Text)

    # Link it to the TripUpdate
    trip_update_id = Column(Integer, ForeignKey('trip_updates.oid'))

    # The .TripUpdate is done by the backref in TripUpdate


class Alert(Base):
    __tablename__ = 'alerts'

    oid = Column(Integer, primary_key=True)

    # Collapsed TimeRange
    start = Column(Integer)
    end = Column(Integer)

    # Add domain
    cause = Column(Text)
    effect = Column(Text)

    url = Column(Text)
    header_text = Column(Text)
    description_text = Column(Text)

    InformedEntities = relationship('EntitySelector', backref='Alert')


class EntitySelector(Base):
    __tablename__ = 'entity_selectors'
    oid = Column(Integer, primary_key=True)

    agency_id = Column(Text)
    route_id = Column(Text)
    route_type = Column(Integer)
    stop_id = Column(Text)

    # Collapsed TripDescriptor
    trip_id = Column(Text)
    trip_route_id = Column(Text)
    trip_start_time = Column(Text)
    trip_start_date = Column(Text)

    alert_id = Column(Integer, ForeignKey('alerts.oid'))


class VehiclePosition(Base):
    __tablename__ = 'vehicle_positions'
    oid = Column(Integer, primary_key=True)

    # This replaces the TripDescriptor message
    # TODO: figure out the relations
    trip_id = Column(Text)
    route_id = Column(Text)
    trip_start_time = Column(Text)
    trip_start_date = Column(Text)

    # Collapsed VehicleDescriptor
    vehicle_id = Column(Text)
    vehicle_label = Column(Text)
    vehicle_license_plate = Column(Text)

    # Collapsed Position
    position_latitude = Column(Float)
    position_longitude = Column(Float)
    position_bearing = Column(Float)
    position_speed = Column(Float)

    occupancy_status = Column(Text)

    # moved from the header, and reformatted as datetime
    timestamp = Column(DateTime)


# So one can loop over all classes to clear them for a new load (-o option)
AllClasses = (TripUpdate, StopTimeUpdate, Alert, EntitySelector, VehiclePosition)
