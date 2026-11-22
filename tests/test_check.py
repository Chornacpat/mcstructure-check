"""Synthetic, offline checker and CLI acceptance tests."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mcstructure_check.inspect import inspect_bytes
from tests.make_fixtures import CLEAN, FINDINGS, SAMPLE_COMMAND, make_structure


class CheckerTests(unittest.TestCase):
    def test_clean_structure(self):
        result = inspect_bytes(make_structure(CLEAN))
        self.assertEqual(result["command_block_count"], 1)
        self.assertEqual(result["issues"], [])

    def test_issues_locate_both_conflict_directions(self):
        result = inspect_bytes(make_structure(FINDINGS))
        self.assertEqual(result["command_block_count"], len(FINDINGS))
        findings = {(issue["code"], tuple(issue.get("position", [])))
                    for issue in result["issues"]}
        required = {
            ("CONDITION_MISMATCH", (2, 0, 1)),
            ("CONDITION_MISMATCH", (1, 1, 0)),
            ("MISSING_COMMAND", (0, 0, 1)),
            ("INVALID_FACING", (0, 0, 1)),
            ("EMPTY_COMMAND", (0, 1, 1)),
            ("INVALID_FACING", (0, 1, 1)),
            ("MISSING_BLOCK_ENTITY", (2, 1, 0)),
        }
        self.assertTrue(required <= findings, required - findings)
        self.assertTrue(all(isinstance(issue["severity"], str) and issue["severity"]
                            for issue in result["issues"]))

    def test_findings_dont_echo_command_body(self):
        self.assertNotIn(SAMPLE_COMMAND, json.dumps(inspect_bytes(make_structure(FINDINGS))))

    def test_malformed_data_is_rejected(self):
        payload = make_structure(CLEAN)
        for malformed in (b"", b"not NBT", payload[:-1], payload + b"\x01",
                          make_structure(CLEAN, first_index=10),
                          make_structure(CLEAN, version=999)):
            with self.subTest(length=len(malformed)), self.assertRaises(ValueError):
                inspect_bytes(malformed)


class CLITests(unittest.TestCase):
    def test_exit_statuses_and_no_command_disclosure(self):
        root = Path(__file__).resolve().parent.parent
        cases = ((0, make_structure(CLEAN)), (1, make_structure(FINDINGS)), (2, b"not NBT"))
        with tempfile.TemporaryDirectory() as tmp:
            for status, payload in cases:
                with self.subTest(status=status):
                    file = Path(tmp) / f"structure {status}.mcstructure"
                    file.write_bytes(payload)
                    result = subprocess.run(
                        [sys.executable, "-m", "mcstructure_check", str(file)],
                        cwd=root, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=10,
                    )
                    output = result.stdout + result.stderr
                    self.assertEqual(result.returncode, status, output)
                    self.assertNotIn(SAMPLE_COMMAND, output)
                    self.assertNotIn("Traceback", output)
                    self.assertEqual(file.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
