from datetime import datetime, timedelta
from typing import Dict


class FeedUpdateTimers:
    def __init__(self):
        self.last_VehiclePosition: datetime = datetime.now()
        self.last_TripUpdate: datetime = datetime.now()
        self.last_Alert: datetime = datetime.now()
        self.current_VehiclePosition: datetime = datetime.now()
        self.current_TripUpdate: datetime = datetime.now()
        self.current_Alert: datetime = datetime.now()
        self.average_update_interval: timedelta = timedelta()
        self.update_intervals: Dict[str, timedelta] = {'VehiclePosition': timedelta(),
                                                       'TripUpdate': timedelta(),
                                                       'Alert': timedelta(),
                                                       'average': timedelta()}

    def process_timestamps(self, obj):
        if type(obj).__name__ == 'VehiclePosition':
            self.update_intervals['VehiclePosition'] = obj.timestamp - self.last_VehiclePosition
            self.last_VehiclePosition = obj.timestamp
        if type(obj).__name__ == 'TripUpdate':
            self.update_intervals['TripUpdate'] = obj.timestamp - self.last_TripUpdate
            self.last_TripUpdate = obj.timestamp
        if type(obj).__name__ == 'Alert':
            self.update_intervals['Alert'] = obj.timestamp - self.last_Alert
            self.last_Alert = obj.timestamp

        updated_feed_values = [v for v in [self.update_intervals['VehiclePosition'],
                              self.update_intervals['TripUpdate'],
                              self.update_intervals['Alert']]
                  if v > timedelta()]
        if updated_feed_values:
            self.average_update_interval = timedelta(
                seconds=int(sum(updated_feed_values, timedelta()).total_seconds() / len(updated_feed_values))
            )
        self.update_intervals['average'] = self.average_update_interval
