"""Reader conformance checks with tiny synthetic files."""

import struct
import unittest

from mcstructure_check.nbt import Byte, Int, NBTError, loads
from tests.make_fixtures import byte, compound, integer, string, string_bytes


class NBTTests(unittest.TestCase):
    def test_numeric_tag_types_and_unicode_round_trip(self):
        kind, payload = compound({
            "byte": byte(-7), "int": integer(-999), "名称": string("样例 🧱"),
        })
        tree = loads(bytes([kind]) + string_bytes("") + payload)
        self.assertIs(type(tree["byte"]), Byte)
        self.assertEqual(tree["byte"], -7)
        self.assertIs(type(tree["int"]), Int)
        self.assertEqual(tree["int"], -999)
        self.assertEqual(tree["名称"], "样例 🧱")

    def test_parse_root_and_reject_duplicate_keys(self):
        prefix = b"\x0a\x00\x00"
        item = b"\x03" + string_bytes("duplicate") + struct.pack("<i", 1)
        self.assertEqual(loads(prefix + b"\x00"), {})
        with self.assertRaises(NBTError):
            loads(prefix + item + item + b"\x00")

    def test_modified_utf8_supplementary_character(self):
        # U+1F9F1 encoded as two UTF-16 surrogate code units.
        raw = b"\xed\xa0\xbe\xed\xb7\xb1"
        payload = b"\x0a\x00\x00\x08" + string_bytes("s") + struct.pack("<H", len(raw))
        self.assertEqual(loads(payload + raw + b"\x00")["s"], "🧱")

    def test_end_tag_cannot_be_a_nonempty_list_element(self):
        payload = b"\x0a\x00\x00\x09" + string_bytes("list") + b"\x00\x01\x00\x00\x00\x00"
        with self.assertRaises(NBTError):
            loads(payload)


if __name__ == "__main__":
    unittest.main()
