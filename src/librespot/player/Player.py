from librespot.core.Session import Session
from librespot.player import PlayerConfiguration, StateWrapper
import sched
import time


class Player:
    VOLUME_MAX: int = 65536
    _scheduler: sched.scheduler = sched.scheduler(time.time)
    _session: Session = None
    _conf: PlayerConfiguration
    state: StateWrapper

    # _playerSession:

    def __init__(self, conf: PlayerConfiguration, session: Session):
        self._conf = conf
        self._session = session

    def init_state(self):
        self.state = StateWrapper(self._session, self, self._conf)
