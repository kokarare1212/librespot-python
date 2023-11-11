from __future__ import annotations
from librespot import util
from librespot.audio.decrypt import AesAudioDecrypt
from librespot.audio.format import SuperAudioFormat
from librespot.audio.storage import ChannelManager
from librespot.cache import CacheManager
from librespot.crypto import Packet
from librespot.metadata import EpisodeId, PlayableId, TrackId
from librespot.proto import Metadata_pb2 as Metadata, StorageResolve_pb2 as StorageResolve
from librespot.structure import AudioDecrypt, AudioQualityPicker, Closeable, FeederException, GeneralAudioStream, GeneralWritableStream, HaltListener, NoopAudioDecrypt, PacketsReceiver
import concurrent.futures
import io
import logging
import math
import queue
import random
import struct
import threading
import time
import typing
import urllib.parse

if typing.TYPE_CHECKING:
    from librespot.core import Session


class AbsChunkedInputStream(io.BytesIO, HaltListener):
    chunk_exception = None
    closed = False
    max_chunk_tries = 128
    preload_ahead = 3
    preload_chunk_retries = 2
    retries: typing.List[int]
    retry_on_chunk_error: bool
    wait_lock: threading.Condition = threading.Condition()
    wait_for_chunk = -1
    __decoded_length = 0
    __mark = 0
    __pos = 0

    def __init__(self, retry_on_chunk_error: bool):
        super().__init__()
        self.retries = [0] * self.chunks()
        self.retry_on_chunk_error = retry_on_chunk_error

    def is_closed(self) -> bool:
        return self.closed

    def buffer(self) -> typing.List[bytes]:
        raise NotImplementedError()

    def size(self) -> int:
        raise NotImplementedError()

    def close(self) -> None:
        self.closed = True
        with self.wait_lock:
            self.wait_lock.notify_all()

    def available(self):
        return self.size() - self.__pos

    def mark_supported(self) -> bool:
        return True

    def mark(self, read_ahead_limit: int) -> None:
        self.__mark = self.__pos

    def reset(self) -> None:
        self.__pos = self.__mark

    def pos(self) -> int:
        return self.__pos

    def seek(self, where: int, **kwargs) -> None:
        if where < 0:
            raise TypeError()
        if self.closed:
            raise IOError("Stream is closed!")
        self.__pos = where
        self.check_availability(int(self.__pos / (128 * 1024)), False, False)

    def skip(self, n: int) -> int:
        if n < 0:
            raise TypeError()
        if self.closed:
            raise IOError("Stream is closed!")
        k = self.size() - self.__pos
        if n < k:
            k = n
        self.__pos += k
        chunk = int(self.__pos / (128 * 1024))
        self.check_availability(chunk, False, False)
        return k

    def requested_chunks(self) -> typing.List[bool]:
        raise NotImplementedError()

    def available_chunks(self) -> typing.List[bool]:
        raise NotImplementedError()

    def chunks(self) -> int:
        raise NotImplementedError()

    def request_chunk_from_stream(self, index: int) -> None:
        raise NotImplementedError()

    def should_retry(self, chunk: int) -> bool:
        if self.retries[chunk] < 1:
            return True
        if self.retries[chunk] > self.max_chunk_tries:
            return False
        return self.retry_on_chunk_error

    def check_availability(self, chunk: int, wait: bool, halted: bool) -> None:
        if halted and not wait:
            raise TypeError()
        if not self.requested_chunks()[chunk]:
            self.request_chunk_from_stream(chunk)
            self.requested_chunks()[chunk] = True
        for i in range(chunk + 1,
                       min(self.chunks() - 1, chunk + self.preload_ahead) + 1):
            if (self.requested_chunks()[i]
                    and self.retries[i] < self.preload_chunk_retries):
                self.request_chunk_from_stream(i)
                self.requested_chunks()[chunk] = True
        if wait:
            if self.available_chunks()[chunk]:
                return
            retry = False
            with self.wait_lock:
                if not halted:
                    self.stream_read_halted(chunk, int(time.time() * 1000))
                self.chunk_exception = None
                self.wait_for_chunk = chunk
                self.wait_lock.wait_for(lambda: self.available_chunks()[chunk])
                if self.closed:
                    return
                if self.chunk_exception is not None:
                    if self.should_retry(chunk):
                        retry = True
                    else:
                        raise AbsChunkedInputStream.ChunkException
                if not retry:
                    self.stream_read_halted(chunk, int(time.time() * 1000))
            if retry:
                time.sleep(math.log10(self.retries[chunk]))
                self.check_availability(chunk, True, True)

    def read(self, __size: int = 0) -> bytes:
        if self.closed:
            raise IOError("Stream is closed!")
        if __size <= 0:
            if self.__pos == self.size():
                return b""
            buffer = io.BytesIO()
            total_size = self.size()
            chunk = int(self.__pos / (128 * 1024))
            chunk_off = int(self.__pos % (128 * 1024))
            chunk_total = int(math.ceil(total_size / (128 * 1024)))
            self.check_availability(chunk, True, False)
            buffer.write(self.buffer()[chunk][chunk_off:])
            chunk += 1
            if chunk != chunk_total:
                while chunk <= chunk_total - 1:
                    self.check_availability(chunk, True, False)
                    buffer.write(self.buffer()[chunk])
                    chunk += 1
            buffer.seek(0)
            self.__pos += buffer.getbuffer().nbytes
            return buffer.read()
        buffer = io.BytesIO()
        chunk = int(self.__pos / (128 * 1024))
        chunk_off = int(self.__pos % (128 * 1024))
        chunk_end = int(__size / (128 * 1024))
        chunk_end_off = int(__size % (128 * 1024))
        if chunk_end > self.size():
            chunk_end = int(self.size() / (128 * 1024))
            chunk_end_off = int(self.size() % (128 * 1024))
        self.check_availability(chunk, True, False)
        if chunk_off + __size > len(self.buffer()[chunk]):
            buffer.write(self.buffer()[chunk][chunk_off:])
            chunk += 1
            while chunk <= chunk_end:
                self.check_availability(chunk, True, False)
                if chunk == chunk_end:
                    buffer.write(self.buffer()[chunk][:chunk_end_off])
                else:
                    buffer.write(self.buffer()[chunk])
                chunk += 1
        else:
            buffer.write(self.buffer()[chunk][chunk_off:chunk_off + __size])
        buffer.seek(0)
        self.__pos += buffer.getbuffer().nbytes
        return buffer.read()

    def notify_chunk_available(self, index: int) -> None:
        self.available_chunks()[index] = True
        self.__decoded_length += len(self.buffer()[index])
        with self.wait_lock:
            if index == self.wait_for_chunk and not self.closed:
                self.wait_for_chunk = -1
                self.wait_lock.notify_all()

    def notify_chunk_error(self, index: int, ex):
        self.available_chunks()[index] = False
        self.requested_chunks()[index] = False
        self.retries[index] += 1
        with self.wait_lock:
            if index == self.wait_for_chunk and not self.closed:
                self.chunk_exception = ex
                self.wait_for_chunk = -1
                self.wait_lock.notify_all()

    def decoded_length(self):
        return self.__decoded_length

    class ChunkException(IOError):

        @staticmethod
        def from_stream_error(stream_error: int):
            return AbsChunkedInputStream \
                .ChunkException("Failed due to stream error, code: {}".format(stream_error))


