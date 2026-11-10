#!/usr/bin/env bash
# Runs the fixtures of eonax-chart-profile through pySHACL against the newest
# profile version: every tests/conforming/*.jsonld must conform; every
# tests/violating/*.jsonld must not conform, and its report must contain the
# message fragment in the matching .expect file. It also checks that
# context.jsonld expands tests/context/short-terms.jsonld to the same graph as
# the long-form conforming fixture category-bar-minimal.jsonld.
set -uo pipefail
cd "$(dirname "$0")/.."
shapes=$(ls -d eonax-chart-profile/v*/ | sort -V | tail -1)ontology.ttl
ctxfile="$(dirname "$shapes")/context.jsonld"
echo "shapes: $shapes"
status=0
for f in eonax-chart-profile/tests/conforming/*.jsonld; do
  if out=$(pyshacl -w -s "$shapes" -df json-ld "$f" 2>&1); then
    echo "ok   conforms   $f"
  else
    echo "FAIL conforms   $f"; echo "$out" | sed 's/^/     /'; status=1
  fi
done
for f in eonax-chart-profile/tests/violating/*.jsonld; do
  expect=$(head -1 "${f%.jsonld}.expect")
  if out=$(pyshacl -w -s "$shapes" -df json-ld "$f" 2>&1); then
    echo "FAIL violates   $f (conforms)"; status=1
  elif ! grep -qF -- "$expect" <<<"$out"; then
    echo "FAIL violates   $f (no \"$expect\" in the report)"; echo "$out" | sed 's/^/     /'; status=1
  else
    echo "ok   violates   $f"
  fi
done
if python3 - "$ctxfile" eonax-chart-profile/tests/context/short-terms.jsonld \
    eonax-chart-profile/tests/conforming/category-bar-minimal.jsonld <<'PY'
import json, sys
from rdflib import Graph
from rdflib.compare import isomorphic
ctx, short, long_ = sys.argv[1:]
c = json.load(open(ctx))
s = json.load(open(short)); s["@context"] = c["@context"]
a = Graph().parse(data=json.dumps(s), format="json-ld")
b = Graph().parse(long_, format="json-ld")
if not isomorphic(a, b):
    print("graphs differ: %d vs %d triples" % (len(a), len(b))); sys.exit(1)
PY
then echo "ok   context    $ctxfile"; else echo "FAIL context    $ctxfile"; status=1; fi
exit $status
