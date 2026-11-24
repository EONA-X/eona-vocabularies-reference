# Vocabulary generators

Generate `schema-org-travel/v30.1/ontology.ttl` and `osdm/v3.11/ontology.ttl` from pinned upstream files (eona-x/backlog#1319).

```sh
pip install -r tools/generators/requirements.txt     # rdflib==7.6.0, PyYAML==6.0.4
tools/generators/regenerate.sh all                   # rewrite the committed files
tools/generators/regenerate.sh --check all           # exit 1 when a committed file differs
python -m unittest discover -s tools/generators/tests -t tools/generators
```

- `sources.json` pins each upstream file by URL (commit) and sha256. A mismatch aborts the run.
- Downloads go into a fresh temporary directory and are only passed as path arguments to the generators, which run with `python -I` (via `run.py`). Nothing downloaded is imported or executed.
- `EONAGEN_SOURCES=<dir>` skips the download. The directory holds the pinned files at their `sources.json` paths (`data/releases/...`, `specification/...`); the sha256 pins are still verified. The same variable enables the smoke tests against the real files.
- `PYTHON=<interpreter>` selects the Python used by the script.
- The output is deterministic (sorted subjects, predicates and objects, inline anonymous nodes, no timestamps): a second run changes nothing.
- CI: the `generators` job in `.github/workflows/verify.yml` runs the unit tests and `regenerate.sh --check all`.
- Per-asset documentation: `schema-org-travel/TERMS.md`, `osdm/TERMS.md`.

To move to a new upstream release, update `sources.json` and the version constants in the generator, add a new `<slug>/v<version>/` directory (see CONTRIBUTING.md), and regenerate.