class AudioKeyManager(PacketsReceiver, Closeable):
    audio_key_request_timeout = 20
    logger = logging.getLogger("Librespot:AudioKeyManager")
    __callbacks: typing.Dict[int, Callback] = {}
    __seq_holder = 0
    __seq_holder_lock = threading.Condition()
    __session: Session
    __zero_short = b"\x00\x00"

    def __init__(self, session: Session):
        self.__session = session

    def dispatch(self, packet: Packet) -> None:
        payload = io.BytesIO(packet.payload)
        seq = struct.unpack(">i", payload.read(4))[0]
        callback = self.__callbacks.get(seq)
        if callback is None:
            self.logger.warning(
                "Couldn't find callback for seq: {}".format(seq))
            return
        if packet.is_cmd(Packet.Type.aes_key):
            key = payload.read(16)
            callback.key(key)
        elif packet.is_cmd(Packet.Type.aes_key_error):
            code = struct.unpack(">H", payload.read(2))[0]
            callback.error(code)
        else:
            self.logger.warning(
                "Couldn't handle packet, cmd: {}, length: {}".format(
                    packet.cmd, len(packet.payload)))

    def get_audio_key(self,
                      gid: bytes,
                      file_id: bytes,
                      retry: bool = True) -> bytes:
        seq: int
        with self.__seq_holder_lock:
            seq = self.__seq_holder
            self.__seq_holder += 1
        out = io.BytesIO()
        out.write(file_id)
        out.write(gid)
        out.write(struct.pack(">i", seq))
        out.write(self.__zero_short)
        out.seek(0)
        self.__session.send(Packet.Type.request_key, out.read())
        callback = AudioKeyManager.SyncCallback(self)
        self.__callbacks[seq] = callback
        key = callback.wait_response()
        if key is None:
            if retry:
                return self.get_audio_key(gid, file_id, False)
            raise RuntimeError(
                "Failed fetching audio key! gid: {}, fileId: {}".format(
                    util.bytes_to_hex(gid), util.bytes_to_hex(file_id)))
        return key

    class Callback:

        def key(self, key: bytes) -> None:
            raise NotImplementedError

        def error(self, code: int) -> None:
            raise NotImplementedError

    class SyncCallback(Callback):
        __audio_key_manager: AudioKeyManager
        __reference = queue.Queue()
        __reference_lock = threading.Condition()

        def __init__(self, audio_key_manager: AudioKeyManager):
            self.__audio_key_manager = audio_key_manager

        def key(self, key: bytes) -> None:
            with self.__reference_lock:
                self.__reference.put(key)
                self.__reference_lock.notify_all()

        def error(self, code: int) -> None:
            self.__audio_key_manager.logger.fatal(
                "Audio key error, code: {}".format(code))
            with self.__reference_lock:
                self.__reference.put(None)
                self.__reference_lock.notify_all()

        def wait_response(self) -> bytes:
            with self.__reference_lock:
                self.__reference_lock.wait(
                    AudioKeyManager.audio_key_request_timeout)
                return self.__reference.get(block=False)


