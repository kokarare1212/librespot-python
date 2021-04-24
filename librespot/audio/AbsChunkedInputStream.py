from librespot.audio.HaltListener import HaltListener
from librespot.audio.storage import ChannelManager
from librespot.standard.InputStream import InputStream
import math
import threading
import time
import typing


class AbsChunkedInputStream(InputStream, HaltListener):
    preload_ahead: typing.Final[int] = 3
    preload_chunk_retries: typing.Final[int] = 2
    max_chunk_tries: typing.Final[int] = 128
    wait_lock: threading.Condition = threading.Condition()
    retries: typing.List[int]
    retry_on_chunk_error: bool
    chunk_exception = None
    wait_for_chunk: int = -1
    _pos: int = 0
    _mark: int = 0
    closed: bool = False
    _decoded_length: int = 0

    def __init__(self, retry_on_chunk_error: bool):
        self.retries: typing.Final[typing.List[int]] = [
            0 for _ in range(self.chunks())
        ]
        self.retry_on_chunk_error = retry_on_chunk_error

    def is_closed(self) -> bool:
        return self.closed

    def buffer(self) -> typing.List[bytearray]:
        raise NotImplementedError()

    def size(self) -> int:
        raise NotImplementedError()

    def close(self) -> None:
        self.closed = True

        with self.wait_lock:
            self.wait_lock.notify_all()

    def available(self):
        return self.size() - self._pos

    def mark_supported(self) -> bool:
        return True

    def mark(self, read_ahead_limit: int) -> None:
        self._mark = self._pos

    def reset(self) -> None:
        self._pos = self._mark

    def pos(self) -> int:
        return self._pos

    def seek(self, where: int) -> None:
        if where < 0:
            raise TypeError()
        if self.closed:
            raise IOError("Stream is closed!")
        self._pos = where

        self.check_availability(int(self._pos / ChannelManager.CHUNK_SIZE),
                                False, False)

    def skip(self, n: int) -> int:
        if n < 0:
            raise TypeError()
        if self.closed:
            raise IOError("Stream is closed!")

        k = self.size() - self._pos
        if n < k:
            k = n
        self._pos += k

        chunk = int(self._pos / ChannelManager.CHUNK_SIZE)
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
            if self.requested_chunks(
            )[i] and self.retries[i] < self.preload_chunk_retries:
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
                self.wait_lock.wait()

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

    def read(self,
             b: bytearray = None,
             offset: int = None,
             length: int = None) -> int:
        if b is None and offset is None and length is None:
            return self.internal_read()
        if not (b is not None and offset is not None and length is not None):
            raise TypeError()

        if self.closed:
            raise IOError("Stream is closed!")

        if offset < 0 or length < 0 or length > len(b) - offset:
            raise IndexError("offset: {}, length: {}, buffer: {}".format(
                offset, length, len(b)))
        elif length == 0:
            return 0

        if self._pos >= self.size():
            return -1

        i = 0
        while True:
            chunk = int(self._pos / ChannelManager.CHUNK_SIZE)
            chunk_off = int(self._pos % ChannelManager.CHUNK_SIZE)

            self.check_availability(chunk, True, False)

            copy = min(len(self.buffer()[chunk]) - chunk_off, length - i)
            b[offset + 0:copy] = self.buffer()[chunk][chunk_off:chunk_off +
                                                      copy]
            i += copy
            self._pos += copy

            if i == length or self._pos >= self.size():
                return i

    def internal_read(self) -> int:
        if self.closed:
            raise IOError("Stream is closed!")

        if self._pos >= self.size():
            return -1

        chunk = int(self._pos / ChannelManager.CHUNK_SIZE)
        self.check_availability(chunk, True, False)

        b = self.buffer()[chunk][self._pos % ChannelManager.CHUNK_SIZE]
        self._pos = self._pos + 1
        return b

    def notify_chunk_available(self, index: int) -> None:
        self.available_chunks()[index] = True
        self._decoded_length += len(self.buffer()[index])

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
        return self._decoded_length

    class ChunkException(IOError):
        @staticmethod
        def from_stream_error(stream_error: int):
            return AbsChunkedInputStream.ChunkException(
                "Failed due to stream error, code: {}".format(stream_error))
