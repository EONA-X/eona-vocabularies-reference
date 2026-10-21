#!/usr/bin/env bash
# Runs the example policies of eonax-odrl-profile-shapes through pySHACL against the
# newest shapes version: every tests/conforming/*.jsonld must conform with no result
# at all, not even a warning, unless a matching .expect file names the message
# fragment of the warning it must report; every tests/violating/*.jsonld must not
# conform, and its report must contain the message fragment in the matching .expect
# file.
set -uo pipefail
cd "$(dirname "$0")/.."
shapes=$(ls -d eonax-odrl-profile-shapes/v*/ | sort -V | tail -1)ontology.ttl
echo "shapes: $shapes"
status=0
for f in eonax-odrl-profile-shapes/tests/conforming/*.jsonld; do
  expect=""
  [ -f "${f%.jsonld}.expect" ] && expect=$(head -1 "${f%.jsonld}.expect")
  if ! out=$(pyshacl -w -s "$shapes" -df json-ld "$f" 2>&1); then
    echo "FAIL conforms   $f"; echo "$out" | sed 's/^/     /'; status=1
  elif [ -z "$expect" ] && grep -q '^Results (' <<<"$out"; then
    echo "FAIL conforms   $f (conforms, but with results)"; echo "$out" | sed 's/^/     /'; status=1
  elif [ -n "$expect" ] && ! grep -qF -- "$expect" <<<"$out"; then
    echo "FAIL conforms   $f (no \"$expect\" warning in the report)"; echo "$out" | sed 's/^/     /'; status=1
  else
    echo "ok   conforms   $f"
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