class CdnFeedHelper:
    _LOGGER: logging = logging.getLogger(__name__)

    @staticmethod
    def get_url(resp: StorageResolve.StorageResolveResponse) -> str:
        selected_url = random.choice(resp.cdnurl)
        while "audio4-gm-fb" in selected_url or "audio-gm-fb" in selected_url:
            selected_url = random.choice(resp.cdnurl)
        return selected_url

    @staticmethod
    def load_track(
            session: Session, track: Metadata.Track, file: Metadata.AudioFile,
            resp_or_url: typing.Union[StorageResolve.StorageResolveResponse,
                                      str], preload: bool,
            halt_listener: HaltListener) -> PlayableContentFeeder.LoadedStream:
        if type(resp_or_url) is str:
            url = resp_or_url
        else:
            url = CdnFeedHelper.get_url(resp_or_url)
        start = int(time.time() * 1000)
        key = session.audio_key().get_audio_key(track.gid, file.file_id)
        audio_key_time = int(time.time() * 1000) - start

        streamer = session.cdn().stream_file(file, key, url, halt_listener)
        input_stream = streamer.stream()
        normalization_data = NormalizationData.read(input_stream)
        if input_stream.skip(0xA7) != 0xA7:
            raise IOError("Couldn't skip 0xa7 bytes!")
        return PlayableContentFeeder.LoadedStream(
            track,
            streamer,
            normalization_data,
            PlayableContentFeeder.Metrics(file.file_id, preload,
                                          -1 if preload else audio_key_time),
        )

    @staticmethod
    def load_episode_external(
            session: Session, episode: Metadata.Episode,
            halt_listener: HaltListener) -> PlayableContentFeeder.LoadedStream:
        resp = session.client().head(episode.external_url)

        if resp.status_code != 200:
            CdnFeedHelper._LOGGER.warning("Couldn't resolve redirect!")

        url = resp.url
        CdnFeedHelper._LOGGER.debug("Fetched external url for {}: {}".format(
            util.bytes_to_hex(episode.gid), url))

        streamer = session.cdn().stream_external_episode(
            episode, url, halt_listener)
        return PlayableContentFeeder.LoadedStream(
            episode,
            streamer,
            None,
            PlayableContentFeeder.Metrics(None, False, -1),
        )

    @staticmethod
    def load_episode(
        session: Session,
        episode: Metadata.Episode,
        file: Metadata.AudioFile,
        resp_or_url: typing.Union[StorageResolve.StorageResolveResponse, str],
        preload: bool,
        halt_listener: HaltListener,
    ) -> PlayableContentFeeder.LoadedStream:
        if type(resp_or_url) is str:
            url = resp_or_url
        else:
            url = CdnFeedHelper.get_url(resp_or_url)
        start = int(time.time() * 1000)
        key = session.audio_key().get_audio_key(episode.gid, file.file_id)
        audio_key_time = int(time.time() * 1000) - start

        streamer = session.cdn().stream_file(file, key, url, halt_listener)
        input_stream = streamer.stream()
        normalization_data = NormalizationData.read(input_stream)
        if input_stream.skip(0xA7) != 0xA7:
            raise IOError("Couldn't skip 0xa7 bytes!")
        return PlayableContentFeeder.LoadedStream(
            episode,
            streamer,
            normalization_data,
            PlayableContentFeeder.Metrics(file.file_id, preload,
                                          -1 if preload else audio_key_time),
        )


