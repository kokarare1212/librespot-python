from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from librespot.audio import AbsChunkedInputStream
    from librespot.audio.format import SuperAudioFormat
    from librespot.core import DealerClient, Session
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


class FeederException(Exception):
    pass


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


class MessageListener:
    def on_message(self, uri: str, headers: typing.Dict[str, str],
                   payload: bytes):
        raise NotImplementedError


class NoopAudioDecrypt(AudioDecrypt):
    def decrypt_chunk(self, chunk_index: int, buffer: bytes):
        return buffer

    def decrypt_time_ms(self):
        return 0


class PacketsReceiver:
    def dispatch(self, packet: Packet):
        raise NotImplementedError


class RequestListener:
    def on_request(self, mid: str, pid: int, sender: str,
                   command: typing.Any) -> DealerClient.RequestResult:
        raise NotImplementedError


class Runnable:
    def run(self):
        raise NotImplementedError


class SessionListener:
    def session_closing(self, session: Session) -> None:
        raise NotImplementedError

    def session_changed(self, session: Session) -> None:
        raise NotImplementedError


class SubListener:
    def event(self, resp: MercuryClient.Response) -> None:
        raise NotImplementedError
