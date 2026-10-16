from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union


class Opcode(IntEnum):
    """TFTP packet opcodes per RFC 1350."""

    RRQ = 1
    WRQ = 2
    DATA = 3
    ACK = 4
    ERROR = 5


class ErrorCode(IntEnum):
    """TFTP error codes per RFC 1350."""

    NOT_DEFINED = 0
    FILE_NOT_FOUND = 1
    ACCESS_VIOLATION = 2
    DISK_FULL = 3
    ILLEGAL_OPERATION = 4
    UNKNOWN_TID = 5
    FILE_ALREADY_EXISTS = 6
    NO_SUCH_USER = 7


@dataclass(frozen=True)
class ReadRequest:
    filename: str
    mode: str = "octet"


@dataclass(frozen=True)
class WriteRequest:
    filename: str
    mode: str = "octet"


@dataclass(frozen=True)
class DataPacket:
    block: int
    data: bytes


@dataclass(frozen=True)
class AckPacket:
    block: int


@dataclass(frozen=True)
class ErrorPacket:
    code: ErrorCode
    message: str


Packet = Union[ReadRequest, WriteRequest, DataPacket, AckPacket, ErrorPacket]


_MAX_BLOCK = 0xFFFF


def _split_cstring(buf: bytes, start: int) -> tuple[str, int]:
    end = buf.index(b"\x00", start)
    return buf[start:end].decode("ascii"), end + 1


def _join_cstrings(*parts: str) -> bytes:
    return b"".join(p.encode("ascii") + b"\x00" for p in parts)


def encode(packet: Packet) -> bytes:
    """Serialize a TFTP packet to its RFC 1350 wire format.

    RFC 1350 uses network byte order (big-endian) for numeric fields and
    NUL-terminated ASCII strings. String fields carry filenames and transfer
    modes; per the RFC the mode is case-insensitive, but we send exactly what
    the caller provided rather than normalizing, so the caller controls the
    exact bytes on the wire.

    Raises:
        ValueError: if the packet type is unknown or a field is out of range.
    """
    if isinstance(packet, ReadRequest):
        return b"\x00\x01" + _join_cstrings(packet.filename, packet.mode)
    if isinstance(packet, WriteRequest):
        return b"\x00\x02" + _join_cstrings(packet.filename, packet.mode)
    if isinstance(packet, DataPacket):
        if not (0 <= packet.block <= _MAX_BLOCK):
            raise ValueError(f"block number out of range: {packet.block}")
        return b"\x00\x03" + packet.block.to_bytes(2, "big") + packet.data
    if isinstance(packet, AckPacket):
        if not (0 <= packet.block <= _MAX_BLOCK):
            raise ValueError(f"block number out of range: {packet.block}")
        return b"\x00\x04" + packet.block.to_bytes(2, "big")
    if isinstance(packet, ErrorPacket):
        return (
            b"\x00\x05"
            + int(packet.code).to_bytes(2, "big")
            + _join_cstrings(packet.message)
        )
    raise ValueError(f"unknown packet type: {type(packet).__name__}")


def decode(data: bytes) -> Packet:
    """Parse a TFTP packet from RFC 1350 wire format.

    Returns one of the five packet dataclasses. Block numbers are returned as
    plain ints. For DATA packets we include the raw payload bytes with no
    length check, because RFC 1350 does not mandate a fixed data length — the
    only rule of interest is that a payload shorter than 512 bytes signals the
    final block, which callers can check themselves.

    Raises:
        ValueError: on truncated input, bad opcode, or malformed structure.
    """
    if len(data) < 2:
        raise ValueError("packet too short for opcode")
    opcode = int.from_bytes(data[:2], "big")
    rest = data[2:]

    if opcode == Opcode.RRQ:
        filename, pos = _split_cstring(rest, 0)
        mode, pos = _split_cstring(rest, pos)
        if pos != len(rest):
            raise ValueError("trailing bytes after mode field")
        return ReadRequest(filename=filename, mode=mode)

    if opcode == Opcode.WRQ:
        filename, pos = _split_cstring(rest, 0)
        mode, pos = _split_cstring(rest, pos)
        if pos != len(rest):
            raise ValueError("trailing bytes after mode field")
        return WriteRequest(filename=filename, mode=mode)

    if opcode == Opcode.DATA:
        if len(rest) < 2:
            raise ValueError("DATA packet missing block number")
        block = int.from_bytes(rest[:2], "big")
        return DataPacket(block=block, data=rest[2:])

    if opcode == Opcode.ACK:
        if len(rest) != 2:
            raise ValueError("ACK packet must be exactly 4 bytes")
        block = int.from_bytes(rest, "big")
        return AckPacket(block=block)

    if opcode == Opcode.ERROR:
        if len(rest) < 3:
            raise ValueError("ERROR packet too short")
        code = int.from_bytes(rest[:2], "big")
        message, pos = _split_cstring(rest, 2)
        if pos != len(rest):
            raise ValueError("trailing bytes after error message")
        try:
            ec = ErrorCode(code)
        except ValueError:
            ec = ErrorCode.NOT_DEFINED
        return ErrorPacket(code=ec, message=message)

    raise ValueError(f"unknown opcode: {opcode}")
