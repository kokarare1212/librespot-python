import struct
import typing


class Shannon:
    N = 16
    FOLD = N
    INITKONST = 0x6996c53a
    KEYP = 13

    R: list
    CRC: list
    initR: list
    konst: int
    sbuf: int
    mbuf: int
    nbuf: int

    def __init__(self):
        self.R = [0 for _ in range(self.N)]
        self.CRC = [0 for _ in range(self.N)]
        self.initR = [0 for _ in range(self.N)]

    def rotl(self, i: int, distance: int):
        return ((i << distance) | (i >> (32 - distance))) & 0xffffffff

    def sbox(self, i: int):
        i ^= self.rotl(i, 5) | self.rotl(i, 7)
        i ^= self.rotl(i, 19) | self.rotl(i, 22)

        return i

    def sbox2(self, i: int):
        i ^= self.rotl(i, 7) | self.rotl(i, 22)
        i ^= self.rotl(i, 5) | self.rotl(i, 19)

        return i

    def cycle(self):
        t: int

        t = self.R[12] ^ self.R[13] ^ self.konst
        t = self.sbox(t) ^ self.rotl(self.R[0], 1)

        for i in range(1, self.N):
            self.R[i - 1] = self.R[i]

        self.R[self.N - 1] = t

        t = self.sbox2(self.R[2] ^ self.R[15])
        self.R[0] ^= t
        self.sbuf = t ^ self.R[8] ^ self.R[12]

    def crc_func(self, i: int):
        t: int

        t = self.CRC[0] ^ self.CRC[2] ^ self.CRC[15] ^ i

        for j in range(1, self.N):
            self.CRC[j - 1] = self.CRC[j]

        self.CRC[self.N - 1] = t

    def mac_func(self, i: int):
        self.crc_func(i)

        self.R[self.KEYP] ^= i

    def init_state(self):
        self.R[0] = 1
        self.R[1] = 1

        for i in range(2, self.N):
            self.R[i] = self.R[i - 1] + self.R[i - 2]

        self.konst = self.INITKONST

    def save_state(self):
        for i in range(self.N):
            self.initR[i] = self.R[i]

    def reload_state(self):
        for i in range(self.N):
            self.R[i] = self.initR[i]

    def gen_konst(self):
        self.konst = self.R[0]

    def add_key(self, k: int):
        self.R[self.KEYP] ^= k

    def diffuse(self):
        for i in range(self.FOLD):
            self.cycle()

    def load_key(self, key: bytes):
        extra = bytearray(4)
        i: int
        j: int
        t: int

        padding_size = int((len(key) + 3) / 4) * 4 - len(key)
        key = key + (b"\x00" * padding_size) + struct.pack("<I", len(key))

        for i in range(0, len(key), 4):
            self.R[self.KEYP] = \
                self.R[self.KEYP] ^ \
                struct.unpack("<I", key[i: i + 4])[0]

            self.cycle()

        for i in range(self.N):
            self.CRC[i] = self.R[i]

        self.diffuse()

        for i in range(self.N):
            self.R[i] ^= self.CRC[i]

    def key(self, key: bytes):
        self.init_state()

        self.load_key(key)

        self.gen_konst()

        self.save_state()

        self.nbuf = 0

    def nonce(self, nonce: typing.Union[bytes, int]):
        if type(nonce) is int:
            nonce = bytes(struct.pack(">I", nonce))

        self.reload_state()

        self.konst = self.INITKONST

        self.load_key(nonce)

        self.gen_konst()

        self.nbuf = 0

    def encrypt(self, buffer: bytes, n: int = None):
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
                return

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

    def decrypt(self, buffer: bytes, n: int = None):
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
                return

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

    def finish(self, n: int):
        buffer = bytearray(4)

        i = 0
        j: int

        if self.nbuf != 0:
            self.mac_func(self.mbuf)

        self.cycle()
        self.add_key(self.INITKONST ^ (self.nbuf << 3))

        self.nbuf = 0

        for j in range(self.N):
            self.R[j] ^= self.CRC[j]

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


if __name__ == "__main__":
    TEST_KEY = b"test key 128bits"
    TEST_PHRASE = b'\x00' * 20
    sh = Shannon()
    sh.key(TEST_KEY)
    sh.nonce(0)
    encr = sh.encrypt(TEST_PHRASE)
    print(encr)
