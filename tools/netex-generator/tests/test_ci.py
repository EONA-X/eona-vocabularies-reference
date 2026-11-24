import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WORKFLOW = os.path.join(HERE, "..", "..", "..", ".github", "workflows", "verify.yml")


def job_text():
    with open(WORKFLOW, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^  netex-generator:\n(.*?)(?=^  \S|\Z)", text, re.S | re.M)
    return m.group(1) if m else None


class WorkflowTest(unittest.TestCase):
    def test_job_runs_the_unit_tests_and_the_drift_check(self):
        job = job_text()
        self.assertIsNotNone(job, "no netex-generator job in verify.yml")
        self.assertIn("pip install -r tools/netex-generator/requirements.txt", job)
        self.assertIn("python -m unittest discover -s tools/netex-generator/tests -t tools/netex-generator", job)
        self.assertIn("tools/netex-generator/regenerate.sh --check netex", job)

    def test_pinned_schema_is_cached_by_the_pin_file_and_still_verified(self):
        job = job_text()
        self.assertIn("hashFiles('tools/netex-generator/sources.json')", job)
        self.assertIn("NETEXGEN_SOURCES", job)

    def test_pins_are_verified_before_the_unit_tests_run_on_the_cached_files(self):
        job = job_text()
        verify = job.find('netexgen.fetch --name netex --local "$RUNNER_TEMP/netex-src"')
        tests = job.find("python -m unittest discover")
        self.assertNotEqual(verify, -1, "no sha256 verification of the restored files")
        self.assertLess(verify, tests)

    def test_only_official_actions_are_used(self):
        for uses in re.findall(r"uses:\s*(\S+)", job_text()):
            self.assertTrue(uses.startswith("actions/"), uses)


if __name__ == "__main__":
    unittest.main()
