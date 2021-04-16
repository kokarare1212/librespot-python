from librespot.common.Utils import Utils
import os


class DiffieHellman:
    prime_bytes: bytearray = bytes(
        [
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xC9,
            0x0F,
            0xDA,
            0xA2,
            0x21,
            0x68,
            0xC2,
            0x34,
            0xC4,
            0xC6,
            0x62,
            0x8B,
            0x80,
            0xDC,
            0x1C,
            0xD1,
            0x29,
            0x02,
            0x4E,
            0x08,
            0x8A,
            0x67,
            0xCC,
            0x74,
            0x02,
            0x0B,
            0xBE,
            0xA6,
            0x3B,
            0x13,
            0x9B,
            0x22,
            0x51,
            0x4A,
            0x08,
            0x79,
            0x8E,
            0x34,
            0x04,
            0xDD,
            0xEF,
            0x95,
            0x19,
            0xB3,
            0xCD,
            0x3A,
            0x43,
            0x1B,
            0x30,
            0x2B,
            0x0A,
            0x6D,
            0xF2,
            0x5F,
            0x14,
            0x37,
            0x4F,
            0xE1,
            0x35,
            0x6D,
            0x6D,
            0x51,
            0xC2,
            0x45,
            0xE4,
            0x85,
            0xB5,
            0x76,
            0x62,
            0x5E,
            0x7E,
            0xC6,
            0xF4,
            0x4C,
            0x42,
            0xE9,
            0xA6,
            0x3A,
            0x36,
            0x20,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
        ]
    )
    prime: int = int.from_bytes(prime_bytes, "big")
    private_key: int
    public_key: int

    def __init__(self):
        key_data = os.urandom(95)
        self.private_key = int.from_bytes(key_data, "big")
        self.public_key = pow(2, self.private_key, self.prime)

    def compute_shared_key(self, remote_key_bytes: bytes):
        remote_key = int.from_bytes(remote_key_bytes, "big")
        return pow(remote_key, self.private_key, self.prime)

    def private_key(self):
        return self.private_key

    def public_key(self):
        return self.public_key

    def public_key_array(self):
        return Utils.to_byte_array(self.public_key)
