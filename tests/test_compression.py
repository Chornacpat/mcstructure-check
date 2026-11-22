"""Synthetic conformance checks for 26.60 version 2 zlib structures.

Format reference: Mojang Minecraft Bedrock Edition 26.60 changelog,
'.mcstructure Files' section.
"""

import json
import unittest
from unittest.mock import patch
import zlib

from mcstructure_check.inspect import inspect_bytes
from tests.make_fixtures import (
    CLEAN, FINDINGS, SAMPLE_COMMAND, byte, byte_array, integer, make_structure,
    make_compressed, string_bytes,
)


class CompressionTests(unittest.TestCase):
    def test_compressed_matches_uncompressed_v2(self):
        for blocks in (CLEAN, FINDINGS):
            with self.subTest(command_count=len(blocks)):
                plain = inspect_bytes(make_structure(blocks, version=2))
                compressed = inspect_bytes(make_compressed(blocks))
                # The transport format flag is permitted to differ.
                plain.pop("compression", None)
                compressed.pop("compression", None)
                self.assertEqual(plain, compressed)
                self.assertNotIn(SAMPLE_COMMAND, json.dumps(compressed))

    def test_explicit_uncompressed_flag(self):
        plain = inspect_bytes(make_structure(CLEAN, version=2, compression_tag=integer(0)))
        self.assertEqual(plain["command_block_count"], 1)
        self.assertFalse(plain["issues"])

    def test_truncated_zlib_stream(self):
        with self.assertRaises(ValueError):
            inspect_bytes(make_compressed(CLEAN, stream_transform=lambda stream: stream[:-1]))

    def test_zlib_stream_rejects_appended_data_and_members(self):
        with self.assertRaises(ValueError):
            inspect_bytes(make_compressed(CLEAN, stream_transform=lambda stream: stream + b"x"))
        with self.assertRaises(ValueError):
            inspect_bytes(make_compressed(
                CLEAN, stream_transform=lambda stream: stream + zlib.compress(b"extra")
            ))

    def test_inner_nbt_is_validated_separately(self):
        with self.assertRaises(ValueError):
            inspect_bytes(make_compressed(CLEAN, inner_transform=lambda nbt: nbt[:-1]))
        with self.assertRaises(ValueError):
            inspect_bytes(make_compressed(CLEAN, inner_transform=lambda nbt: nbt + b"x"))

    def test_compression_flag_and_payload_type_must_agree(self):
        for flag, writer in (
                (integer(1), None),
                (integer(0), lambda compound: byte_array(b"placeholder")),
                (integer(2), None),
                (byte(0), None)):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                inspect_bytes(make_structure(CLEAN, version=2, compression_tag=flag,
                                             encode_structure=writer))

    def test_inflated_nbt_respects_limit(self):
        lengths = []

        def record(nbt):
            lengths.append(len(nbt))
            return nbt

        file = make_compressed(CLEAN, inner_transform=record)
        self.assertGreater(lengths[0], 64)
        with patch("mcstructure_check.nbt.MAX_ZLIB_OUTPUT", lengths[0]):
            self.assertEqual(inspect_bytes(file)["command_block_count"], 1)
        with patch("mcstructure_check.nbt.MAX_ZLIB_OUTPUT", lengths[0] - 1):
            with self.assertRaises(ValueError):
                inspect_bytes(file)

    def test_compression_not_allowed_on_version_one(self):
        with self.assertRaises(ValueError):
            inspect_bytes(make_structure(
                CLEAN, version=1, compression_tag=integer(1),
                encode_structure=lambda compound: byte_array(zlib.compress(
                    bytes([compound[0]]) + string_bytes("") + compound[1]
                )),
            ))


if __name__ == "__main__":
    unittest.main()
