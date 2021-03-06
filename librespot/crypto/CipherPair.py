from librespot.crypto.Packet import Packet
from librespot.crypto.Shannon import Shannon
import struct


class CipherPair:
    send_cipher: Shannon
    receive_cipher: Shannon
    send_nonce = 0
    receive_nonce = 0

    def __init__(self, send_key: bytes, receive_key: bytes):
        self.send_cipher = Shannon()
        self.send_cipher.key(send_key)
        self.send_nonce = 0

        self.receive_cipher = Shannon()
        self.receive_cipher.key(receive_key)
        self.receive_nonce = 0

    def send_encoded(self, conn, cmd: bytes, payload: bytes):
        self.send_cipher.nonce(self.send_nonce)
        self.send_nonce += 1

        buffer = b""
        buffer += cmd
        buffer += struct.pack(">H", len(payload))
        buffer += payload

        buffer = self.send_cipher.encrypt(buffer)

        mac = self.send_cipher.finish(4)

        conn.write(buffer)
        conn.write(mac)
        conn.flush()

    def receive_encoded(self, conn) -> Packet:
        try:
            self.receive_cipher.nonce(self.receive_nonce)
            self.receive_nonce += 1

            header_bytes = self.receive_cipher.decrypt(conn.read(3))

            cmd = struct.pack(">s", bytes([header_bytes[0]]))
            payload_length = (header_bytes[1] << 8) | (header_bytes[2] & 0xff)

            payload_bytes = self.receive_cipher.decrypt(
                conn.read(payload_length))

            mac = conn.read(4)

            expected_mac = self.receive_cipher.finish(4)
            if mac != expected_mac:
                raise RuntimeError()

            return Packet(cmd, payload_bytes)
        except IndexError:
            raise RuntimeError()
