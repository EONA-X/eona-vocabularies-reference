# Contributing

Thanks for considering a contribution to the Eona-X vocabulary sources. This
repository holds the reference Turtle for the ontologies/vocabularies the
[Eona Vocabulary Hub](https://github.com/Eona-X/eona-vocabulary-services)
publishes, plus the metadata describing each one.

## What lives here

One directory per ontology, named by its slug:

```
<slug>/
├── ontology.ttl          # the vocabulary itself — owl:versionInfo is its version of record
├── catalog-fragment.ttl  # optional: additional catalog/display metadata (see below)
├── metadata.ttl          # title, description, classification, upstream attribution
└── TERMS.md              # optional: field-by-field documentation
```

### `metadata.ttl`

Each vocabulary's `metadata.ttl` is real DCAT-AP 3.0.0 + ADMS 2.00 RDF (Turtle),
not Python-mapped literals — the hub's own asset descriptions are semantically
self-describing (eona-x/backlog#793). Every asset is modeled as **both**
`dcat:Dataset` and `adms:Asset`:

```turtle
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix adms: <http://www.w3.org/ns/adms#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix vann: <http://purl.org/vocab/vann/> .
@prefix assettype: <http://publications.europa.eu/resource/authority/asset-classification/> .
@prefix status: <http://publications.europa.eu/resource/authority/concept-status/> .
@prefix eona: <https://vocab.eona-x.eu/> .

<> a dcat:Dataset, adms:Asset ;
    dcterms:title "Example Vocabulary"@en ;
    dcterms:description "One-line description shown in the catalog."@en ;
    dcat:type assettype:c_89b4bdb7 ;
    adms:status status:CURRENT .

# Optional upstream attribution (an Eona-X original with no external upstream
# omits this entirely).
<> dcterms:creator [ a foaf:Agent ; foaf:name "Standards Body Name" ] .

# Optional hero/logo image for the catalog card — a plain filename literal,
# resolved by generate.py into assets/<value> exactly like the old
# metadata.toml upstream.logo did. It's a build-relative filename, not a
# dereferenceable IRI at authoring time, so a literal on the custom eona:logo
# property (reusing the eona: prefix rather than stretching foaf:depiction's
# resource-typed range) is the pragmatic choice.
<> eona:logo "logo-filename.png" .

# Optional — only when this vocabulary needs a Prez curie prefix binding for
# its own namespace (most vocabularies don't need one).
# [] vann:preferredNamespacePrefix "prefix" ;
#     vann:preferredNamespaceUri "https://example.org/ns#" .
```

`dcat:type` — pick exactly one Asset Classification concept, matching the old
`metadata.toml` `type` key (default was `"owl"` when the key was absent):

| old `type=` | Asset Classification concept | Use for |
| --- | --- | --- |
| `"owl"` (or absent) | `assettype:c_89b4bdb7` "Formal ontology" | an OWL/RDFS ontology |
| `"shacl"` | `assettype:c_3948c2ed` "Markup schema" | a SHACL shapes graph |
| `"crosswalk"` | `assettype:c_bba2bb35` "Alignment" | a SKOS crosswalk between two vocabularies (confirmed in eona-x/backlog#800) |
| — | `assettype:c_64714767` "Terminology" | a SKOS-based vocabulary defining terms (concepts, collections), not classes or properties — e.g. the Eona-X ODRL profile |

`assettype:` expands to
`<http://publications.europa.eu/resource/authority/asset-classification/>`.

`adms:status` — the vocabulary's lifecycle state, from the Concept Status
authority table (`status:` = `<http://publications.europa.eu/resource/authority/concept-status/>`).
Every vocabulary currently published here is `status:CURRENT`; the full table
also has `DRAFT`, `DEPRECATED`, `RETIRED`, `CANDIDATE`, `PLANNED`, `REVISED`,
`WAITING` (and `*_DEPRECATED` variants) for when one is actually superseded or
withdrawn. `eonax-metadata-profile/ontology.ttl` (see below) SHACL-validates
`dcat:type` and `adms:status` against exactly the concepts the hub currently
uses, defaulting `adms:status` to `status:CURRENT` — read its `rdfs:comment`/
`skos:definition` annotations for the reasoning behind each constraint before
picking a value outside that set.

EuroVoc theming (`dcat:theme`) is intentionally **not** part of `metadata.ttl`
— it's a ~400MB thesaurus, deferred as too heavy for this pass (eona-x/backlog#791).

### `catalog-fragment.ttl`

Per-vocabulary Prez curie-prefix bindings (`vann:preferredNamespacePrefix` /
`vann:preferredNamespaceUri`) now live inline in `metadata.ttl` (see above)
rather than in a separate `catalog-fragment.ttl`. A `catalog-fragment.ttl`
sibling is still used where it carries more than that — e.g. merging a
vocabulary's browsable `skos:ConceptScheme`(s) into the shared `eona:catalog`
via `dcterms:hasPart`, with their own title/description so Prez renders them
as collections. Both files load into the same named graph
(`https://vocab.eona-x.eu/catalog/<slug>`), so there's no need to duplicate
that catalog-membership content into `metadata.ttl`.

## Kinds of contribution

- **Fix an error** in an existing ontology (a wrong domain/range, a missing
  label, a broken `owl:versionInfo`) — open a PR against the relevant
  `<slug>/ontology.ttl`.
- **Update to a newer upstream release** — bump the bundled Turtle and
  `owl:versionInfo` together, and note the upstream version in your PR
  description.
- **Add a new vocabulary** — open an issue first describing what it is and
  why it belongs here; once agreed, add a new `<slug>/` directory following
  the layout above.
- **Improve metadata** — a better description, a missing upstream logo, a
  `TERMS.md` write-up.

## Guidelines

- Keep each ontology's Turtle **self-contained**: no `owl:imports` of
  something not itself vendored here or resolvable without network access at
  build time (downstream builds are offline by design).
- Validate your Turtle parses before opening a PR (any RDF library will do,
  e.g. `python3 -c "import rdflib; rdflib.Graph().parse('slug/ontology.ttl')"`
  or `riot --validate slug/ontology.ttl` from Apache Jena).
- One logical change per PR — a metadata fix and an ontology content change
  are easier to review separately.
- By contributing, you agree your contribution is licensed under this
  repository's [Apache 2.0 license](./LICENSE). If you're contributing an
  upstream standard's own Turtle, make sure its license permits
  redistribution here and note that in `metadata.ttl`/`TERMS.md`.
- `metadata.ttl` changes should also satisfy `eonax-metadata-profile/ontology.ttl`,
  the hub-wide SHACL profile for this file (see `## What lives here` above);
  validate with e.g. `pyshacl -s eonax-metadata-profile/ontology.ttl -d <slug>/metadata.ttl`
  if you have pySHACL installed. Either way, when validating any `.ttl` file
  with rdflib, pass `publicID='https://vocab.eona-x.eu/catalog/<slug>'` — that's
  the base IRI the consuming `generate.py` loads it with, and it's what makes
  the relative `<>` subject in `metadata.ttl` resolve correctly.

## Questions

Open an issue — for a question about a specific vocabulary, tag it with the
ontology's slug.
