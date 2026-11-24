"""turtle.py, fetch.py and run.py are copies of the vocabulary generators' files
(tools/generators in eona-x/backlog#1319, branch feat/1319-travel-vocabulary-assets,
commit 88d7889). They must stay byte-identical so the two tools can be unified by
moving files. Update the digests only together with the same change in tools/generators.
"""
import hashlib
import os
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHA256 = {
    "netexgen/turtle.py": "2bf96294c92ee928c450d7a0568532673796ef4d49874a4496a8a44fe5b7766e",
    "netexgen/fetch.py": "51da1d1025dcd055df5715599d9d0cf0047fa2126a466636336dadcb9d01d0f5",
    "run.py": "c8fb2edd4d534469582cce9780dd84a348aaa2e2fe2980116897d4341556868c",
}


class IdentityTest(unittest.TestCase):
    def test_copied_files_match_the_reference_digests(self):
        for rel, want in SHA256.items():
            with open(os.path.join(HERE, rel), "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), want, rel)


if __name__ == "__main__":
    unittest.main()
