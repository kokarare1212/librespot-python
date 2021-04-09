import math


class Base62:
    standard_base = 256
    target_base = 62
    alphabet: bytes
    lookup: bytearray

    def __init__(self, alphabet: bytes):
        self.alphabet = alphabet
        self.create_lookup_table()

    @staticmethod
    def create_instance_with_inverted_character_set():
        return Base62(Base62.CharacterSets.inverted)

    def encode(self, message: bytes, length: int = -1):
        indices = self.convert(message, self.standard_base, self.target_base,
                               length)
        return self.translate(indices, self.alphabet)

    def decode(self, encoded: bytes, length: int = -1):
        prepared = self.translate(encoded, self.lookup)
        return self.convert(prepared, self.target_base, self.standard_base,
                            length)

    def translate(self, indices: bytes, dictionary: bytes):
        translation = bytearray(len(indices))
        for i in range(len(indices)):
            translation[i] = dictionary[int.from_bytes(indices[i].encode(),
                                                       "big")]

        return translation

    def convert(self, message: bytes, source_base: int, target_base: int,
                length: int):
        estimated_length = self.estimate_output_length(
            len(message), source_base, target_base) if length == -1 else length
        out = b""
        source = message
        while len(source) > 0:
            quotient = b""
            remainder = 0
            for b in source:
                accumulator = int(b & 0xff) + remainder * source_base
                digit = int(
                    (accumulator - (accumulator % target_base)) / target_base)
                remainder = int(accumulator % target_base)
                if len(quotient) > 0 or digit > 0:
                    quotient += bytes([digit])

            out += bytes([remainder])
            source = quotient

        if len(out) < estimated_length:
            size = len(out)
            for i in range(estimated_length - size):
                out += bytes([0])

            return self.reverse(out)
        if len(out) > estimated_length:
            return self.reverse(out[:estimated_length])
        return self.reverse(out)

    def estimate_output_length(self, input_length: int, source_base: int,
                               target_base: int):
        return int(
            math.ceil((math.log(source_base) / math.log(target_base)) *
                      input_length))

    def reverse(self, arr: bytes):
        length = len(arr)
        reversed_arr = bytearray(length)
        for i in range(length):
            reversed_arr[length - i - 1] = arr[i]

        return bytes(reversed_arr)

    def create_lookup_table(self):
        self.lookup = bytearray(256)
        for i in range(len(self.alphabet)):
            self.lookup[self.alphabet[i]] = i & 0xff

    class CharacterSets:
        gmp = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        inverted = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
