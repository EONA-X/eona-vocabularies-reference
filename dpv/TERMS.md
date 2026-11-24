# W3C Data Privacy Vocabulary (DPV)

Upstream: [Data Privacy Vocabulary (DPV)](https://w3id.org/dpv/), W3C Data Privacy Vocabularies and Controls Community Group (DPVCG). Namespace `https://w3id.org/dpv#`.

| Version | Source | sha256 |
| --- | --- | --- |
| `v2.3` | `https://w3id.org/dpv/2.3/dpv/dpv.ttl`, byte-identical to `https://raw.githubusercontent.com/w3c/dpv/5af893701677a4a54a28ad617e350bb98cf4d3b8/2.3/dpv/dpv.ttl` (w3c/dpv commit `5af8937`) | `97bc7ce1a4544d39b9e480eeb7990693bee1155fb094f3dd50b9eb1d0c0d578f` |
| `v2.1` | w3c/dpv master `2.1/dpv/dpv.ttl` (as loaded by eona-vocabulary-services, load-icam); upstream commit not recorded | `bb264ef1e753e789fefb22b67d51a1dcd37879a00649644bf246830aa431c9a3` |

`v2.3/ontology.ttl` is the upstream file, unmodified. It declares one `owl:Ontology` (`<https://w3id.org/dpv>`, `owl:versionIRI <https://w3id.org/dpv/2.3/dpv>`, `owl:versionInfo "2.3"`) and no `owl:imports`, so no deviation from the offline-build rule applies. `v2.1` stays published next to it; both share the namespace `https://w3id.org/dpv`.

The right operands of the Eona-X travel ODRL profile (the `dpv:Purpose` subclasses, `dpv:ConsentGiven`, `dpv:ConsentWithdrawn`, `dpv:PersonalData`) are all declared as `rdfs:Class` in 2.3. The Personal Data Categories extension is vendored as `dpv-pd/v2.3`.

DPV uses `https://schema.org/` (https), while the metadata of this repository and DATAtourisme use `http://schema.org/`. The upstream file is not normalised. schema.org states that `http://schema.org/X` and `https://schema.org/X` denote the same term, so consumers compare terms after rewriting the scheme to `https`; no bridge triples are emitted.

## Licence

DPV declares `dct:license` [W3C Document License 2023](https://www.w3.org/copyright/document-license-2023/). The file carries no copyright notice.
