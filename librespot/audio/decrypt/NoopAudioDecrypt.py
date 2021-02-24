from librespot.audio.decrypt import AudioDecrypt


class NoopAudioDecrypt(AudioDecrypt):
    def decrypt_chunk(self, chunk_index: int, buffer: bytes):
        pass

    def decrypt_time_ms(self):
        return 0
