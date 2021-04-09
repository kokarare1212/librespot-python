from __future__ import annotations
import concurrent.futures
import enum
import time
import typing
import logging

from librespot.core import Session
from librespot.mercury import RawMercuryRequest
from librespot.standard import ByteArrayOutputStream


class EventService:
    _session: Session
    _LOGGER: logging = logging.getLogger(__name__)
    _worker: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(
    )

    def __init__(self, session: Session):
        self._session = session

    def _worker_callback(self, event_builder: EventService.EventBuilder):
        try:
            body = event_builder.to_array()
            resp = self._session.mercury().send_sync(RawMercuryRequest.Builder(
            ).set_uri("hm://event-service/v1/events").set_method(
                "POST").add_user_field("Accept-Language", "en").add_user_field(
                    "X-ClientTimeStamp",
                    int(time.time() * 1000)).add_payload_part(body).build())

            self._LOGGER.debug("Event sent. body: {}, result: {}".format(
                body, resp.status_code))
        except IOError as ex:
            self._LOGGER.error("Failed sending event: {} {}".format(
                event_builder, ex))

    def send_event(self,
                   event_or_builder: typing.Union[EventService.GenericEvent,
                                                  EventService.EventBuilder]):
        if type(event_or_builder) is EventService.GenericEvent:
            builder = event_or_builder.build()
        elif type(event_or_builder) is EventService.EventBuilder:
            builder = event_or_builder
        else:
            TypeError()
        self._worker.submit(lambda: self._worker_callback(builder))

    def language(self, lang: str):
        event = EventService.EventBuilder(EventService.Type.LANGUAGE)
        event.append(s=lang)

    def close(self):
        pass

    class Type(enum.Enum):
        LANGUAGE = ("812", 1)
        FETCHED_FILE_ID = ("274", 3)
        NEW_SESSION_ID = ("557", 3)
        NEW_PLAYBACK_ID = ("558", 1)
        TRACK_PLAYED = ("372", 1)
        TRACK_TRANSITION = ("12", 37)
        CDN_REQUEST = ("10", 20)

        _eventId: str
        _unknown: str

        def __init__(self, event_id: str, unknown: str):
            self._eventId = event_id
            self._unknown = unknown

    class GenericEvent:
        def build(self) -> EventService.EventBuilder:
            pass

    class EventBuilder:
        body: ByteArrayOutputStream = ByteArrayOutputStream(256)

        def __init__(self, type: EventService.Type):
            self.append_no_delimiter(type.value[0])
            self.append(type.value[1])

        def append_no_delimiter(self, s: str = None) -> None:
            if s is None:
                s = ""

            self.body.write(buffer=bytearray(s.encode()))

        def append(self,
                   c: int = None,
                   s: str = None) -> EventService.EventBuilder:
            if c is None and s is None or c is not None and s is not None:
                raise TypeError()
            if c is not None:
                self.body.write(byte=0x09)
                self.body.write(byte=c)
                return self
            if s is not None:
                self.body.write(byte=0x09)
                self.append_no_delimiter(s)
                return self

        def to_array(self) -> bytearray:
            return self.body.to_byte_array()
