from __future__ import annotations
from librespot.player import PlayerConfiguration


class AudioSink:
    def __init__(self, conf: PlayerConfiguration,
                 listener: AudioSink.Listener):
        pass

    class Listener:
        def sink_error(self, ex: Exception):
            pass