class CdnManager:
    logger: logging = logging.getLogger("Librespot:CdnManager")
    __session: Session

    def __init__(self, session: Session):
        self.__session = session

    def get_head(self, file_id: bytes):
        response = self.__session.client() \
            .get(self.__session.get_user_attribute("head-files-url", "https://heads-fa.spotify.com/head/{file_id}")
                 .replace("{file_id}", util.bytes_to_hex(file_id)))
        if response.status_code != 200:
            raise IOError("{}".format(response.status_code))
        body = response.content
        if body is None:
            raise IOError("Response body is empty!")
        return body

    def stream_external_episode(self, episode: Metadata.Episode,
                                external_url: str,
                                halt_listener: HaltListener):
        return CdnManager.Streamer(
            self.__session,
            StreamId(episode=episode),
            SuperAudioFormat.MP3,
            CdnManager.CdnUrl(self, None, external_url),
            self.__session.cache(),
            NoopAudioDecrypt(),
            halt_listener,
        )

    def stream_file(self, file: Metadata.AudioFile, key: bytes, url: str,
                    halt_listener: HaltListener):
        return CdnManager.Streamer(
            self.__session,
            StreamId(file=file),
            SuperAudioFormat.get(file.format),
            CdnManager.CdnUrl(self, file.file_id, url),
            self.__session.cache(),
            AesAudioDecrypt(key),
            halt_listener,
        )

    def get_audio_url(self, file_id: bytes):
        response = self.__session.api()\
            .send("GET", "/storage-resolve/files/audio/interactive/{}".format(util.bytes_to_hex(file_id)), None, None)
        if response.status_code != 200:
            raise IOError(response.status_code)
        body = response.content
        if body is None:
            raise IOError("Response body is empty!")
        proto = StorageResolve.StorageResolveResponse()
        proto.ParseFromString(body)
        if proto.result == StorageResolve.StorageResolveResponse.Result.CDN:
            url = random.choice(proto.cdnurl)
            self.logger.debug("Fetched CDN url for {}: {}".format(
                util.bytes_to_hex(file_id), url))
            return url
        raise CdnManager.CdnException(
            "Could not retrieve CDN url! result: {}".format(proto.result))

    class CdnException(Exception):
        pass

    class InternalResponse:
        buffer: bytes
        headers: typing.Dict[str, str]

        def __init__(self, buffer: bytes, headers: typing.Dict[str, str]):
            self.buffer = buffer
            self.headers = headers

    class CdnUrl:
        __cdn_manager = None
        __file_id: bytes
        __expiration: int
        url: str

        def __init__(self, cdn_manager, file_id: typing.Union[bytes, None],
                     url: str):
            self.__cdn_manager: CdnManager = cdn_manager
            self.__file_id = file_id
            self.set_url(url)

        def url(self):
            if self.__expiration == -1:
                return self.url
            if self.__expiration <= int(time.time() * 1000) + 5 * 60 * 1000:
                self.url = self.__cdn_manager.get_audio_url(self.__file_id)
            return self.url

        def set_url(self, url: str):
            self.url = url
            if self.__file_id is not None:
                token_url = urllib.parse.urlparse(url)
                token_query = urllib.parse.parse_qs(token_url.query)
                token_list = token_query.get("__token__")
                try:
                    token_str = str(token_list[0])
                except TypeError:
                    token_str = ""
                expires_list = token_query.get("Expires")
                try:
                    expires_str = str(expires_list[0])
                except TypeError:
                    expires_str = ""
                if token_str != "None" and len(token_str) != 0:
                    expire_at = None
                    split = token_str.split("~")
                    for s in split:
                        try:
                            i = s.index("=")
                        except ValueError:
                            continue
                        if s[:i] == "exp":
                            expire_at = int(s[i + 1:])
                            break
                    if expire_at is None:
                        self.__expiration = -1
                        self.__cdn_manager.logger.warning(
                            "Invalid __token__ in CDN url: {}".format(url))
                        return
                    self.__expiration = expire_at * 1000
                elif expires_str != "None" and len(expires_str) != 0:
                    expires_at = None
                    expires_str = expires_str.split("~")[0]
                    expires_at = int(expires_str)
                    if expires_at is None:
                        self.__expiration = -1
                        self.__cdn_manager.logger.warning("Invalid Expires param in CDN url: {}".format(url))
                        return
                    self.__expiration = expires_at * 1000
                else:
                    try:
                        i = token_url.query.index("_")
                    except ValueError:
                        self.__expiration = -1
                        self.__cdn_manager.logger \
                            .warning("Couldn't extract expiration, invalid parameter in CDN url: {}".format(url))
                        return
                    self.__expiration = int(token_url.query[:i]) * 1000

            else:
                self.__expiration = -1

    class Streamer(GeneralAudioStream, GeneralWritableStream):
        available: typing.List[bool]
        buffer: typing.List[bytes]
        chunks: int
        executor_service = concurrent.futures.ThreadPoolExecutor()
        halt_listener: HaltListener
        requested: typing.List[bool]
        size: int
        __audio_format: SuperAudioFormat
        __audio_decrypt: AudioDecrypt
        __cdn_url: CdnManager.CdnUrl
        __internal_stream: InternalStream
        __session: Session
        __stream_id: StreamId

        def __init__(self, session: Session, stream_id: StreamId,
                     audio_format: SuperAudioFormat,
                     cdn_url: CdnManager.CdnUrl, cache: CacheManager,
                     audio_decrypt: AudioDecrypt, halt_listener: HaltListener):
            self.__session = session
            self.__stream_id = stream_id
            self.__audio_format = audio_format
            self.__audio_decrypt = audio_decrypt
            self.__cdn_url = cdn_url
            self.halt_listener = halt_listener
            response = self.request(range_start=0,
                                    range_end=ChannelManager.chunk_size - 1)
            content_range = response.headers.get("Content-Range")
            if content_range is None:
                raise IOError("Missing Content-Range header!")
            split = content_range.split("/")
            self.size = int(split[1])
            self.chunks = int(math.ceil(self.size / ChannelManager.chunk_size))
            first_chunk = response.buffer
            self.available = [False for _ in range(self.chunks)]
            self.requested = [False for _ in range(self.chunks)]
            self.buffer = [b"" for _ in range(self.chunks)]
            self.__internal_stream = CdnManager.Streamer.InternalStream(
                self, False)
            self.requested[0] = True
            self.write_chunk(first_chunk, 0, False)

        def write_chunk(self, chunk: bytes, chunk_index: int,
                        cached: bool) -> None:
            if self.__internal_stream.is_closed():
                return
            self.__session.logger.debug(
                "Chunk {}/{} completed, cached: {}, stream: {}".format(
                    chunk_index + 1, self.chunks, cached, self.describe()))
            self.buffer[chunk_index] = self.__audio_decrypt.decrypt_chunk(
                chunk_index, chunk)
            self.__internal_stream.notify_chunk_available(chunk_index)

        def stream(self) -> AbsChunkedInputStream:
            return self.__internal_stream

        def codec(self) -> SuperAudioFormat:
            return self.__audio_format

        def describe(self) -> str:
            if self.__stream_id.is_episode():
                return "episode_gid: {}".format(
                    self.__stream_id.get_episode_gid())
            return "file_id: {}".format(self.__stream_id.get_file_id())

        def decrypt_time_ms(self) -> int:
            return self.__audio_decrypt.decrypt_time_ms()

        def request_chunk(self, index: int) -> None:
            response = self.request(index)
            self.write_chunk(response.buffer, index, False)

        def request(self, chunk: int = None, range_start: int = None, range_end: int = None)\
                -> CdnManager.InternalResponse:
            if chunk is None and range_start is None and range_end is None:
                raise TypeError()
            if chunk is not None:
                range_start = ChannelManager.chunk_size * chunk
                range_end = (chunk + 1) * ChannelManager.chunk_size - 1
            response = self.__session.client().get(
                self.__cdn_url.url,
                headers={
                    "Range": "bytes={}-{}".format(range_start, range_end)
                },
            )
            if response.status_code != 206:
                raise IOError(response.status_code)
            body = response.content
            if body is None:
                raise IOError("Response body is empty!")
            return CdnManager.InternalResponse(body, dict(response.headers))

        class InternalStream(AbsChunkedInputStream):
            streamer: CdnManager.Streamer

            def __init__(self, streamer, retry_on_chunk_error: bool):
                self.streamer: CdnManager.Streamer = streamer
                super().__init__(retry_on_chunk_error)

            def buffer(self) -> typing.List[bytes]:
                return self.streamer.buffer

            def size(self) -> int:
                return self.streamer.size

            def close(self) -> None:
                super().close()
                del self.streamer.buffer

            def requested_chunks(self) -> typing.List[bool]:
                return self.streamer.requested

            def available_chunks(self) -> typing.List[bool]:
                return self.streamer.available

            def chunks(self) -> int:
                return self.streamer.chunks

            def request_chunk_from_stream(self, index: int) -> None:
                self.streamer.executor_service \
                    .submit(lambda: self.streamer.request_chunk(index))

            def stream_read_halted(self, chunk: int, _time: int) -> None:
                if self.streamer.halt_listener is not None:
                    self.streamer.executor_service\
                        .submit(lambda: self.streamer.halt_listener.stream_read_halted(chunk, _time))

            def stream_read_resumed(self, chunk: int, _time: int) -> None:
                if self.streamer.halt_listener is not None:
                    self.streamer.executor_service \
                        .submit(lambda: self.streamer.halt_listener.stream_read_resumed(chunk, _time))


