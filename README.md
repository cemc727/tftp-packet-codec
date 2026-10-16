# tftp-packet-codec

Encodes and decodes TFTP read request, write request, data, acknowledgement, and error packets per RFC 1350.

```python
from tftp_packet_codec import ReadRequest, encode, decode

wire = encode(ReadRequest(filename="boot.img", mode="octet"))
# b'\x00\x01boot.img\x00octet\x00'

pkt = decode(wire)
# ReadRequest(filename='boot.img', mode='octet')
```

Exports: `Opcode`, `ErrorCode`, `ReadRequest`, `WriteRequest`, `DataPacket`, `AckPacket`, `ErrorPacket`, `encode`, `decode`.

## Why

This library exists to handle the wire-format details of TFTP so a server or client implementation can focus on the transfer state machine. The trade-off is that this library is deliberately thin: it does not implement transfer logic, block sequencing, timeouts, or the final-block detection rule (a DATA payload shorter than 512 bytes). Callers get the raw bytes and check that themselves.

## Edge cases

- Strings are NUL-terminated ASCII. Passing non-ASCII in a filename or mode will raise `UnicodeEncodeError` at encode time.
- DATA block numbers are 16-bit unsigned (0–65535). Anything outside that range raises `ValueError`.
- Unknown error codes on decode fall back to `ErrorCode.NOT_DEFINED` rather than raising, so a client can still read the error message text from an interop partner that uses a non-standard code.
- Malformed input (truncated, trailing bytes, missing fields) raises `ValueError` on decode.
