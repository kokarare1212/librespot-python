from __future__ import annotations
from librespot.core.Session import Session
from librespot.player import PlayerConfiguration, StateWrapper
from librespot.player.metrics import PlaybackMetrics
from librespot.player.mixing import AudioSink
from librespot.player.playback.PlayerSession import PlayerSession
from librespot.player.state.DeviceStateHandler import DeviceStateHandler
from librespot.standard.Closeable import Closeable
import sched
import time


class Player(Closeable, PlayerSession.Listener, AudioSink.Listener):
    VOLUME_MAX: int = 65536
    _scheduler: sched.scheduler = sched.scheduler(time.time)
    _session: Session = None
    _conf: PlayerConfiguration = None
    _events: Player.EventsDispatcher = None
    _sink: AudioSink = None
    _metrics: dict[str, PlaybackMetrics] = dict()
    _state: StateWrapper = None
    _playerSession: PlayerSession = None
    _releaseLineFuture = None
    _deviceStateListener: DeviceStateHandler.Listener = None

    def __init__(self, conf: PlayerConfiguration, session: Session):
        self._conf = conf
        self._session = session
        self._events = Player.EventsDispatcher(conf)
        self._sink = AudioSink(conf, self)

    def init_state(self):
        self._state = StateWrapper(self._session, self, self._conf)

        class Anonymous(DeviceStateHandler.Listener):
            def ready(self) -> None:
                pass

            def command(self, endpoint: DeviceStateHandler.Endpoint, data: DeviceStateHandler.CommandBody) -> None:
                pass

        self._deviceStateListener = Anonymous()


    def volume_up(self, steps: int = 1):
        if self.state is None:
            return


    class EventsDispatcher:
        def __init__(self, conf: PlayerConfiguration):
            pass
