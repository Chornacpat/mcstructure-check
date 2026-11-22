"""A bounded reader for raw, little-endian Bedrock Named Binary Tag data.

Numeric tag identity is preserved for the four integer scalar types. TAG_List
becomes a Python list, TAG_Byte_Array becomes bytes, and TAG_Int_Array and
TAG_Long_Array become packed signed arrays ('i' and 'q'). The zlib helper
decodes one bounded stream containing a serialized NBT compound. There is no
filesystem access or command evaluation.
"""

from array import array
import struct
import sys
import zlib


class NBTError(ValueError):
    """Input could not be decoded as one supported NBT document."""


class Byte(int):
    """Signed TAG_Byte."""


class Short(int):
    """Signed TAG_Short."""


class Int(int):
    """Signed TAG_Int."""


class Long(int):
    """Signed TAG_Long."""


MAX_BYTES = 64 * 1024 * 1024
MAX_ZLIB_OUTPUT = MAX_BYTES
MAX_DEPTH = 64
MAX_COLLECTION = 8 * 1024 * 1024
MAX_NODES = 1_000_000
_NUMBERS = {
    1: (struct.Struct("<b"), Byte),
    2: (struct.Struct("<h"), Short),
    3: (struct.Struct("<i"), Int),
    4: (struct.Struct("<q"), Long),
    5: (struct.Struct("<f"), float),
    6: (struct.Struct("<d"), float),
}
_U16 = struct.Struct("<H")
_I32 = struct.Struct("<i")
_MIN_TAG_BYTES = {1: 1, 2: 2, 3: 4, 4: 8, 5: 4, 6: 8, 7: 4,
                  8: 2, 9: 5, 10: 1, 11: 4, 12: 4}


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.remaining_nodes = MAX_NODES

    def _advance(self, size: int) -> int:
        start = self.pos
        if size > len(self.data) - start:
            raise NBTError("truncated NBT")
        self.pos += size
        return start

    def _number(self, decoder: struct.Struct):
        return decoder.unpack_from(self.data, self._advance(decoder.size))[0]

    def _u8(self) -> int:
        return self.data[self._advance(1)]

    def _string(self) -> str:
        size = self._number(_U16)
        start = self._advance(size)
        raw = self.data[start:self.pos]
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            # Some writers use Java-style modified UTF-8, which encodes NUL
            # as C0 80 and non-BMP characters as two UTF-8 surrogate code units.
            # Reject invalid/unpaired data rather than replacing bytes silently.
            try:
                value = raw.replace(b"\xc0\x80", b"\x00").decode(
                    "utf-8", errors="surrogatepass"
                )
                return value.encode("utf-16-le", errors="surrogatepass").decode(
                    "utf-16-le"
                )
            except UnicodeError:
                raise NBTError("invalid NBT string encoding") from None

    def _count(self) -> int:
        count = self._number(_I32)
        if count < 0:
            raise NBTError("negative NBT collection length")
        if count > MAX_COLLECTION:
            raise NBTError("NBT collection length exceeds limit")
        return count

    def _array(self, kind: int):
        count = self._count()
        if kind == 7:
            start = self._advance(count)
            return self.data[start:self.pos]
        fmt, width = ("i", 4) if kind == 11 else ("q", 8)
        size = count * width
        start = self._advance(size)
        values = array(fmt)
        if values.itemsize != width:
            raise NBTError("unsupported native array width")
        values.frombytes(memoryview(self.data)[start:self.pos])
        if sys.byteorder != "little":
            values.byteswap()
        return values

    def _value(self, kind: int, depth: int):
        if depth > MAX_DEPTH:
            raise NBTError("NBT nesting exceeds limit")
        self.remaining_nodes -= 1
        if self.remaining_nodes < 0:
            raise NBTError("NBT decoded node count exceeds limit")

        if kind in _NUMBERS:
            decoder, scalar = _NUMBERS[kind]
            return scalar(self._number(decoder))
        if kind == 8:
            return self._string()
        if kind in (7, 11, 12):
            return self._array(kind)
        if kind == 9:
            element = self._u8()
            count = self._count()
            if element not in _MIN_TAG_BYTES and not (element == 0 and count == 0):
                raise NBTError("invalid NBT list element tag")
            if count > self.remaining_nodes:
                raise NBTError("NBT decoded node count exceeds limit")
            if count and count * _MIN_TAG_BYTES[element] > len(self.data) - self.pos:
                raise NBTError("truncated NBT")
            return [self._value(element, depth + 1) for _ in range(count)]
        if kind == 10:
            value: dict = {}
            while True:
                child = self._u8()
                if child == 0:
                    return value
                if child not in _MIN_TAG_BYTES:
                    raise NBTError("invalid NBT tag")
                key = self._string()
                if key in value:
                    raise NBTError("duplicate NBT compound key")
                value[key] = self._value(child, depth + 1)
        raise NBTError("invalid NBT tag")


def loads(data: bytes) -> dict:
    """Decode a single named root compound from an uncompressed Bedrock file."""
    if len(data) > MAX_BYTES:
        raise NBTError("NBT input exceeds 64 MiB limit")
    reader = _Reader(data)
    if reader._u8() != 10:
        raise NBTError("NBT root is not a compound")
    reader._string()
    root = reader._value(10, 0)
    if reader.pos != len(data):
        raise NBTError("trailing bytes after NBT root")
    return root


def loads_zlib_compound(payload: bytes) -> dict:
    """Inflate one zlib-wrapped little-endian NBT compound within fixed limits."""
    decoder = zlib.decompressobj(wbits=zlib.MAX_WBITS)
    try:
        data = decoder.decompress(payload, MAX_ZLIB_OUTPUT + 1)
    except zlib.error:
        raise NBTError("invalid structure zlib stream") from None
    if len(data) > MAX_ZLIB_OUTPUT or decoder.unconsumed_tail:
        raise NBTError("decompressed structure exceeds size limit")
    if not decoder.eof:
        raise NBTError("truncated structure zlib stream")
    if decoder.unused_data:
        raise NBTError("trailing bytes after structure zlib stream")
    return loads(data)
