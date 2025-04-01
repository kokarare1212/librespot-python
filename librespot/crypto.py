from __future__ import annotations
from Cryptodome import Random
from librespot import util
import io
import re
import struct
import typing

if typing.TYPE_CHECKING:
    from librespot.core import Session


class CipherPair:
    __receive_cipher: Shannon
    __receive_nonce = 0
    __send_cipher: Shannon
    __send_nonce = 0

    def __init__(self, send_key: bytes, receive_key: bytes):
        self.__send_cipher = Shannon()
        self.__send_cipher.key(send_key)
        self.__receive_cipher = Shannon()
        self.__receive_cipher.key(receive_key)

    def send_encoded(self, connection: Session.ConnectionHolder, cmd: bytes,
                     payload: bytes) -> None:
        """
        Send decrypted data to the socket
        :param connection:
        :param cmd:
        :param payload:
        :return:
        """
        self.__send_cipher.nonce(self.__send_nonce)
        self.__send_nonce += 1
        buffer = io.BytesIO()
        buffer.write(cmd)
        buffer.write(struct.pack(">H", len(payload)))
        buffer.write(payload)
        buffer.seek(0)
        contents = self.__send_cipher.encrypt(buffer.read())
        mac = self.__send_cipher.finish(4)
        connection.write(contents)
        connection.write(mac)
        connection.flush()

    def receive_encoded(self, connection: Session.ConnectionHolder) -> Packet:
        """
        Receive and parse decrypted data from the socket
        Args:
            connection: ConnectionHolder
        Return:
            The parsed packet will be returned
        """
        try:
            self.__receive_cipher.nonce(self.__receive_nonce)
            self.__receive_nonce += 1
            header_bytes = self.__receive_cipher.decrypt(connection.read(3))
            cmd = struct.pack(">s", bytes([header_bytes[0]]))
            payload_length = (header_bytes[1] << 8) | (header_bytes[2] & 0xff)
            payload_bytes = self.__receive_cipher.decrypt(
                connection.read(payload_length))
            mac = connection.read(4)
            expected_mac = self.__receive_cipher.finish(4)
            if mac != expected_mac:
                raise RuntimeError()
            return Packet(cmd, payload_bytes)
        except (IndexError, OSError):
            raise RuntimeError("Failed to receive packet")


class DiffieHellman:
    """
    DiffieHellman Keyexchange
    """
    __prime = int.from_bytes(
        b'\xff\xff\xff\xff\xff\xff\xff\xff\xc9\x0f'
        b'\xda\xa2!h\xc24\xc4\xc6b\x8b\x80\xdc\x1c'
        b'\xd1)\x02N\x08\x8ag\xcct\x02\x0b\xbe\xa6;'
        b'\x13\x9b"QJ\x08y\x8e4\x04\xdd\xef\x95\x19'
        b'\xb3\xcd:C\x1b0+\nm\xf2_\x147O\xe15mmQ\xc2'
        b'E\xe4\x85\xb5vb^~\xc6\xf4LB\xe9\xa6:6 \xff'
        b'\xff\xff\xff\xff\xff\xff\xff',
        byteorder="big")
    __private_key: int
    __public_key: int

    def __init__(self):
        key_data = Random.get_random_bytes(0x5f)
        self.__private_key = int.from_bytes(key_data, byteorder="big")
        self.__public_key = pow(2, self.__private_key, self.__prime)

    def compute_shared_key(self, remote_key_bytes: bytes):
        """
        Compute shared_key
        """
        remote_key = int.from_bytes(remote_key_bytes, "big")
        return pow(remote_key, self.__private_key, self.__prime)

    def private_key(self) -> int:
        """
        Return DiffieHellman's private key
        Returns:
            DiffieHellman's private key
        """
        return self.__private_key

    def public_key(self) -> int:
        """
        Return DiffieHellman's public key
        Returns:
            DiffieHellman's public key
        """
        return self.__public_key

    def public_key_bytes(self) -> bytes:
        """
        Return DiffieHellman's packed public key
        Returns:
            DiffieHellman's packed public key
        """
        return util.int_to_bytes(self.__public_key)


