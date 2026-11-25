"""Download pinned upstream files into a fresh directory and verify sha256.

The downloaded files are data. Nothing here imports or executes them.
Usage: python -m eonagen.fetch --name NAME --dest DIR [--local DIR]
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request


class ChecksumMismatch(Exception):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _check_rel(rel):
    parts = rel.split("/")
    if rel.startswith("/") or ".." in parts or "" in parts:
        raise ValueError("unsafe path in sources.json: %r" % rel)


def _urlopen_get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def fetch_pinned(entry, dest, get=_urlopen_get):
    for rel in entry["files"]:
        _check_rel(rel)
    if os.path.isdir(dest) and os.listdir(dest):
        raise FileExistsError("destination is not empty: " + dest)
    os.makedirs(dest, exist_ok=True)
    try:
        for rel, sha in entry["files"].items():
            data = get(entry["base"] + rel)
            if _sha(data) != sha:
                raise ChecksumMismatch("%s: expected %s, got %s" % (rel, sha, _sha(data)))
            path = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise


def verify_dir(entry, directory):
    for rel, sha in entry["files"].items():
        _check_rel(rel)
        with open(os.path.join(directory, rel), "rb") as f:
            got = _sha(f.read())
        if got != sha:
            raise ChecksumMismatch("%s: expected %s, got %s" % (rel, sha, got))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--dest")
    ap.add_argument("--local", help="verify an existing directory instead of downloading")
    ap.add_argument("--sources", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources.json"))
    a = ap.parse_args(argv)
    with open(a.sources) as f:
        entry = json.load(f)[a.name]
    if a.local:
        verify_dir(entry, a.local)
    else:
        fetch_pinned(entry, a.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
