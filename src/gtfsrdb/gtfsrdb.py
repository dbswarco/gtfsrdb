# gtfsrdb.py: load gtfs-realtime data to a database
# recommended to have the (static) GTFS data for the agency you are connecting
# to already loaded.

# Copyright 2011, 2013 Matt Conway

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
# Jorge Adorno

import datetime
import queue
import threading
import time
import sys
from optparse import OptionParser
import logging
import json
from urllib.request import urlopen, Request
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import gtfs_realtime_pb2 as gtfs_realtime_pb2
from model import *
from adaptive import FeedUpdateTimers

# Sentinel value used to signal the DB worker thread to shut down.
_WORKER_STOP = object()


def parse_options():
    p = OptionParser()

    p.add_option('-t', '--trip-updates', dest='tripUpdates', default=None,
                 help='The trip updates URL', metavar='URL')

    p.add_option('-a', '--alerts', default=None, dest='alerts',
                 help='The alerts URL', metavar='URL')

    p.add_option('-p', '--vehicle-positions', dest='vehiclePositions', default=None,
                 help='The vehicle positions URL', metavar='URL')

    p.add_option('-d', '--database', default=None, dest='dsn',
                 help='Database connection string', metavar='DSN')

    p.add_option('-o', '--discard-old', default=False, dest='deleteOld',
                 action='store_true',
                 help='Discard old updates, so the database is always current')

    p.add_option('-c', '--create-tables', default=False, dest='create',
                 action='store_true', help="Create tables if they aren't found")

    p.add_option('-1', '--once', default=False, dest='once', action='store_true',
                 help='Only issue a request once')

    p.add_option('-w', '--wait', default=1, type='int', metavar='SECS',
                 dest='timeout', help='Time to wait between requests (in seconds)')

    p.add_option('-k', '--kill-after', default=0, dest='killAfter', type="float",
                 help='Kill process after this many minutes')

    p.add_option('-v', '--verbose', default=False, dest='verbose',
                 action='store_true', help='Print generated SQL')

    p.add_option('-q', '--quiet', default=False, dest='quiet',
                 action='store_true', help="Don't print warnings and status messages")

    p.add_option('-l', '--language', default='en', dest='lang', metavar='LANG',
                 help='When multiple translations are available, prefer this language')

    p.add_option('--print-positions', default=None, dest='print_positions',
                 help='Print position updates for a given route number')

    p.add_option('-H', '--header', default=None,
             help="Add HTTP header options such as API key. "
                  "Format: JSON string like '{\"Key\":\"Value\"}' or simple 'Key:Value'", metavar="HEADER")

    p.add_option('--sleep', default=0, type='int', metavar='SECS',
                 dest='sleep_before_start',
                 help='Seconds to wait before starting data collection (useful for API limits)')

    return p.parse_args()


def setup_logger(opts):
    if opts.quiet:
        level = logging.ERROR
    elif opts.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logger = logging.getLogger()
    logger.setLevel(level)
    loghandler = logging.StreamHandler(sys.stdout)
    logformatter = logging.Formatter(fmt='%(message)s')
    loghandler.setFormatter(logformatter)
    logger.addHandler(loghandler)

    if opts.dsn is None:
        logging.error('No database specified!')
        exit(1)

    if opts.alerts is None and opts.tripUpdates is None and opts.vehiclePositions is None:
        logging.error('No trip updates, alerts, or vehicle positions URLs were specified!')
        exit(1)

    if opts.alerts is None:
        logging.warning('No alert URL specified')

    if opts.tripUpdates is None:
        logging.warning('No trip update URL specified')

    if opts.vehiclePositions is None:
        logging.warning('No vehicle positions URL specified')


def delete_old(session):
    # Go through all of the tables that we create, clear them
    # Don't mess with other tables (i.e., tables from static GTFS)
    for theClass in AllClasses:
        for obj in session.query(theClass):
            session.delete(obj)


def get_translation(string, lang):
    '''Get a specific translation from a TranslatedString.'''
    # If we don't find the requested language, return this
    untranslated = None
    # single translation, return it
    if len(string.translation) == 1:
        return string.translation[0].text
    for t in string.translation:
        if t.language == lang:
            return t.text
        if t.language is None:
            untranslated = t.text
    return untranslated
pass


