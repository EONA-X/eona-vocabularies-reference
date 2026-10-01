# Contributing

Thanks for considering a contribution to the Eona-X vocabulary sources. This
repository holds the reference Turtle for the ontologies/vocabularies the
[Eona Vocabulary Hub](https://github.com/Eona-X/eona-vocabulary-services)
publishes, plus the metadata describing each one.

## What lives here

One directory per asset, named by its slug, holding one directory per version:

```
<slug>/
├── v<version>/               # one per published version, e.g. v0.1.0/ — v + its dcat:version
│   ├── ontology.ttl          # the graph (alignment.ttl for a crosswalk; another name if metadata.ttl declares it)
│   └── metadata.ttl          # title, description, classification, dcat:version, upstream attribution
├── v<next-version>/          # a new version goes next to the previous ones, which stay published
└── TERMS.md                  # optional: field-by-field documentation of the asset
```

To release a new version, copy the current version directory to `v<new-version>/`,
change it there, and bump `dcat:version` (and, for a vocabulary minted under
`https://eona-x.eu/`, `owl:versionInfo` and the version in its IRIs). Earlier
versions stay as they are: their IRIs are in use.

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
@prefix schema: <http://schema.org/> .

<> a dcat:Dataset, adms:Asset ;
    dcat:version "0.1.0" ;
    dcterms:title "Example Vocabulary"@en ;
    dcterms:description "One-line description shown in the catalog."@en ;
    dcat:type assettype:c_89b4bdb7 ;
    adms:status status:CURRENT .

# Optional upstream attribution (an Eona-X original with no external upstream
# omits this entirely).
<> dcterms:creator [ a foaf:Agent ; foaf:name "Standards Body Name" ] .

# Optional hero/logo image for the catalog card — a plain filename literal,
# resolved by the publishing pipeline into assets/<value>. schema:logo accepts
# text as well as a URL, so a build-relative filename needs no custom term.
<> schema:logo "logo-filename.png" .

# Optional — only when the graph file is not ontology.ttl (alignment.ttl for a
# crosswalk): name it as this asset's distribution, relative to this file.
# <> dcat:distribution [ a dcat:Distribution ; dcat:downloadURL <my-graph.ttl> ; dcat:mediaType "text/turtle" ] .

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
withdrawn. `eonax-metadata-profile/v<newest>/ontology.ttl` (see below) SHACL-validates
`dcat:type` and `adms:status` against exactly the concepts the hub currently
uses, defaulting `adms:status` to `status:CURRENT` — read its `rdfs:comment`/
`skos:definition` annotations for the reasoning behind each constraint before
picking a value outside that set.

EuroVoc theming (`dcat:theme`) is intentionally **not** part of `metadata.ttl`
— it's a ~400MB thesaurus, deferred as too heavy for this pass (eona-x/backlog#791).

### IRIs: `https://eona-x.eu/<asset-type>/<slug>/<version>#<term>`

Vocabularies Eona-X mints are published at

```
https://eona-x.eu/<asset-type>/<slug>/<version>#<term>
```

- `<asset-type>` is one of `ontology`, `shape`, `crosswalk`, `vocabulary`,
  `codelist`, and must cover the asset's `dcat:type`: `ontology` ⇐ Formal
  ontology; `shape` ⇐ Application profile, Markup schema; `crosswalk` ⇐
  Alignment; `vocabulary` ⇐ Terminology, Thesaurus, Glossary, Dictionary,
  Lexicon, Synonym ring, Folksonomy, Categorisation; `codelist` ⇐ Code list,
  Authority file.
- `<version>` is `v` + the root's `owl:versionInfo`, e.g. `v0.1.0`.
- The root (`owl:Ontology`, or `skos:ConceptScheme` for a code list or
  thesaurus) is the namespace itself, `…/<version>#`; code lists embedded in the
  vocabulary live under it (`…/<version>#StatusCodes`, `…/<version>#StatusCodes/active`).

No other IRI on an Eona-X host (`eona-x.eu` and its subdomains, `w3id.org/eonax/`)
is accepted. Vocabularies maintained elsewhere keep their own upstream namespaces.

### Checks on every pull request

`tools/vocabulary-check` runs on every pull request (and is what the publishing
pipeline builds with); run it locally with

```
cargo run --manifest-path tools/vocabulary-check/Cargo.toml -- .
```

It reports every finding at once: Turtle that does not parse, an asset not in a
`<slug>/v<version>/` directory or whose `dcat:version` does not name it, a `metadata.ttl`
without `dcterms:title`, a Formal ontology without `owl:Ontology`, a crosswalk
whose `void:Linkset` does not reach two published vocabularies, a reference to
an ontology of this repository that has no `metadata.ttl`, and any IRI on an
Eona-X host that is not the convention above. A second job validates every
`metadata.ttl` against the newest `eonax-metadata-profile/v*/ontology.ttl` with pySHACL.

## Kinds of contribution

- **Fix an error** in an existing ontology (a wrong domain/range, a missing
  label, a broken `owl:versionInfo`) — open a PR against the relevant
  `<slug>/v<version>/ontology.ttl` — or, if the version is already in use downstream, release the fix as a new version (see above).
- **Update to a newer upstream release** — add it as a new version directory,
  `<slug>/v<upstream-version>/`, with its own `metadata.ttl` (`dcat:version` set
  to the upstream version); the earlier version stays published next to it.
- **Add a new vocabulary** — open an issue first describing what it is and
  why it belongs here; once agreed, add a new `<slug>/` directory following
  the layout above.
- **Improve metadata** — a better description, a missing upstream logo, a
  `TERMS.md` write-up.

## Guidelines

- Keep each ontology's Turtle **self-contained**: no `owl:imports` of
  something not itself vendored here or resolvable without network access at
  build time (downstream builds are offline by design).
- Run the checks above before opening a PR; they include Turtle parsing.
- One logical change per PR — a metadata fix and an ontology content change
  are easier to review separately.
- By contributing, you agree your contribution is licensed under this
  repository's [Apache 2.0 license](./LICENSE). If you're contributing an
  upstream standard's own Turtle, make sure its license permits
  redistribution here and note that in `metadata.ttl`/`TERMS.md`.
- `metadata.ttl` changes should also satisfy the newest `eonax-metadata-profile/v*/ontology.ttl`,
  the hub-wide SHACL profile for this file (see `## What lives here` above);
  validate with e.g. `pyshacl -s eonax-metadata-profile/v1.3.0/ontology.ttl -d <slug>/<version>/metadata.ttl`
  if you have pySHACL installed. The relative `<>` subject in `metadata.ttl`
  is the asset itself: tools resolve it against any base they choose (the
  catalog uses `https://vocabulary.eona-x.eu/catalog/<slug>`).

## Questions

Open an issue — for a question about a specific vocabulary, tag it with the
ontology's slug.
