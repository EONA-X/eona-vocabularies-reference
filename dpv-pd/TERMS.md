# DPV Personal Data Categories (PD)

Upstream: [DPV Personal Data Categories extension](https://w3id.org/dpv/pd), W3C Data Privacy Vocabularies and Controls Community Group (DPVCG). Namespace `https://w3id.org/dpv/pd#`.

| Version | Source | sha256 |
| --- | --- | --- |
| `v2.3` | `https://w3id.org/dpv/2.3/pd/pd.ttl`, w3c/dpv commit `5af893701677a4a54a28ad617e350bb98cf4d3b8`, path `2.3/pd/pd.ttl` | `65d3f07a407a76c7dbf2934a386e74137e434f0b0446f93000b4fb580c641080` |

`v2.3/ontology.ttl` is the upstream file, unmodified. It declares one `owl:Ontology` (`<https://w3id.org/dpv/pd>`) and no `owl:imports`.

## Dependency on DPV core

The terms specialise `dpv:` core terms (e.g. `dpv:PersonalData`) without importing them. No `owl:imports` is added: consumers load `dpv/v2.3` alongside this asset. The repository checker raises no reference finding because `dpv/v2.3` is published here.

## Licence

Same as DPV core: [W3C Document License 2023](https://www.w3.org/copyright/document-license-2023/), as declared in the file.