class NormalizationData:
    _LOGGER: logging = logging.getLogger(__name__)
    track_gain_db: float
    track_peak: float
    album_gain_db: float
    album_peak: float

    def __init__(self, track_gain_db: float, track_peak: float,
                 album_gain_db: float, album_peak: float):
        self.track_gain_db = track_gain_db
        self.track_peak = track_peak
        self.album_gain_db = album_gain_db
        self.album_peak = album_peak

        self._LOGGER.debug(
            "Loaded normalization data, track_gain: {}, track_peak: {}, album_gain: {}, album_peak: {}"
            .format(track_gain_db, track_peak, album_gain_db, album_peak))

    @staticmethod
    def read(input_stream: AbsChunkedInputStream) -> NormalizationData:
        input_stream.seek(144)
        data = input_stream.read(4 * 4)
        input_stream.seek(0)
        buffer = io.BytesIO(data)
        return NormalizationData(
            struct.unpack("<f", buffer.read(4))[0],
            struct.unpack("<f", buffer.read(4))[0],
            struct.unpack("<f", buffer.read(4))[0],
            struct.unpack("<f", buffer.read(4))[0])

    def get_factor(self, normalisation_pregain) -> float:
        normalisation_factor = float(
            math.pow(10, (self.track_gain_db + normalisation_pregain) / 20))
        if normalisation_factor * self.track_peak > 1:
            self._LOGGER \
                .warning("Reducing normalisation factor to prevent clipping. Please add negative pregain to avoid.")
            normalisation_factor = 1 / self.track_peak
        return normalisation_factor


