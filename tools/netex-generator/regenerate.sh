#!/usr/bin/env bash
# Regenerate netex/v1.0.0/ontology.ttl from the pinned NeTEx XSD.
#   tools/netex-generator/regenerate.sh [--check] netex
# --check writes to a temp dir and fails (exit 1) when the committed file differs.
# NETEXGEN_SOURCES=<dir> skips the download (the sha256 pins are still verified);
# it holds the pinned files at their sources.json paths, i.e. the checkout root that contains xsd/.
# PYTHON overrides the interpreter (needs rdflib from requirements.txt).
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$here/../.." && pwd)
py=${PYTHON:-python3}
check=0
if [ "${1:-}" = "--check" ]; then check=1; shift; fi
target=${1:-}
case "$target" in
  netex) ;;
  *) echo "usage: $0 [--check] netex" >&2; exit 2 ;;
esac

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

run() { "$py" -I "$here/run.py" "$@"; }   # downloads are only ever passed as path arguments

out_rel=netex/v1.0.0/ontology.ttl
if [ -n "${NETEXGEN_SOURCES:-}" ]; then
  src=${NETEXGEN_SOURCES%/}
  run netexgen.fetch --name netex --local "$src"
else
  src=$tmp/src-netex
  run netexgen.fetch --name netex --dest "$src"
fi
if [ "$check" = 1 ]; then out=$tmp/netex.ttl; else out=$root/$out_rel; fi
mkdir -p "$(dirname "$out")"
run netexgen.netex_owl --xsd-dir "$src/xsd" --sources "$here/sources.json" --out "$out"
if [ "$check" = 1 ]; then
  if ! diff -u "$root/$out_rel" "$out" > "$tmp/netex.diff" 2>&1; then
    echo "drift: $out_rel differs from the generator output" >&2
    head -40 "$tmp/netex.diff" >&2
    exit 1
  fi
  echo "ok   $out_rel"
else
  echo "wrote $out_rel"
fi
