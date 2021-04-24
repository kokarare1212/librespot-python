from __future__ import annotations

import queue

from librespot.audio.storage import AudioFile
from librespot.common import Utils
from librespot.core import PacketsReceiver, Session
from librespot.crypto import Packet
from librespot.standard import BytesInputStream, BytesOutputStream, Closeable, Runnable
import concurrent.futures
import logging
import threading
import typing


class ChannelManager(Closeable, PacketsReceiver.PacketsReceiver):
    CHUNK_SIZE: int = 128 * 1024
    _LOGGER: logging = logging.getLogger(__name__)
    _channels: typing.Dict[int, Channel] = {}
    _seqHolder: int = 0
    _seqHolderLock: threading.Condition = threading.Condition()
    _executorService: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(
    )
    _session: Session = None

    def __init__(self, session: Session):
        self._session = session

    def request_chunk(self, file_id: bytes, index: int, file: AudioFile):
        start = int(index * self.CHUNK_SIZE / 4)
        end = int((index + 1) * self.CHUNK_SIZE / 4)

        channel = ChannelManager.Channel(self, file, index)
        self._channels[channel.chunkId] = channel

        out = BytesOutputStream()
        out.write_short(channel.chunkId)
        out.write_int(0x00000000)
        out.write_int(0x00000000)
        out.write_int(0x00004e20)
        out.write_int(0x00030d40)
        out.write(file_id)
        out.write_int(start)
        out.write_int(end)

        self._session.send(Packet.Type.stream_chunk, out.buffer)

    def dispatch(self, packet: Packet) -> None:
        payload = BytesInputStream(packet.payload)
        if packet.is_cmd(Packet.Type.stream_chunk_res):
            chunk_id = payload.read_short()
            channel = self._channels.get(chunk_id)
            if channel is None:
                self._LOGGER.warning(
                    "Couldn't find channel, id: {}, received: {}".format(
                        chunk_id, len(packet.payload)))
                return

            channel._add_to_queue(payload)
        elif packet.is_cmd(Packet.Type.channel_error):
            chunk_id = payload.read_short()
            channel = self._channels.get(chunk_id)
            if channel is None:
                self._LOGGER.warning(
                    "Dropping channel error, id: {}, code: {}".format(
                        chunk_id, payload.read_short()))
                return

            channel.stream_error(payload.read_short())
        else:
            self._LOGGER.warning(
                "Couldn't handle packet, cmd: {}, payload: {}".format(
                    packet.cmd, Utils.Utils.bytes_to_hex(packet.payload)))

    def close(self) -> None:
        self._executorService.shutdown()

    class Channel:
        _channelManager: ChannelManager
        chunkId: int
        _q: queue.Queue = queue.Queue()
        _file: AudioFile
        _chunkIndex: int
        _buffer: BytesOutputStream = BytesOutputStream()
        _header: bool = True

        def __init__(self, channel_manager: ChannelManager, file: AudioFile,
                     chunk_index: int):
            self._channelManager = channel_manager
            self._file = file
            self._chunkIndex = chunk_index
            with self._channelManager._seqHolderLock:
                self.chunkId = self._channelManager._seqHolder
                self._channelManager._seqHolder += 1

            self._channelManager._executorService.submit(
                lambda: ChannelManager.Channel.Handler(self))

        def _handle(self, payload: BytesInputStream) -> bool:
            if len(payload.buffer) == 0:
                if not self._header:
                    self._file.write_chunk(bytearray(payload.buffer),
                                           self._chunkIndex, False)
                    return True

                self._channelManager._LOGGER.debug(
                    "Received empty chunk, skipping.")
                return False

            if self._header:
                length: int
                while len(payload.buffer) > 0:
                    length = payload.read_short()
                    if not length > 0:
                        break
                    header_id = payload.read_byte()
                    header_data = payload.read(length - 1)
                    self._file.write_header(int.from_bytes(header_id, "big"),
                                            bytearray(header_data), False)
                self._header = False
            else:
                self._buffer.write(payload.read(len(payload.buffer)))

            return False

        def _add_to_queue(self, payload):
            self._q.put(payload)

        def stream_error(self, code: int) -> None:
            self._file.stream_error(self._chunkIndex, code)

        class Handler(Runnable):
            _channel: ChannelManager.Channel = None

            def __init__(self, channel: ChannelManager.Channel):
                self._channel = channel

            def run(self) -> None:
                self._channel._channelManager._LOGGER.debug(
                    "ChannelManager.Handler is starting")

                with self._channel._q.all_tasks_done:
                    self._channel._channelManager._channels.pop(
                        self._channel.chunkId)

                self._channel._channelManager._LOGGER.debug(
                    "ChannelManager.Handler is shutting down")