class PlayableContentFeeder:
    logger = logging.getLogger("Librespot:PlayableContentFeeder")
    storage_resolve_interactive = "/storage-resolve/files/audio/interactive/{}"
    storage_resolve_interactive_prefetch = "/storage-resolve/files/audio/interactive_prefetch/{}"
    __session: Session

    def __init__(self, session: Session):
        self.__session = session

    def load(self, playable_id: PlayableId,
             audio_quality_picker: AudioQualityPicker, preload: bool,
             halt_listener: typing.Union[HaltListener, None]):
        if type(playable_id) is TrackId:
            return self.load_track(playable_id, audio_quality_picker, preload,
                                   halt_listener)
        if type(playable_id) is EpisodeId:
            return self.load_episode(playable_id, audio_quality_picker,
                                     preload, halt_listener)
        raise TypeError("Unknown content: {}".format(playable_id))

    def load_stream(self, file: Metadata.AudioFile, track: Metadata.Track,
                    episode: Metadata.Episode, preload: bool,
                    halt_lister: HaltListener):
        if track is None and episode is None:
            raise RuntimeError()
        response = self.resolve_storage_interactive(file.file_id, preload)
        if response.result == StorageResolve.StorageResolveResponse.Result.CDN:
            if track is not None:
                return CdnFeedHelper.load_track(self.__session, track, file,
                                                response, preload, halt_lister)
            return CdnFeedHelper.load_episode(self.__session, episode, file,
                                              response, preload, halt_lister)
        if response.result == StorageResolve.StorageResolveResponse.Result.STORAGE:
            if track is None:
                pass
        elif response.result == StorageResolve.StorageResolveResponse.Result.RESTRICTED:
            raise RuntimeError("Content is restricted!")
        elif response.result == StorageResolve.StorageResolveResponse.Response.UNRECOGNIZED:
            raise RuntimeError("Content is unrecognized!")
        else:
            raise RuntimeError("Unknown result: {}".format(response.result))

    def load_episode(self, episode_id: EpisodeId,
                     audio_quality_picker: AudioQualityPicker, preload: bool,
                     halt_listener: HaltListener) -> LoadedStream:
        episode = self.__session.api().get_metadata_4_episode(episode_id)
        if episode.external_url:
            return CdnFeedHelper.load_episode_external(self.__session, episode,
                                                       halt_listener)
        file = audio_quality_picker.get_file(episode.audio)
        if file is None:
            self.logger.fatal(
                "Couldn't find any suitable audio file, available: {}".format(
                    episode.audio))
        return self.load_stream(file, None, episode, preload, halt_listener)

    def load_track(self, track_id_or_track: typing.Union[TrackId,
                                                         Metadata.Track],
                   audio_quality_picker: AudioQualityPicker, preload: bool,
                   halt_listener: HaltListener):
        if type(track_id_or_track) is TrackId:
            original = self.__session.api().get_metadata_4_track(
                track_id_or_track)
            track = self.pick_alternative_if_necessary(original)
            if track is None:
                raise RuntimeError("Cannot get alternative track")
        else:
            track = track_id_or_track
        file = audio_quality_picker.get_file(track.file)
        if file is None:
            self.logger.fatal(
                "Couldn't find any suitable audio file, available: {}".format(
                    track.file))
            raise FeederException()
        return self.load_stream(file, track, None, preload, halt_listener)

    def pick_alternative_if_necessary(
            self, track: Metadata.Track) -> typing.Union[Metadata.Track, None]:
        if len(track.file) > 0:
            return track
        for alt in track.alternative:
            if len(alt.file) > 0:
                return Metadata.Track(
                    gid=track.gid,
                    name=track.name,
                    album=track.album,
                    artist=track.artist,
                    number=track.number,
                    disc_number=track.disc_number,
                    duration=track.duration,
                    popularity=track.popularity,
                    explicit=track.explicit,
                    external_id=track.external_id,
                    restriction=track.restriction,
                    file=alt.file,
                    sale_period=track.sale_period,
                    preview=track.preview,
                    tags=track.tags,
                    earliest_live_timestamp=track.earliest_live_timestamp,
                    has_lyrics=track.has_lyrics,
                    availability=track.availability,
                    licensor=track.licensor)
        return None

    def resolve_storage_interactive(
            self, file_id: bytes,
            preload: bool) -> StorageResolve.StorageResolveResponse:
        resp = self.__session.api().send(
            "GET",
            (self.storage_resolve_interactive_prefetch
             if preload else self.storage_resolve_interactive).format(
                 util.bytes_to_hex(file_id)),
            None,
            None,
        )
        if resp.status_code != 200:
            raise RuntimeError(resp.status_code)
        body = resp.content
        if body is None:
            raise RuntimeError("Response body is empty!")
        storage_resolve_response = StorageResolve.StorageResolveResponse()
        storage_resolve_response.ParseFromString(body)
        return storage_resolve_response

    class LoadedStream:
        episode: Metadata.Episode
        track: Metadata.Track
        input_stream: GeneralAudioStream
        normalization_data: NormalizationData
        metrics: PlayableContentFeeder.Metrics

        def __init__(self, track_or_episode: typing.Union[Metadata.Track,
                                                          Metadata.Episode],
                     input_stream: GeneralAudioStream,
                     normalization_data: typing.Union[NormalizationData, None],
                     metrics: PlayableContentFeeder.Metrics):
            if type(track_or_episode) is Metadata.Track:
                self.track = track_or_episode
                self.episode = None
            elif type(track_or_episode) is Metadata.Episode:
                self.track = None
                self.episode = track_or_episode
            else:
                raise TypeError()
            self.input_stream = input_stream
            self.normalization_data = normalization_data
            self.metrics = metrics

    class Metrics:
        file_id: str
        preloaded_audio_key: bool
        audio_key_time: int

        def __init__(self, file_id: typing.Union[bytes, None],
                     preloaded_audio_key: bool, audio_key_time: int):
            self.file_id = None if file_id is None else util.bytes_to_hex(
                file_id)
            self.preloaded_audio_key = preloaded_audio_key
            self.audio_key_time = audio_key_time
            if preloaded_audio_key and audio_key_time != -1:
                raise RuntimeError()


class StreamId:
    file_id: bytes
    episode_gid: bytes

    def __init__(self,
                 file: Metadata.AudioFile = None,
                 episode: Metadata.Episode = None):
        if file is None and episode is None:
            return
        self.file_id = None if file is None else file.file_id
        self.episode_gid = None if episode is None else episode.gid

    def get_file_id(self):
        if self.file_id is None:
            raise RuntimeError("Not a file!")
        return util.bytes_to_hex(self.file_id)

    def is_episode(self):
        return self.episode_gid is not None

    def get_episode_gid(self):
        if self.episode_gid is None:
            raise RuntimeError("Not an episode!")
        return util.bytes_to_hex(self.episode_gid)
