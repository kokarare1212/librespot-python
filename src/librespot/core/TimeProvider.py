import math
import time


class TimeProvider:
    offset = 0
    method = 0x00

    def init(self, conf=None, session=None):
        if conf is None and session is None:
            return
        if conf is not None:
            self.method = conf.time_synchronization_method
            if conf.time_synchronization_method == TimeProvider.Method.ntp:
                self.update_with_ntp()
            if conf.time_synchronization_method == TimeProvider.Method.manual:
                self.offset = conf.time_manual_correction
        if session is not None:
            if self.method != TimeProvider.Method.melody:
                return
            self.update_melody(session)

    def current_time_millis(self):
        return math.floor(time.time() * 1000) + self.offset

    def update_melody(self, session):
        pass

    def update_with_ntp(self):
        pass

    class Method:
        ntp = 0x00
        ping = 0x01
        melody = 0x02
        manual = 0x03
