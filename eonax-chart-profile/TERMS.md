# Eona-X Chart Profile

Terms and SHACL shapes for chart datasets expressed with the [W3C RDF Data Cube vocabulary](../data-cube/TERMS.md). The Eona-X UI toolkit chart components read a JSON-LD document that conforms to this profile; `v0.1.0/ontology.ttl` holds both the terms and the shapes.

Namespace `https://eona-x.eu/shape/chart-profile#` (stable; release IRI `https://eona-x.eu/shape/chart-profile/v0.1.0#`). Prefix `chart:`.

## Terms

| Term | Kind | Value | On |
| --- | --- | --- | --- |
| `chart:category` | `qb:DimensionProperty` | `xsd:string` | observation |
| `chart:date` | `qb:DimensionProperty` | `xsd:date`, `xsd:gYearMonth` or `xsd:gYear` | observation |
| `chart:series` | `qb:DimensionProperty` | `xsd:string` | observation |
| `chart:value` | `qb:MeasureProperty` | `xsd:decimal`, `xsd:double`, `xsd:float` or `xsd:integer`, finite | observation |
| `chart:unit` | `qb:AttributeProperty` | `xsd:string` | dataset |
| `chart:order` | annotation | `xsd:integer` | observation |

## Contract

- Exactly one `qb:DataSet`, with at least one `rdfs:label` (`xsd:string` or `rdf:langString`), any number of `rdfs:comment`, at most one `chart:unit`. `qb:structure` is optional and ignored.
- 0 to 10000 `qb:Observation` nodes, each with exactly one `qb:dataSet` pointing at a `qb:DataSet`. Zero observations conform and render the empty state.
- Each observation has exactly one of `chart:category` and `chart:date`. All observations use the same one; for dates, the same datatype.
- `chart:value`: exactly one, not NaN or infinite.
- `chart:series`: on every observation or on none, at most 8 distinct values.
- The pair (`chart:category` or `chart:date`, `chart:series`) is unique.
- Categories are ordered by `chart:order`, then lexically; dates chronologically.
- Other nodes are ignored.

Every constraint is a `sh:Violation`. The cross-observation rules are `sh:sparql` constraints on the dataset. The dataset-count rules target the fixed node `chart:Document`, so that a document without any dataset still gets a focus node; it is not a class and is never expected in data.

## Context

`v0.1.0/context.jsonld` is the JSON-LD context of the profile. It defines the prefixes `qb`, `chart`, `rdfs`, `xsd`, the short terms `DataSet`, `Observation`, `dataSet`, `label`, `comment`, `category`, `series`, `date`, `value`, `unit`, `order`, and `observations` as `@reverse` of `qb:dataSet`, so observations nest under their dataset. `tools/chart-shapes-test.sh` checks that it expands `tests/context/short-terms.jsonld` to the same graph as the long-form fixture.

Two URLs identify it:

- `https://eona-x.eu/shape/chart-profile/context.jsonld` is the stable URL and the identifier producers put in `@context`. The Vocabulary Hub serves the context of the latest version there (hub change, separate MR).
- `https://eona-x.eu/shape/chart-profile/v0.1.0.context.jsonld` is the versioned URL, a sibling of `v0.1.0.ttl` and `v0.1.0.jsonld`; use it to pin a version.

The toolkit never fetches either URL: it embeds the context and maps the stable URL to that built-in copy. Until the hub serves the stable URL, this repository does not publish it.

## Tests

`tests/conforming/*.jsonld` must conform; `tests/violating/*.jsonld` must not, and the report must contain the first line of the matching `.expect`. Fixtures carry an inline `@context` (pySHACL runs offline). `tools/chart-shapes-test.sh` runs them, and the `chart-profile-shapes` job of `verify.yml` runs that script. The 10000-observation limit has no fixture: a conforming-size document makes pySHACL evaluate the uniqueness rule in quadratic time.

## Legacy

The menu package of the toolkit still uses `https://eona-x.eu/ns/menu#`, which is off-convention; it is not covered by this asset.
