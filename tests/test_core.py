import unittest

from tftp_packet_codec import (
    Opcode,
    ErrorCode,
    ReadRequest,
    WriteRequest,
    DataPacket,
    AckPacket,
    ErrorPacket,
    encode,
    decode,
)


class TestRoundTrip(unittest.TestCase):
    def test_rrq(self):
        wire = encode(ReadRequest(filename="file.txt", mode="octet"))
        self.assertEqual(
            wire,
            b"\x00\x01file.txt\x00octet\x00",
        )
        pkt = decode(wire)
        self.assertIsInstance(pkt, ReadRequest)
        self.assertEqual(pkt.filename, "file.txt")
        self.assertEqual(pkt.mode, "octet")

    def test_wrq(self):
        wire = encode(WriteRequest(filename="out.bin", mode="netascii"))
        self.assertEqual(wire, b"\x00\x02out.bin\x00netascii\x00")
        pkt = decode(wire)
        self.assertIsInstance(pkt, WriteRequest)
        self.assertEqual(pkt.filename, "out.bin")
        self.assertEqual(pkt.mode, "netascii")

    def test_data(self):
        payload = b"\x01\x02\x03"
        wire = encode(DataPacket(block=1, data=payload))
        self.assertEqual(wire, b"\x00\x03\x00\x01" + payload)
        pkt = decode(wire)
        self.assertIsInstance(pkt, DataPacket)
        self.assertEqual(pkt.block, 1)
        self.assertEqual(pkt.data, payload)

    def test_data_max_block(self):
        wire = encode(DataPacket(block=0xFFFF, data=b""))
        self.assertEqual(wire, b"\x00\x03\xff\xff")
        pkt = decode(wire)
        self.assertEqual(pkt.block, 0xFFFF)
        self.assertEqual(pkt.data, b"")

    def test_data_block_overflow(self):
        with self.assertRaises(ValueError):
            encode(DataPacket(block=0x10000, data=b""))

    def test_ack(self):
        wire = encode(AckPacket(block=42))
        self.assertEqual(wire, b"\x00\x04\x00\x2a")
        pkt = decode(wire)
        self.assertIsInstance(pkt, AckPacket)
        self.assertEqual(pkt.block, 42)

    def test_error(self):
        wire = encode(ErrorPacket(code=ErrorCode.FILE_NOT_FOUND, message="not here"))
        self.assertEqual(wire, b"\x00\x05\x00\x01not here\x00")
        pkt = decode(wire)
        self.assertIsInstance(pkt, ErrorPacket)
        self.assertEqual(pkt.code, ErrorCode.FILE_NOT_FOUND)
        self.assertEqual(pkt.message, "not here")

    def test_error_empty_message(self):
        wire = encode(ErrorPacket(code=ErrorCode.NOT_DEFINED, message=""))
        self.assertEqual(wire, b"\x00\x05\x00\x00\x00")
        pkt = decode(wire)
        self.assertEqual(pkt.message, "")


class TestDecodeErrors(unittest.TestCase):
    def test_short_opcode(self):
        with self.assertRaises(ValueError):
            decode(b"\x00")

    def test_empty(self):
        with self.assertRaises(ValueError):
            decode(b"")

    def test_unknown_opcode(self):
        with self.assertRaises(ValueError):
            decode(b"\x00\x09\x00")

    def test_rrq_missing_mode(self):
        with self.assertRaises(ValueError):
            decode(b"\x00\x01file.txt\x00")

    def test_rrq_trailing_bytes(self):
        with self.assertRaises(ValueError):
            decode(b"\x00\x01f\x00octet\x00extra")

    def test_ack_wrong_length(self):
        with self.assertRaises(ValueError):
            decode(b"\x00\x04\x00\x01\x00")

    def test_error_too_short(self):
        with self.assertRaises(ValueError):
            decode(b"\x00\x05\x00\x01")

    def test_error_trailing_bytes(self):
        with self.assertRaises(ValueError):
            decode(b"\x00\x05\x00\x01msg\x00extra")

    def test_data_missing_block(self):
        with self.assertRaises(ValueError):
            decode(b"\x00\x03")

    def test_error_unknown_code_falls_back(self):
        pkt = decode(b"\x00\x05\x00\xffmsg\x00")
        self.assertIsInstance(pkt, ErrorPacket)
        self.assertEqual(pkt.code, ErrorCode.NOT_DEFINED)


class TestEncodeErrors(unittest.TestCase):
    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            encode("not a packet")

    def test_negative_block(self):
        with self.assertRaises(ValueError):
            encode(DataPacket(block=-1, data=b""))


if __name__ == "__main__":
    unittest.main()
