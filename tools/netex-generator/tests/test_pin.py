import hashlib
import json
import os
import tempfile
import unittest

from netexgen import pin
from netexgen.xsd_load import ClosureError, closure

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_ROOT = os.path.join(HERE, "fixtures", "netex")
ENTRY = "xsd/NeTEx_publication.xsd"
SCHEMA = ('<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
          'targetNamespace="urn:t">%s</xsd:schema>')


def write(root, rel, body):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(SCHEMA % body)


class ClosureTest(unittest.TestCase):
    def test_fixture_closure_is_complete_and_sorted(self):
        got = closure(FIXTURE_ROOT, ENTRY, confine="xsd")
        self.assertEqual(got, [
            "xsd/NeTEx_publication.xsd",
            "xsd/gml/gml_base.xsd",
            "xsd/netex_framework/netex_base.xsd",
            "xsd/netex_part_1/netex_equipment.xsd",
            "xsd/siri/siri_base.xsd",
        ])

    def test_include_cycle_terminates(self):
        # netex_base.xsd and netex_equipment.xsd include each other
        self.assertEqual(len(closure(FIXTURE_ROOT, ENTRY, confine="xsd")), 5)

    def refused(self, location, **kw):
        with tempfile.TemporaryDirectory() as d:
            write(d, "xsd/a.xsd", '<xsd:include schemaLocation="%s"/>' % location)
            write(d, "xsd/b.xsd", "")
            write(d, "other.xsd", "")
            with self.assertRaises(ClosureError):
                closure(d, "xsd/a.xsd", confine="xsd")

    def test_remote_location_is_refused(self):
        self.refused("https://example.org/b.xsd")

    def test_absolute_location_is_refused(self):
        self.refused("/etc/passwd")

    def test_escape_from_the_xsd_directory_is_refused(self):
        self.refused("../other.xsd")

    def test_missing_file_is_refused(self):
        self.refused("missing.xsd")

    def test_redefine_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "xsd/a.xsd", '<xsd:redefine schemaLocation="b.xsd"/>')
            write(d, "xsd/b.xsd", "")
            with self.assertRaises(ClosureError):
                closure(d, "xsd/a.xsd", confine="xsd")


class EntryTest(unittest.TestCase):
    def test_entry_lists_every_file_with_its_digest(self):
        e = pin.build_entry(FIXTURE_ROOT, ENTRY, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "https://example.org/raw/")
        self.assertEqual(e["base"], "https://example.org/raw/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/")
        self.assertEqual(list(e["files"]), sorted(e["files"]))
        path = os.path.join(FIXTURE_ROOT, "xsd", "gml", "gml_base.xsd")
        with open(path, "rb") as f:
            self.assertEqual(e["files"]["xsd/gml/gml_base.xsd"], hashlib.sha256(f.read()).hexdigest())

    def test_json_output_is_stable(self):
        a = pin.render(pin.build_entry(FIXTURE_ROOT, ENTRY, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "https://example.org/raw/"))
        b = pin.render(pin.build_entry(FIXTURE_ROOT, ENTRY, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "https://example.org/raw/"))
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("\n"))
        self.assertEqual(json.loads(a)["files"].keys(), pin.build_entry(
            FIXTURE_ROOT, ENTRY, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "https://example.org/raw/")["files"].keys())

    def test_commit_must_be_a_full_sha(self):
        with self.assertRaises(ValueError):
            pin.build_entry(FIXTURE_ROOT, ENTRY, "main", "https://example.org/raw/")


if __name__ == "__main__":
    unittest.main()
