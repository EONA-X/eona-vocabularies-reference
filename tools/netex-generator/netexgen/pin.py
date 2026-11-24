"""Print the sources.json entry for a local checkout of the NeTEx repository.

python -I run.py netexgen.pin --xsd-root CHECKOUT --entry xsd/NeTEx_publication.xsd --commit SHA

Walks the xsd:include / xsd:import closure of the entry file, rejects remote,
absolute and escaping schemaLocations, and prints {base, files{path: sha256}}
sorted by path. Run it once to create the entry and again on each upstream bump.
"""
import argparse
import hashlib
import json
import os
import re
import sys

from netexgen.xsd_load import closure

RAW_BASE = "https://raw.githubusercontent.com/TransmodelEcosystem/NeTEx/"


def build_entry(xsd_root, entry, commit, raw_base=RAW_BASE):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("commit must be a full 40-character sha, got %r" % commit)
    files = {}
    for rel in closure(xsd_root, entry, confine=entry.split("/")[0]):
        with open(os.path.join(xsd_root, *rel.split("/")), "rb") as f:
            files[rel] = hashlib.sha256(f.read()).hexdigest()
    return {"base": "%s%s/" % (raw_base, commit), "files": files}


def render(entry):
    return json.dumps(entry, indent=2, sort_keys=True) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--xsd-root", required=True, help="checkout root, the directory that contains xsd/")
    ap.add_argument("--entry", default="xsd/NeTEx_publication.xsd")
    ap.add_argument("--commit", required=True)
    a = ap.parse_args(argv)
    sys.stdout.write(render(build_entry(a.xsd_root, a.entry, a.commit)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
