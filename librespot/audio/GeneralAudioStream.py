from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from librespot.audio.AbsChunkedInputStream import AbsChunkedInputStream
    from librespot.audio.format import SuperAudioFormat


class GeneralAudioStream:
    def stream(self) -> AbsChunkedInputStream:
        pass

    def codec(self) -> SuperAudioFormat:
        pass

    def describe(self) -> str:
        pass

    def decrypt_time_ms(self) -> int:
        pass
