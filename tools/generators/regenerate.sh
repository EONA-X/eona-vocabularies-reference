#!/usr/bin/env bash
# Regenerate the generated vocabulary assets from their pinned upstream files.
#   tools/generators/regenerate.sh [--check] <schema-org-travel|osdm|all>
# --check writes to a temp dir and fails (exit 1) when the committed file differs.
# EONAGEN_SOURCES=<dir> skips the download (the sha256 pins are still verified);
# it holds the pinned files at their sources.json paths (one directory can serve all targets).
# PYTHON overrides the interpreter (needs rdflib and PyYAML from requirements.txt).
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$here/../.." && pwd)
py=${PYTHON:-python3}
check=0
if [ "${1:-}" = "--check" ]; then check=1; shift; fi
target=${1:-}
case "$target" in
  schema-org-travel|osdm) targets=("$target") ;;
  all) targets=(schema-org-travel osdm) ;;
  *) echo "usage: $0 [--check] <schema-org-travel|osdm|all>" >&2; exit 2 ;;
esac

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

run() { "$py" -I "$here/run.py" "$@"; }   # downloads are only ever passed as path arguments

status=0
for t in "${targets[@]}"; do
  case "$t" in
    schema-org-travel) out_rel=schema-org-travel/v30.1/ontology.ttl ;;
    osdm) out_rel=osdm/v3.11/ontology.ttl ;;
  esac
  if [ -n "${EONAGEN_SOURCES:-}" ]; then
    src=${EONAGEN_SOURCES%/}
    run eonagen.fetch --name "$t" --local "$src"
  else
    src=$tmp/src-$t
    run eonagen.fetch --name "$t" --dest "$src"
  fi
  if [ "$check" = 1 ]; then out=$tmp/$t.ttl; else out=$root/$out_rel; fi
  mkdir -p "$(dirname "$out")"
  case "$t" in
    schema-org-travel)
      run eonagen.schema_org_slice --source "$src/data/releases/30.1/schemaorg-current-https.ttl" --out "$out" ;;
    osdm)
      run eonagen.osdm_owl --spec-dir "$src/specification" --out "$out" ;;
  esac
  if [ "$check" = 1 ]; then
    if ! diff -u "$root/$out_rel" "$out" > "$tmp/$t.diff" 2>&1; then
      echo "drift: $out_rel differs from the generator output" >&2
      head -40 "$tmp/$t.diff" >&2
      status=1
    else
      echo "ok   $out_rel"
    fi
  else
    echo "wrote $out_rel"
  fi
done
exit $status