class Packet:
    cmd: bytes
    payload: bytes

    def __init__(self, cmd: bytes, payload: bytes):
        self.cmd = cmd
        self.payload = payload

    def is_cmd(self, cmd: bytes) -> bool:
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
        def parse(val: typing.Union[bytes, None]) -> typing.Union[bytes, None]:
            for cmd in [
                    Packet.Type.__dict__[attr] for attr in Packet.Type.__dict__
                    if re.search("__.+?__", attr) is None
                    and type(Packet.Type.__dict__[attr]) is bytes
            ]:
                if cmd == val:
                    return cmd
            return None

        @staticmethod
        def for_method(method: str) -> bytes:
            if method == "SUB":
                return Packet.Type.mercury_sub
            if method == "UNSUB":
                return Packet.Type.mercury_unsub
            return Packet.Type.mercury_req


class Shannon:
    n = 16
    fold = n
    initkonst = 0x6996c53a
    keyp = 13
    r: list
    crc: list
    init_r: list
    konst: int
    sbuf: int
    mbuf: int
    nbuf: int

    def __init__(self):
        self.r = [0 for _ in range(self.n)]
        self.crc = [0 for _ in range(self.n)]
        self.init_r = [0 for _ in range(self.n)]

    def rotl(self, i: int, distance: int) -> int:
        return ((i << distance) | (i >> (32 - distance))) & 0xffffffff

    def sbox(self, i: int) -> int:
        i ^= self.rotl(i, 5) | self.rotl(i, 7)
        i ^= self.rotl(i, 19) | self.rotl(i, 22)
        return i

    def sbox2(self, i: int) -> int:
        i ^= self.rotl(i, 7) | self.rotl(i, 22)
        i ^= self.rotl(i, 5) | self.rotl(i, 19)
        return i

    def cycle(self) -> None:
        t: int
        t = self.r[12] ^ self.r[13] ^ self.konst
        t = self.sbox(t) ^ self.rotl(self.r[0], 1)
        for i in range(1, self.n):
            self.r[i - 1] = self.r[i]
        self.r[self.n - 1] = t
        t = self.sbox2(self.r[2] ^ self.r[15])
        self.r[0] ^= t
        self.sbuf = t ^ self.r[8] ^ self.r[12]

    def crc_func(self, i: int) -> None:
        t: int
        t = self.crc[0] ^ self.crc[2] ^ self.crc[15] ^ i
        for j in range(1, self.n):
            self.crc[j - 1] = self.crc[j]
        self.crc[self.n - 1] = t

    def mac_func(self, i: int) -> None:
        self.crc_func(i)
        self.r[self.keyp] ^= i

    def init_state(self) -> None:
        self.r[0] = 1
        self.r[1] = 1
        for i in range(2, self.n):
            self.r[i] = self.r[i - 1] + self.r[i - 2]
        self.konst = self.initkonst

    def save_state(self) -> None:
        for i in range(self.n):
            self.init_r[i] = self.r[i]

    def reload_state(self) -> None:
        for i in range(self.n):
            self.r[i] = self.init_r[i]

    def gen_konst(self) -> None:
        self.konst = self.r[0]

    def add_key(self, k: int) -> None:
        self.r[self.keyp] ^= k

    def diffuse(self) -> None:
        for _ in range(self.fold):
            self.cycle()

    def load_key(self, key: bytes) -> None:
        i: int
        j: int
        t: int
        padding_size = int((len(key) + 3) / 4) * 4 - len(key)
        key = key + (b"\x00" * padding_size) + struct.pack("<I", len(key))
        for i in range(0, len(key), 4):
            self.r[self.keyp] = \
                self.r[self.keyp] ^ \
                struct.unpack("<I", key[i: i + 4])[0]
            self.cycle()
        for i in range(self.n):
            self.crc[i] = self.r[i]
        self.diffuse()
        for i in range(self.n):
            self.r[i] ^= self.crc[i]

    def key(self, key: bytes) -> None:
        self.init_state()
        self.load_key(key)
        self.gen_konst()
        self.save_state()
        self.nbuf = 0

    def nonce(self, nonce: typing.Union[bytes, int]) -> None:
        if type(nonce) is int:
            nonce = bytes(struct.pack(">I", nonce))
        self.reload_state()
        self.konst = self.initkonst
        self.load_key(nonce)
        self.gen_konst()
        self.nbuf = 0

    def encrypt(self, buffer: bytes, n: int = None) -> bytes:
        if n is None:
            return self.encrypt(buffer, len(buffer))
        buffer = bytearray(buffer)
        i = 0
        j: int
        t: int
        if self.nbuf != 0:
            while self.nbuf != 0 and n != 0:
                self.mbuf ^= (buffer[i] & 0xff) << (32 - self.nbuf)
                buffer[i] ^= (self.sbuf >> (32 - self.nbuf)) & 0xff
                i += 1
                self.nbuf -= 8
                n -= 1
            if self.nbuf != 0:
                return b""
            self.mac_func(self.mbuf)
        j = n & ~0x03
        while i < j:
            self.cycle()
            t = ((buffer[i + 3] & 0xFF) << 24) | \
                ((buffer[i + 2] & 0xFF) << 16) | \
                ((buffer[i + 1] & 0xFF) << 8) | \
                (buffer[i] & 0xFF)
            self.mac_func(t)
            t ^= self.sbuf
            buffer[i + 3] = (t >> 24) & 0xFF
            buffer[i + 2] = (t >> 16) & 0xFF
            buffer[i + 1] = (t >> 8) & 0xFF
            buffer[i] = t & 0xFF
            i += 4
        n &= 0x03
        if n != 0:
            self.cycle()
            self.mbuf = 0
            self.nbuf = 32
            while self.nbuf != 0 and n != 0:
                self.mbuf ^= (buffer[i] & 0xff) << (32 - self.nbuf)
                buffer[i] ^= (self.sbuf >> (32 - self.nbuf)) & 0xff
                i += 1
                self.nbuf -= 8
                n -= 1
        return bytes(buffer)

    def decrypt(self, buffer: bytes, n: int = None) -> bytes:
        if n is None:
            return self.decrypt(buffer, len(buffer))
        buffer = bytearray(buffer)
        i = 0
        j: int
        t: int
        if self.nbuf != 0:
            while self.nbuf != 0 and n != 0:
                buffer[i] ^= (self.sbuf >> (32 - self.nbuf)) & 0xff
                self.mbuf ^= (buffer[i] & 0xff) << (32 - self.nbuf)
                i += 1
                self.nbuf -= 8
                n -= 1
            if self.nbuf != 0:
                return b""
            self.mac_func(self.mbuf)
        j = n & ~0x03
        while i < j:
            self.cycle()
            t = ((buffer[i + 3] & 0xFF) << 24) | \
                ((buffer[i + 2] & 0xFF) << 16) | \
                ((buffer[i + 1] & 0xFF) << 8) | \
                (buffer[i] & 0xFF)
            t ^= self.sbuf
            self.mac_func(t)
            buffer[i + 3] = (t >> 24) & 0xFF
            buffer[i + 2] = (t >> 16) & 0xFF
            buffer[i + 1] = (t >> 8) & 0xFF
            buffer[i] = t & 0xFF
            i += 4
        n &= 0x03
        if n != 0:
            self.cycle()
            self.mbuf = 0
            self.nbuf = 32
            while self.nbuf != 0 and n != 0:
                buffer[i] ^= (self.sbuf >> (32 - self.nbuf)) & 0xff
                self.mbuf ^= (buffer[i] & 0xff) << (32 - self.nbuf)
                i += 1
                self.nbuf -= 8
                n -= 1
        return bytes(buffer)

    def finish(self, n: int) -> bytes:
        buffer = bytearray(4)
        i = 0
        j: int
        if self.nbuf != 0:
            self.mac_func(self.mbuf)
        self.cycle()
        self.add_key(self.initkonst ^ (self.nbuf << 3))
        self.nbuf = 0
        for j in range(self.n):
            self.r[j] ^= self.crc[j]
        self.diffuse()
        while n > 0:
            self.cycle()
            if n >= 4:
                buffer[i + 3] = (self.sbuf >> 24) & 0xff
                buffer[i + 2] = (self.sbuf >> 16) & 0xff
                buffer[i + 1] = (self.sbuf >> 8) & 0xff
                buffer[i] = self.sbuf & 0xff
                n -= 4
                i += 4
            else:
                for j in range(n):
                    buffer[i + j] = (self.sbuf >> (i * 8)) & 0xff
                break
        return bytes(buffer)