def parse_headers(header_string):
    """Parse header string as either JSON or simple key:value format."""
    if not header_string or not header_string.strip():
        return None

    header_string = header_string.strip()

    # Try to parse as JSON first
    if header_string.startswith('{'):
        try:
            return json.loads(header_string)
        except json.JSONDecodeError as e:
            logging.error(f'Failed to parse header as JSON: {e}')
            logging.error(f'Header value: {repr(header_string)}')
            raise

    # Otherwise, treat as simple key:value or key=value format
    if ':' in header_string:
        key, value = header_string.split(':', 1)
        return {key.strip(): value.strip()}
    elif '=' in header_string:
        key, value = header_string.split('=', 1)
        return {key.strip(): value.strip()}
    else:
        logging.error(f'Header format not recognized. Use JSON or Key:Value format.')
        logging.error(f'Header value: {repr(header_string)}')
        raise ValueError(f'Invalid header format: {header_string}')


def process_trip_updates(fm, opts, timers):
    """Fetch the trip-updates feed and return a list of ORM objects ready to persist."""
    headers = parse_headers(opts.header)
    fm.ParseFromString(urlopen(Request(opts.tripUpdates, headers=headers)).read())
    timestamp = datetime.datetime.utcfromtimestamp(fm.header.timestamp)
    logging.info('Collected %s trip updates', len(fm.entity))
    objects = []
    for entity in fm.entity:
        tu = entity.trip_update
        dbtu = TripUpdate(
            trip_id=tu.trip.trip_id,
            route_id=tu.trip.route_id,
            trip_start_time=tu.trip.start_time,
            trip_start_date=tu.trip.start_date,
            # get the schedule relationship
            # This is somewhat undocumented, but by referencing the
            # DESCRIPTOR.enum_types_by_name, you get a dict of enum types
            # as described at
            # http://code.google.com/apis/protocolbuffers/docs/reference/python/google.protobuf.descriptor.EnumDescriptor-class.html
            schedule_relationship=tu.trip.DESCRIPTOR.enum_types_by_name[
                'ScheduleRelationship'].values_by_number[tu.trip.schedule_relationship].name,
            vehicle_id=tu.vehicle.id,
            vehicle_label=tu.vehicle.label,
            vehicle_license_plate=tu.vehicle.license_plate,
            timestamp=timestamp)
        for stu in tu.stop_time_update:
            dbstu = StopTimeUpdate(
                stop_sequence=stu.stop_sequence,
                stop_id=stu.stop_id,
                arrival_delay=stu.arrival.delay,
                arrival_time=stu.arrival.time,
                arrival_uncertainty=stu.arrival.uncertainty,
                departure_delay=stu.departure.delay,
                departure_time=stu.departure.time,
                departure_uncertainty=stu.departure.uncertainty,
                schedule_relationship=tu.trip.DESCRIPTOR.enum_types_by_name[
                    'ScheduleRelationship'].values_by_number[tu.trip.schedule_relationship].name
            )
            dbtu.StopTimeUpdates.append(dbstu)
        objects.append(dbtu)
    if objects:
        timers.process_timestamps(objects[0])
    return objects


def process_alerts(fm, opts, timers):
    """Fetch the alerts feed and return a list of ORM objects ready to persist."""
    headers = parse_headers(opts.header)
    fm.ParseFromString(urlopen(Request(opts.alerts, headers=headers)).read())
    logging.info('Collected %s alerts', len(fm.entity))
    objects = []
    for entity in fm.entity:
        alert = entity.alert
        dbalert = Alert(
            start=alert.active_period[0].start,
            end=alert.active_period[0].end,
            cause=alert.DESCRIPTOR.enum_types_by_name['Cause'].values_by_number[alert.cause].name,
            effect=alert.DESCRIPTOR.enum_types_by_name['Effect'].values_by_number[alert.effect].name,
            url=get_translation(alert.url, opts.lang),
            header_text=get_translation(alert.header_text, opts.lang),
            description_text=get_translation(alert.description_text, opts.lang)
        )
        for ie in alert.informed_entity:
            dbie = EntitySelector(
                agency_id=ie.agency_id,
                route_id=ie.route_id,
                route_type=ie.route_type,
                stop_id=ie.stop_id,
                trip_id=ie.trip.trip_id,
                trip_route_id=ie.trip.route_id,
                trip_start_time=ie.trip.start_time,
                trip_start_date=ie.trip.start_date)
            dbalert.InformedEntities.append(dbie)
        objects.append(dbalert)
        if objects:
            timers.process_timestamps(objects[0])
        return objects


