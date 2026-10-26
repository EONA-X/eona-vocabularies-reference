# IATA ONE Record ontology

Verbatim copies of the IATA ONE Record data-model ontology, published by IATA
under the MIT licence (`LICENSE` in this directory). Terms keep their upstream
namespace, `https://onerecord.iata.org/ns/cargo#`.

| Version | Upstream file | Commit |
| --- | --- | --- |
| `v3.2-rc2` | `2025-07-standard/Data-Model/IATA-1R-DM-Ontology.ttl` | `5de71a0da2989808c64133091b4055908ecc620f` |
| `v3.3` | `2026-07-standard/Data-Model/IATA-1R-DM-Ontology.ttl` | `49e8ac1bfdc24d76fddf307e87f36e381b6941b1` |

Both import the code lists, vendored separately as
[`iata-one-record-code-lists/v1.1.0`](../iata-one-record-code-lists/).

## Differences from upstream

- Line endings are LF (upstream `v3.2-rc2` is CRLF). The content is otherwise byte-identical.
- `v3.3` imports `<https://onerecord.iata.org/ns/code-lists/1.1.0>` (the code lists'
  `owl:versionIRI`) instead of upstream's
  `<https://raw.githubusercontent.com/IATA-Cargo/ONE-Record/refs/heads/master/2026-07-standard/Data-Model/IATA-1R-CL-Ontology.ttl>`.
  That URL follows a moving branch and needs the network at build time; the
  versioned IRI is the one `v3.2-rc2` already uses, and it names the vendored copy.
- `v3.2-rc2` is a snapshot taken between release candidates: its
  `owl:versionIRI` already reads `…/cargo/3.2` while `owl:versionInfo` reads
  `3.2-rc2`. IATA has since released 3.2 final.
