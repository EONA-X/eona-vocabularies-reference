import json
import os
import subprocess
import unittest

from netexgen import netex_owl

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "sources.json"), encoding="utf-8") as f:
            cls.sources = json.load(f)

    def test_one_entry_named_netex(self):
        self.assertEqual(list(self.sources), ["netex"])

    def test_base_is_pinned_to_the_commit_the_generator_names(self):
        base = self.sources["netex"]["base"]
        self.assertTrue(base.endswith("/"))
        self.assertEqual(base, "https://raw.githubusercontent.com/TransmodelEcosystem/NeTEx/%s/" % netex_owl.COMMIT)

    def test_files_are_the_xsd_closure_with_sha256_pins(self):
        files = self.sources["netex"]["files"]
        self.assertEqual(len(files), 437)
        self.assertEqual(list(files), sorted(files))
        self.assertIn("xsd/NeTEx_publication.xsd", files)
        for path, sha in files.items():
            self.assertTrue(path.startswith("xsd/") and path.endswith(".xsd"), path)
            self.assertRegex(sha, r"^[0-9a-f]{64}$")


class RegenerateScriptTest(unittest.TestCase):
    script = os.path.join(HERE, "regenerate.sh")

    def test_script_is_executable_bash(self):
        self.assertTrue(os.access(self.script, os.X_OK))
        subprocess.run(["bash", "-n", self.script], check=True)

    def test_unknown_target_is_a_usage_error(self):
        r = subprocess.run([self.script, "nope"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)

    def test_a_tampered_source_directory_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "xsd"))
            with open(os.path.join(d, "xsd", "NeTEx_publication.xsd"), "w") as f:
                f.write("<x/>")
            r = subprocess.run([self.script, "--check", "netex"], capture_output=True, text=True,
                               env={**os.environ, "NETEXGEN_SOURCES": d})
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
