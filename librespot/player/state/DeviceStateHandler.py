from __future__ import annotations

import base64
import concurrent.futures
import enum
import logging
import time
import typing
import urllib.parse

from librespot.common import Utils
from librespot.core import Session
from librespot.player import PlayerConfiguration
from librespot.proto import Connect
from librespot.proto import Player


class DeviceStateHandler:
    _LOGGER: logging = logging.getLogger(__name__)
    _session: Session = None
    _deviceInfo: Connect.DeviceInfo = None
    _listeners: typing.List[DeviceStateHandler.Listener] = []
    _putState: Connect.PutStateRequest = None
    _putStateWorker: concurrent.futures.ThreadPoolExecutor = (
        concurrent.futures.ThreadPoolExecutor())
    _connectionId: str = None

    def __init__(self, session: Session, player, conf: PlayerConfiguration):
        self._session = session
        self._deviceInfo = None
        self._putState = Connect.PutStateRequest()

    def _update_connection_id(self, newer: str) -> None:
        newer = urllib.parse.unquote(newer, "UTF-8")

        if self._connectionId is None or self._connectionId != newer:
            self._connectionId = newer
            self._LOGGER.debug("Updated Spotify-Connection-Id: {}".format(
                self._connectionId))
            self._notify_ready()

    def add_listener(self, listener: DeviceStateHandler.Listener):
        self._listeners.append(listener)

    def _notify_ready(self) -> None:
        for listener in self._listeners:
            listener.ready()

    def update_state(
        self,
        reason: Connect.PutStateReason,
        player_time: int,
        state: Player.PlayerState,
    ):
        if self._connectionId is None:
            raise TypeError()

        if player_time == -1:
            pass
        else:
            pass

        self._putState.put_state_reason = reason
        self._putState.client_side_timestamp = int(time.time() * 1000)
        self._putState.device.device_info = self._deviceInfo
        self._putState.device.player_state = state

        self._putStateWorker.submit(self._put_connect_state, self._putState)

    def _put_connect_state(self, req: Connect.PutStateRequest):
        self._session.api().put_connect_state(self._connectionId, req)
        self._LOGGER.info("Put state. ts: {}, connId: {}, reason: {}".format(
            req.client_side_timestamp,
            Utils.truncate_middle(self._connectionId, 10),
            req.put_state_reason,
        ))

    class Endpoint(enum.Enum):
        Play: str = "play"
        Pause: str = "pause"
        Resume: str = "resume"
        SeekTo: str = "seek_to"
        SkipNext: str = "skip_next"
        SkipPrev: str = "skip_prev"

    class Listener:
        def ready(self) -> None:
            pass

        def command(
            self,
            endpoint: DeviceStateHandler.Endpoint,
            data: DeviceStateHandler.CommandBody,
        ) -> None:
            pass

        def volume_changed(self) -> None:
            pass

        def not_active(self) -> None:
            pass

    class CommandBody:
        _obj: typing.Any = None
        _data: bytes = None
        _value: str = None

        def __init__(self, obj: typing.Any):
            self._obj = obj

            if obj.get("data") is not None:
                self._data = base64.b64decode(obj.get("data"))

            if obj.get("value") is not None:
                self._value = obj.get("value")