def process_vehicle_positions(fm, opts, timers):
    """Fetch the vehicle-positions feed and return a list of ORM objects ready to persist."""
    headers = parse_headers(opts.header)
    fm.ParseFromString(urlopen(Request(opts.vehiclePositions, headers=headers)).read())
    timestamp = datetime.datetime.utcfromtimestamp(fm.header.timestamp)
    logging.info('Collected %s vehicle positions', len(fm.entity))
    objects = []
    for entity in fm.entity:
        vp = entity.vehicle

        # Handle optional fields with HasField check or default values
        trip_direction_id = vp.trip.direction_id if vp.trip.HasField('direction_id') else None
        trip_schedule_relationship = gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship.Name(
            vp.trip.schedule_relationship) if vp.trip.HasField('schedule_relationship') else None

        current_stop_sequence = vp.current_stop_sequence if vp.HasField('current_stop_sequence') else None
        stop_id = vp.stop_id if vp.HasField('stop_id') else None

        position_odometer = vp.position.odometer if vp.position.HasField('odometer') else None

        congestion_level = gtfs_realtime_pb2.VehiclePosition.CongestionLevel.Name(
            vp.congestion_level) if vp.HasField('congestion_level') else None

        dbvp = VehiclePosition(
            trip_id=vp.trip.trip_id,
            route_id=vp.trip.route_id,
            trip_start_time=vp.trip.start_time,
            trip_start_date=vp.trip.start_date,
            trip_direction_id=trip_direction_id,
            trip_schedule_relationship=trip_schedule_relationship,
            vehicle_id=vp.vehicle.id,
            vehicle_label=vp.vehicle.label,
            vehicle_license_plate=vp.vehicle.license_plate,
            position_latitude=vp.position.latitude,
            position_longitude=vp.position.longitude,
            position_bearing=vp.position.bearing,
            position_speed=vp.position.speed,
            position_odometer=position_odometer,
            current_stop_sequence=current_stop_sequence,
            stop_id=stop_id,
            current_status=gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus.Name(vp.current_status),
            congestion_level=congestion_level,
            occupancy_status=gtfs_realtime_pb2.VehiclePosition.OccupancyStatus.Name(vp.occupancy_status),
            timestamp=timestamp)

        if (opts.print_positions is not None and
                (dbvp.route_id in [item.strip() for item in opts.print_positions.split(",")]
                and dbvp.vehicle_id in [item.strip() for item in opts.print_positions.split(",")])):
            logging.info(f'{dbvp.timestamp}: Route {dbvp.route_id}, Veh {dbvp.vehicle_id}: '
                         f'Position {dbvp.position_latitude}, {dbvp.position_longitude}, '
                         f'Stop {dbvp.stop_id} (seq {dbvp.current_stop_sequence}), '
                         f'Status {dbvp.current_status}, Occupancy {dbvp.occupancy_status}, '
                         f'Congestion {dbvp.congestion_level}')
            try:
                with open('print_positions.csv', 'x') as f:
                    f.write(f'Timestamp, Route ID, Vehicle ID, Latitude, Longitude, Stop ID, Current Stop Sequence, '
                            f'Current Status, Occupancy Status, Congestion Level\n')
            except FileExistsError:
                pass
            finally:
                with open('print_positions.csv', 'a') as f:
                    f.write(f'{dbvp.timestamp}, {dbvp.route_id}, {dbvp.vehicle_id}, '
                             f'{dbvp.position_latitude}, {dbvp.position_longitude}, '
                             f'{dbvp.stop_id}, (seq {dbvp.current_stop_sequence}), '
                             f'{dbvp.current_status}, {dbvp.occupancy_status}, '
                             f'{dbvp.congestion_level}\n')

        objects.append(dbvp)
    if objects:
        timers.process_timestamps(objects[0])
    return objects


def collect_feed(opts, timers):
    """Fetch all configured feeds and return a flat list of ORM objects.

    All network I/O and protobuf parsing happens here, on the calling thread.
    The returned objects are plain Python/SQLAlchemy instances with no live
    protobuf references, so they are safe to hand off to another thread.
    """
    objects = []
    fm = gtfs_realtime_pb2.FeedMessage()
    if opts.tripUpdates:
        try:
            objects.extend(process_trip_updates(fm, opts, timers))
        except Exception:
            logging.error('Error fetching trip updates: %s', sys.exc_info())
    if opts.alerts:
        try:
            objects.extend(process_alerts(fm, opts, timers))
        except Exception:
            logging.error('Error fetching alerts: %s', sys.exc_info())
    if opts.vehiclePositions:
        try:
            objects.extend(process_vehicle_positions(fm, opts, timers))
        except Exception:
            logging.error('Error fetching vehicle positions: %s', sys.exc_info())
    logging.info('Average feed update interval: %s' % timers.average_update_interval)
    logging.debug('All update intervals: %s' % timers.update_intervals)
    return objects


