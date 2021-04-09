from __future__ import annotations
from librespot.common import Utils
from librespot.core import Session
from librespot.core.PacketsReceiver import PacketsReceiver
from librespot.crypto import Packet
from librespot.standard import BytesInputStream, ByteArrayOutputStream
import logging
import queue
import threading


class AudioKeyManager(PacketsReceiver):
    _ZERO_SHORT: bytes = bytes([0, 0])
    _LOGGER: logging = logging.getLogger(__name__)
    _AUDIO_KEY_REQUEST_TIMEOUT: int = 20
    _seqHolder: int = 0
    _seqHolderLock: threading.Condition = threading.Condition()
    _callbacks: dict[int, AudioKeyManager.Callback] = {}
    _session: Session = None

    def __init__(self, session: Session):
        self._session = session

    def get_audio_key(self,
                      gid: bytes,
                      file_id: bytes,
                      retry: bool = True) -> bytes:
        seq: int
        with self._seqHolderLock:
            seq = self._seqHolder
            self._seqHolder += 1

        out = ByteArrayOutputStream()
        out.write(buffer=bytearray(file_id))
        out.write(buffer=bytearray(gid))
        out.write(buffer=bytearray(Utils.to_byte_array(seq)))
        out.write(buffer=bytearray(self._ZERO_SHORT))

        self._session.send(Packet.Type.request_key, out.to_bytes())

        callback = AudioKeyManager.SyncCallback(self)
        self._callbacks[seq] = callback

        key = callback.wait_response()
        if key is None:
            if retry:
                return self.get_audio_key(gid, file_id, False)
            raise RuntimeError(
                "Failed fetching audio key! gid: {}, fileId: {}".format(
                    Utils.Utils.bytes_to_hex(gid),
                    Utils.Utils.bytes_to_hex(file_id)))

        return key

    def dispatch(self, packet: Packet) -> None:
        payload = BytesInputStream(packet.payload)
        seq = payload.read_int()

        callback = self._callbacks.get(seq)
        if callback is None:
            self._LOGGER.warning(
                "Couldn't find callback for seq: {}".format(seq))
            return

        if packet.is_cmd(Packet.Type.aes_key):
            key = payload.read(16)
            callback.key(key)
        elif packet.is_cmd(Packet.Type.aes_key_error):
            code = payload.read_short()
            callback.error(code)
        else:
            self._LOGGER.warning(
                "Couldn't handle packet, cmd: {}, length: {}".format(
                    packet.cmd, len(packet.payload)))

    class Callback:
        def key(self, key: bytes) -> None:
            pass

        def error(self, code: int) -> None:
            pass

    class SyncCallback(Callback):
        _audioKeyManager: AudioKeyManager
        reference = queue.Queue()
        reference_lock = threading.Condition()

        def __init__(self, audio_key_manager: AudioKeyManager):
            self._audioKeyManager = audio_key_manager

        def key(self, key: bytes) -> None:
            with self.reference_lock:
                self.reference.put(key)
                self.reference_lock.notify_all()

        def error(self, code: int) -> None:
            self._audioKeyManager._LOGGER.fatal(
                "Audio key error, code: {}".format(code))
            with self.reference_lock:
                self.reference.put(None)
                self.reference_lock.notify_all()

        def wait_response(self) -> bytes:
            with self.reference_lock:
                self.reference_lock.wait(
                    AudioKeyManager._AUDIO_KEY_REQUEST_TIMEOUT)
                return self.reference.get(block=False)

    class AesKeyException(IOError):
        def __init__(self, ex):
            super().__init__(ex)
