from librespot.proto import Mercury
import typing


class RawMercuryRequest:
    header: Mercury.Header
    payload: typing.List[bytes]

    def __init__(self, header: Mercury.Header, payload: typing.List[bytes]):
        self.header = header
        self.payload = payload

    @staticmethod
    def sub(uri: str):
        return RawMercuryRequest.new_builder().set_uri(uri).set_method(
            "SUB").build()

    @staticmethod
    def unsub(uri: str):
        return RawMercuryRequest.new_builder().set_uri(uri).set_method(
            "UNSUB").build()

    @staticmethod
    def get(uri: str):
        return RawMercuryRequest.new_builder().set_uri(uri).set_method(
            "GET").build()

    @staticmethod
    def send(uri: str, part: bytes):
        return RawMercuryRequest.new_builder().set_uri(uri).add_payload_part(
            part).set_method("SEND").build()

    @staticmethod
    def post(uri: str, part: bytes):
        return RawMercuryRequest.new_builder().set_uri(uri).set_method(
            "POST").add_payload_part(part).build()

    @staticmethod
    def new_builder():
        return RawMercuryRequest.Builder()

    class Builder:
        header_dict: dict
        payload: typing.List[bytes]

        def __init__(self):
            self.header_dict = {}
            self.payload = []

        def set_uri(self, uri: str):
            self.header_dict["uri"] = uri
            return self

        def set_content_type(self, content_type: str):
            self.header_dict["content_type"] = content_type
            return self

        def set_method(self, method: str):
            self.header_dict["method"] = method
            return self

        def add_user_field(self,
                           field: Mercury.UserField = None,
                           key: str = None,
                           value: str = None):
            if field is None and (key is None or value is None):
                return self
            try:
                self.header_dict["user_fields"]
            except KeyError:
                self.header_dict["user_fields"] = []
            if field is not None:
                self.header_dict["user_fields"].append(field)
            if key is not None and value is not None:
                self.header_dict["user_fields"].append(
                    Mercury.UserField(key=key, value=value.encode()))
            return self

        def add_payload_part(self, part: bytes):
            self.payload.append(part)
            return self

        def add_protobuf_payload(self, msg):
            return self.add_payload_part(msg)

        def build(self):
            return RawMercuryRequest(Mercury.Header(**self.header_dict),
                                     self.payload)
