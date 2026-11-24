# NeTEx generator

Generates `netex/v1.0.0/ontology.ttl` from the pinned NeTEx v2.0 XML Schema (eona-x/backlog#1320).

```sh
pip install -r tools/netex-generator/requirements.txt   # rdflib==7.6.0
tools/netex-generator/regenerate.sh netex               # rewrite the committed file
tools/netex-generator/regenerate.sh --check netex       # exit 1 when the committed file differs
python -m unittest discover -s tools/netex-generator/tests -t tools/netex-generator
```

- `sources.json` pins the 437 files of the `xsd:include` / `xsd:import` closure of `xsd/NeTEx_publication.xsd` by URL (commit `11d40b5e94684fa2ddea0222702b220d7d93760b` of `TransmodelEcosystem/NeTEx`, branch `v2.0`) and sha256. A mismatch aborts the run.
- At generation time the loader recomputes the closure from the entry file and fails when it differs from the pinned set (a file that is not pinned, or a pinned file that is never reached).
- Downloads go into a fresh temporary directory and are only passed as path arguments to the generator, which runs with `python -I` (via `run.py`). The schema files are parsed as data with `xml.etree.ElementTree`. Nothing downloaded is imported or executed.
- `NETEXGEN_SOURCES=<dir>` skips the download. The directory holds the pinned files at their `sources.json` paths (`xsd/...`), for example a checkout of the pinned commit; the sha256 pins are still verified. The same variable enables the smoke tests against the real schema.
- `PYTHON=<interpreter>` selects the Python used by the script.
- The output is deterministic (sorted subjects, predicates and objects, inline anonymous nodes, no timestamps): a second run changes nothing, whatever `PYTHONHASHSEED` is.
- CI: the `netex-generator` job in `.github/workflows/verify.yml` runs the unit tests and `regenerate.sh --check netex`.
- Mapping rules, IRI forms and dropped constructs: `netex/TERMS.md`.

## Layout

| File | Role |
|---|---|
| `run.py`, `netexgen/turtle.py`, `netexgen/fetch.py` | Copies of the files of the same name in `tools/generators` (see below) |
| `netexgen/pin.py` | Prints the `sources.json` entry for a local checkout |
| `netexgen/xsd_load.py` | Closure walk, per-(namespace, name) symbol tables, content-model walk with group flattening |
| `netexgen/netex_owl.py` | XSD to OWL mapping, invariants, root ontology, command line |
| `netexgen/v020_alignment.py` | Hand-maintained alignment of the v0.2.0 EV-charging terms to the generated terms |
| `tests/` | Unit tests on a hand-written mini schema (`tests/fixtures/netex/xsd`), a golden file, and smoke tests on the real schema |

## Moving to a newer upstream commit

```sh
git clone https://github.com/TransmodelEcosystem/NeTEx /tmp/netex && git -C /tmp/netex checkout <sha>
python -I tools/netex-generator/run.py netexgen.pin --xsd-root /tmp/netex --commit <sha>   # copy the entry into sources.json
```

Then update `COMMIT` in `netexgen/netex_owl.py`, regenerate, and release the result as a new `netex/v<version>/` directory (see CONTRIBUTING.md). The counts in the generator tests and in `netex/TERMS.md` may need updating.

## Copies of the vocabulary generators' files

`run.py`, `netexgen/turtle.py` and `netexgen/fetch.py` are byte copies of `tools/generators/run.py`, `tools/generators/eonagen/turtle.py` and `tools/generators/eonagen/fetch.py` (branch `feat/1319-travel-vocabulary-assets`, commit 88d7889). `tests/test_identity.py` checks their sha256:

| File | sha256 |
|---|---|
| `run.py` | `c8fb2edd4d534469582cce9780dd84a348aaa2e2fe2980116897d4341556868c` |
| `netexgen/turtle.py` | `2bf96294c92ee928c450d7a0568532673796ef4d49874a4496a8a44fe5b7766e` |
| `netexgen/fetch.py` | `51da1d1025dcd055df5715599d9d0cf0047fa2126a466636336dadcb9d01d0f5` |

The docstring of `fetch.py` still says `eonagen.fetch`; it is kept so the files stay identical.

## Unification with `tools/generators`

Once both pull requests are merged, fold this tool into `tools/generators` in one follow-up pull request:

1. `git mv netexgen/netex_owl.py netexgen/xsd_load.py netexgen/pin.py netexgen/v020_alignment.py` into `tools/generators/eonagen/`, then `sed -i s/netexgen/eonagen/g` on them and on the tests.
2. Delete the copied `turtle.py`, `fetch.py` and `run.py`. `diff` must show they are identical to the `eonagen` versions before deletion; `tests/test_identity.py` encodes the same check.
3. Move the `"netex"` entry of `sources.json` into `tools/generators/sources.json`.
4. Add `netex) out_rel=netex/v1.0.0/ontology.ttl; run eonagen.netex_owl --xsd-dir "$src/xsd" --sources "$here/sources.json" --out "$out"` to `regenerate.sh`, and add `netex` to the `all` set.
5. Merge the tests and fixtures into `tools/generators/tests/` (`tests/helpers.py` becomes a shared module; the golden file moves to `tests/golden/`).
6. Drop the `netex-generator` CI job: the `generators` job then covers it.
7. Rename `NETEXGEN_SOURCES` to `EONAGEN_SOURCES`.
