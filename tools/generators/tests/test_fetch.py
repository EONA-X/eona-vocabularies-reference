import hashlib
import json
import os
import tempfile
import unittest

from eonagen.fetch import ChecksumMismatch, fetch_pinned, verify_dir


def entry(files):
    return {"base": "https://example.org/base/",
            "files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}}


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.files = {"a/b.txt": b"hello", "c.txt": b"world"}

    def test_downloads_and_verifies(self):
        calls = []

        def get(url):
            calls.append(url)
            return self.files[url[len("https://example.org/base/"):]]

        dest = os.path.join(self.tmp.name, "d")
        fetch_pinned(entry(self.files), dest, get)
        self.assertEqual(open(os.path.join(dest, "a/b.txt"), "rb").read(), b"hello")
        self.assertEqual(sorted(calls), ["https://example.org/base/a/b.txt", "https://example.org/base/c.txt"])

    def test_sha_mismatch_is_refused(self):
        dest = os.path.join(self.tmp.name, "d")
        with self.assertRaises(ChecksumMismatch):
            fetch_pinned(entry(self.files), dest, lambda url: b"tampered")
        self.assertFalse(os.path.exists(os.path.join(dest, "c.txt")))

    def test_refuses_non_empty_destination(self):
        dest = os.path.join(self.tmp.name, "d")
        os.makedirs(dest)
        open(os.path.join(dest, "x"), "w").close()
        with self.assertRaises(FileExistsError):
            fetch_pinned(entry(self.files), dest, lambda url: b"")

    def test_refuses_path_traversal(self):
        e = {"base": "https://example.org/", "files": {"../evil": hashlib.sha256(b"x").hexdigest()}}
        with self.assertRaises(ValueError):
            fetch_pinned(e, os.path.join(self.tmp.name, "d"), lambda url: b"x")

    def test_verify_dir_checks_local_copy(self):
        d = os.path.join(self.tmp.name, "local")
        os.makedirs(os.path.join(d, "a"))
        for k, v in self.files.items():
            open(os.path.join(d, k), "wb").write(v)
        verify_dir(entry(self.files), d)
        open(os.path.join(d, "c.txt"), "wb").write(b"changed")
        with self.assertRaises(ChecksumMismatch):
            verify_dir(entry(self.files), d)

    def test_sources_json_is_well_formed(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data = json.load(open(os.path.join(here, "sources.json")))
        for name in ("schema-org-travel", "osdm"):
            self.assertTrue(data[name]["base"].endswith("/"))
            for sha in data[name]["files"].values():
                self.assertEqual(len(sha), 64)


if __name__ == "__main__":
    unittest.main()
