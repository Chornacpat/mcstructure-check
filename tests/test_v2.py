import unittest

from mcstructure_check.inspect import inspect_bytes
from tests.make_fixtures import CLEAN, FINDINGS, make_structure


class V2Tests(unittest.TestCase):
    def test_single_layer_int_array(self):
        report = inspect_bytes(make_structure(CLEAN, version=2))
        self.assertEqual(report["format_version"], 2)
        self.assertEqual(report["command_block_count"], 1)
        self.assertEqual(report["issue_count"], 0)

    def test_both_conditional_conflicts_at_same_positions_in_both_versions(self):
        v1 = inspect_bytes(make_structure(FINDINGS, version=1))
        v2 = inspect_bytes(make_structure(FINDINGS, version=2))
        self.assertEqual(v1["issues"], v2["issues"])
