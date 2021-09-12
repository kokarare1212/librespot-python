from __future__ import annotations
from Cryptodome.Cipher import AES
from Cryptodome.Util import Counter
from librespot.audio.storage import ChannelManager
from librespot.structure import AudioDecrypt
import io
import time


class AesAudioDecrypt(AudioDecrypt):
    audio_aes_iv = b'r\xe0g\xfb\xdd\xcb\xcfw\xeb\xe8\xbcd?c\r\x93'
    cipher = None
    decrypt_count = 0
    decrypt_total_time = 0
    iv_int = int.from_bytes(audio_aes_iv, "big")
    iv_diff = 0x100
    key: bytes

    def __init__(self, key: bytes):
        self.key = key

    def decrypt_chunk(self, chunk_index: int, buffer: bytes):
        new_buffer = io.BytesIO()
        iv = self.iv_int + int(ChannelManager.chunk_size * chunk_index / 16)
        start = time.time_ns()
        for i in range(0, len(buffer), 4096):
            cipher = AES.new(key=self.key,
                             mode=AES.MODE_CTR,
                             counter=Counter.new(128, initial_value=iv))
            count = min(4096, len(buffer) - i)
            decrypted_buffer = cipher.decrypt(buffer[i:i + count])
            new_buffer.write(decrypted_buffer)
            if count != len(decrypted_buffer):
                raise RuntimeError(
                    "Couldn't process all data, actual: {}, expected: {}".
                    format(len(decrypted_buffer), count))
            iv += self.iv_diff
        self.decrypt_total_time += time.time_ns() - start
        self.decrypt_count += 1
        new_buffer.seek(0)
        return new_buffer.read()

    def decrypt_time_ms(self):
        return 0 if self.decrypt_count == 0 else int(
            (self.decrypt_total_time / self.decrypt_count) / 1000000)
