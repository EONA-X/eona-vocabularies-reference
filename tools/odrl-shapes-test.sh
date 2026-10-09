#!/usr/bin/env bash
# Runs the example policies of eonax-odrl-profile-shapes through pySHACL against the
# newest shapes version: every tests/conforming/*.jsonld must conform (warnings
# allowed), every tests/violating/*.jsonld must not, and its report must contain the
# message fragment in the matching .expect file.
set -uo pipefail
cd "$(dirname "$0")/.."
shapes=$(ls -d eonax-odrl-profile-shapes/v*/ | sort -V | tail -1)ontology.ttl
echo "shapes: $shapes"
status=0
for f in eonax-odrl-profile-shapes/tests/conforming/*.jsonld; do
  if out=$(pyshacl -w -s "$shapes" -df json-ld "$f" 2>&1); then
    echo "ok   conforms   $f"
  else
    echo "FAIL conforms   $f"; echo "$out" | sed 's/^/     /'; status=1
  fi
done
for f in eonax-odrl-profile-shapes/tests/violating/*.jsonld; do
  expect=$(head -1 "${f%.jsonld}.expect")
  if out=$(pyshacl -w -s "$shapes" -df json-ld "$f" 2>&1); then
    echo "FAIL violates   $f (conforms)"; status=1
  elif ! grep -qF -- "$expect" <<<"$out"; then
    echo "FAIL violates   $f (no \"$expect\" in the report)"; echo "$out" | sed 's/^/     /'; status=1
  else
    echo "ok   violates   $f"
  fi
done
exit $status
