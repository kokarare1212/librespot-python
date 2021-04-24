from __future__ import annotations

import logging
import sched
import time
import typing

from librespot.core.Session import Session
from librespot.player import PlayerConfiguration
from librespot.player import StateWrapper
from librespot.player.metrics import PlaybackMetrics
from librespot.player.mixing import AudioSink
from librespot.player.playback.PlayerSession import PlayerSession
from librespot.player.state.DeviceStateHandler import DeviceStateHandler
from librespot.standard.Closeable import Closeable


class Player(Closeable, PlayerSession.Listener, AudioSink.Listener):
    VOLUME_MAX: int = 65536
    _LOGGER: logging = logging.getLogger(__name__)
    _scheduler: sched.scheduler = sched.scheduler(time.time)
    _session: Session = None
    _conf: PlayerConfiguration = None
    _events: Player.EventsDispatcher = None
    _sink: AudioSink = None
    _metrics: typing.Dict[str, PlaybackMetrics] = {}
    _state: StateWrapper = None
    _playerSession: PlayerSession = None
    _releaseLineFuture = None
    _deviceStateListener: DeviceStateHandler.Listener = None

    def __init__(self, conf: PlayerConfiguration, session: Session):
        self._conf = conf
        self._session = session
        self._events = Player.EventsDispatcher(conf)
        self._sink = AudioSink(conf, self)

        self._init_state()

    def _init_state(self):
        self._state = StateWrapper.StateWrapper(self._session, self,
                                                self._conf)

        class Anonymous(DeviceStateHandler.Listener):
            _player: Player = None

            def __init__(self, player: Player):
                self._player = player

            def ready(self) -> None:
                pass

            def command(
                self,
                endpoint: DeviceStateHandler.Endpoint,
                data: DeviceStateHandler.CommandBody,
            ) -> None:
                self._player._LOGGER.debug(
                    "Received command: {}".format(endpoint))

        self._deviceStateListener = Anonymous(self)
        self._state.add_listener(self._deviceStateListener)

    def volume_up(self, steps: int = 1):
        if self._state is None:
            return

    class EventsDispatcher:
        def __init__(self, conf: PlayerConfiguration):
            pass
