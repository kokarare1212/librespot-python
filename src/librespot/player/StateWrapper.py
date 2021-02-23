from __future__ import annotations
from librespot.core import Session
from librespot.player import Player, PlayerConfiguration


class StateWrapper:
    session: Session
    player: Player

    def __init__(self, session: Session, player: Player,
                 conf: PlayerConfiguration):
        self.session = session
        self.player = player
