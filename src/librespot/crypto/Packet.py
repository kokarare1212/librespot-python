import re


class Packet:
    cmd: bytes
    payload: bytes

    def __init__(self, cmd: bytes, payload: bytes):
        self.cmd = cmd
        self.payload = payload

    def is_cmd(self, cmd: bytes):
        return cmd == self.cmd

    class Type:
        secret_block = b"\x02"
        ping = b"\x04"
        stream_chunk = b"\x08"
        stream_chunk_res = b"\x09"
        channel_error = b"\x0a"
        channel_abort = b"\x0b"
        request_key = b"\x0c"
        aes_key = b"\x0d"
        aes_key_error = b"\x0e"
        image = b"\x19"
        country_code = b"\x1b"
        pong = b"\x49"
        pong_ack = b"\x4a"
        pause = b"\x4b"
        product_info = b"\x50"
        legacy_welcome = b"\x69"
        license_version = b"\x76"
        login = b"\xab"
        ap_welcome = b"\xac"
        auth_failure = b"\xad"
        mercury_req = b"\xb2"
        mercury_sub = b"\xb3"
        mercury_unsub = b"\xb4"
        mercury_event = b"\xb5"
        track_ended_time = b"\x82"
        unknown_data_all_zeros = b"\x1f"
        preferred_locale = b"\x74"
        unknown_0x4f = b"\x4f"
        unknown_0x0f = b"\x0f"
        unknown_0x10 = b"\x10"

        @staticmethod
        def parse(val: bytes):
            for cmd in [
                    Packet.Type.__dict__[attr]
                    for attr in Packet.Type.__dict__.keys()
                    if re.search("__.+?__", attr) is None
                    and type(Packet.Type.__dict__[attr]) is bytes
            ]:
                if cmd == val:
                    return cmd

            return None

        @staticmethod
        def for_method(method: str):
            if method == "SUB":
                return Packet.Type.mercury_sub
            if method == "UNSUB":
                return Packet.Type.mercury_unsub
            return Packet.Type.mercury_req
