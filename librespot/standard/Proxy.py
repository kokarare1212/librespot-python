from __future__ import annotations
import enum


class Proxy:
    class Type(enum.Enum):
        DIRECT = enum.auto()
        HTTP = enum.auto()
        SOCKS = enum.auto()
