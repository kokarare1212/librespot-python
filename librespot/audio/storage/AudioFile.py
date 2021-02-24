from librespot.audio.GeneralWritableStream import GeneralWritableStream


class AudioFile(GeneralWritableStream):
    def write_chunk(self, buffer: bytearray, chunk_index: int, cached: bool):
        pass

    def write_header(self, chunk_id: int, b: bytearray, cached: bool):
        pass

    def stream_error(self, chunk_index: int, code: int):
        pass
