class HaltListener:
    def stream_read_halted(self, chunk: int, _time: int) -> None:
        pass

    def stream_read_resumed(self, chunk: int, _time: int):
        pass
