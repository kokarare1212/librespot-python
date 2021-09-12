from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from librespot.audio import AbsChunkedInputStream
    from librespot.audio.format import SuperAudioFormat
    from librespot.crypto import Packet
    from librespot.mercury import MercuryClient
    from librespot.proto import Metadata_pb2 as Metadata


class AudioDecrypt:
    def decrypt_chunk(self, chunk_index: int, buffer: bytes):
        raise NotImplementedError

    def decrypt_time_ms(self):
        raise NotImplementedError


class AudioQualityPicker:
    def get_file(self,
                 files: typing.List[Metadata.AudioFile]) -> Metadata.AudioFile:
        raise NotImplementedError


class Closeable:
    def close(self) -> None:
        raise NotImplementedError


class GeneralAudioStream:
    def stream(self) -> AbsChunkedInputStream:
        raise NotImplementedError

    def codec(self) -> SuperAudioFormat:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError

    def decrypt_time_ms(self) -> int:
        raise NotImplementedError


class GeneralWritableStream:
    def write_chunk(self, buffer: bytearray, chunk_index: int, cached: bool):
        raise NotImplementedError


class HaltListener:
    def stream_read_halted(self, chunk: int, _time: int) -> None:
        raise NotImplementedError

    def stream_read_resumed(self, chunk: int, _time: int) -> None:
        raise NotImplementedError


class NoopAudioDecrypt(AudioDecrypt):
    def decrypt_chunk(self, chunk_index: int, buffer: bytes):
        raise NotImplementedError

    def decrypt_time_ms(self):
        return 0


class PacketsReceiver:
    def dispatch(self, packet: Packet):
        raise NotImplementedError


class SubListener:
    def event(self, resp: MercuryClient.Response) -> None:
        raise NotImplementedError