def db_worker(work_queue, Session, opts):
    """Background thread: drain *work_queue* and write each batch to the DB.

    Each item on the queue is either:
      - a list of SQLAlchemy ORM objects to add, or
      - the _WORKER_STOP sentinel, which causes the thread to exit cleanly.

    The worker owns its own Session so there is no cross-thread SQLAlchemy
    state sharing with the main (fetch) thread.
    """
    with Session() as session:
        while True:
            try:
                batch = work_queue.get(timeout=1)
            except queue.Empty:
                continue

            if batch is _WORKER_STOP:
                work_queue.task_done()
                break

            try:
                if opts.deleteOld:
                    delete_old(session)
                for obj in batch:
                    session.add(obj)
                session.commit()
                remaining = work_queue.qsize()
                if remaining > 0:
                    logging.warning(
                        'DB worker is %d batch(es) behind; consider a longer -w interval '
                        'or a faster database connection.', remaining)
            except Exception:
                logging.error('DB worker error: %s', sys.exc_info())
                session.rollback()
            finally:
                work_queue.task_done()

    logging.info('DB worker stopped.')


def main():
    # Parse command line options/args
    opts, args = parse_options()
    # Set up a logger
    setup_logger(opts)

    # Connect to the database
    engine = create_engine(opts.dsn, echo=opts.verbose)
    insp = inspect(engine)
    Session = sessionmaker(bind=engine)

    # Check / create tables before starting the worker thread
    for table in Base.metadata.tables.keys():
        if not insp.has_table(table):
            if opts.create:
                logging.info('Creating table %s', table)
                Base.metadata.tables[table].create(engine)
            else:
                logging.error('Missing table %s! Use -c to create it.', table)
                exit(1)

    if opts.sleep_before_start:
        logging.info('Waiting %s seconds before collecting GTFS-RT data...' % opts.sleep_before_start)
        time.sleep(opts.sleep_before_start)

    # Check the feed version once (uses a fresh, empty FeedMessage)
    fm = gtfs_realtime_pb2.FeedMessage()
    if fm.header.gtfs_realtime_version != u'1.0':
        logging.warning('Warning: feed version mismatch: found %s, expected 1.0',
                        fm.header.gtfs_realtime_version)
    timers = FeedUpdateTimers()

    # Unbounded queue: the fetch loop enqueues batches; the worker drains them.
    work_queue = queue.Queue()

    worker = threading.Thread(
        target=db_worker,
        args=(work_queue, Session, opts),
        name='db-worker',
        daemon=True,
    )
    worker.start()

    stop_time = None
    if opts.killAfter > 0:
        stop_time = datetime.datetime.now() + datetime.timedelta(minutes=opts.killAfter)

    def shutdown(reason):
        """Stop the fetch loop, flush queued batches, and exit cleanly."""
        logging.info('%s Waiting for DB worker to finish writing...', reason)
        shutdown_start = datetime.datetime.now()
        work_queue.put(_WORKER_STOP)
        if worker.is_alive():
            work_queue.join()
        logging.info('Database write extended beyond shutdown signal by %s seconds.' %
                     (datetime.datetime.now()-shutdown_start).total_seconds())
        logging.info('Done.')

    try:
        keep_running = True
        while keep_running:
            loop_start = time.time()

            if stop_time and datetime.datetime.now() > stop_time:
                logging.info('Kill-after time reached, stopping fetch loop.')
                break

            logging.info("Collecting GTFS-RT feed data at %s",
                         datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            try:
                batch = collect_feed(opts, timers)
                if batch:
                    work_queue.put(batch)
            except Exception:
                logging.error('Exception collecting feed: %s', sys.exc_info())

            loop_time = time.time() - loop_start
            logging.debug('Feed collection took %.4f seconds', loop_time)

            if opts.once:
                logging.info('Executed the load ONCE ... going to stop now...')
                keep_running = False
            else:
                sleep_time = opts.timeout - loop_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logging.warning(
                        'Feed collection overran the -w interval by %.4f seconds',
                        -sleep_time)

        shutdown('Fetch loop finished.')

    except KeyboardInterrupt:
        shutdown('Interrupted.')


if __name__ == "__main__":
    main()
