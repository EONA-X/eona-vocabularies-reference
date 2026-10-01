# NeTEx ↔ DATEX II crosswalk (alignment graph) — #446

The EMDS-demo **passerelle** (demo point C): a hub-curated SKOS alignment between
the DATEX II EnergyInfrastructure EV-charging subset (#433,
[`../datex-ii/`](../datex-ii)) and the NeTEx/Transmodel-style EV-charging subset
(#445, [`../netex/`](../netex)). Given a term in one vocabulary, it resolves to
its counterpart in the other.

This loader runs **last** in the chain (mobility → DATEX II → NeTEx →
**crosswalk**). It only *references* the existing concept IRIs; it never
redefines the concepts (those live in the datex/netex graphs).

## Named graphs

| Graph IRI | Asset | Content |
| --- | --- | --- |
| `https://eona-x.eu/crosswalk/netex-datex/v0.1.0#` | `alignment.ttl` | the alignment graph (match triples + provenance) |

The alignment resource node `<https://eona-x.eu/crosswalk/netex-datex/v0.1.0#>`
is typed `dcat:Resource`, `void:Linkset`, `skos:Collection` and carries
graph-level provenance (`dcterms:title` "NeTEx ↔ DATEX II crosswalk
(EV-charging)", `dcterms:description`, `dcterms:created`, `dcterms:creator`,
`dcterms:source`, `rdfs:seeAlso` the two schemes).

## The 5 mappings

Each pair is asserted in **both directions** (SKOS match properties are
symmetric; the reverse triple is asserted explicitly so plain, non-inferencing
SPARQL resolves either way).

| DATEX II | predicate | NeTEx | rationale |
| --- | --- | --- | --- |
| `datex:ElectricVehicleChargingPoint` | `skos:closeMatch` | `netex:ElectricVehicleChargingEquipment` | point vs equipment |
| `datex:status` | `skos:closeMatch` | `netex:availabilityStatus` | availability status; value sets not asserted identical |
| `datex:power` | `skos:exactMatch` | `netex:powerRating` | same quantity & units (kW) |
| `datex:connectorType` | `skos:closeMatch` | `netex:connectorStandard` | "type" vs "standard" framing |
| `datex:location` | `skos:exactMatch` | `netex:location` | same geographic concept |

(`datex:` = `https://eona-x.eu/ontology/datex-ii/v0.3.0#`,
`netex:` = `https://eona-x.eu/ontology/netex/v0.2.0#`)

Per-mapping provenance is attached via **RDF reification**: one `rdf:Statement`
per pair (`align:map-charging-point`, `align:map-status`, `align:map-power`,
`align:map-connector`, `align:map-location`) with `rdf:subject/predicate/object`
+ `skos:note` (closeness rationale) + `dcterms:source` + `dcterms:created`.

## Example SPARQL — given a DATEX II term, return its NeTEx equivalent

Query the live Oxigraph endpoint (`http://oxigraph:7878/query` in-compose, or
`http://localhost:7878/query` from the host). Prez does not expose raw SPARQL.

```sparql
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX datex: <https://eona-x.eu/ontology/datex-ii/v0.3.0#>
PREFIX netex: <https://eona-x.eu/ontology/netex/v0.2.0#>

SELECT ?netexTerm WHERE {
  datex:power skos:exactMatch|skos:closeMatch ?netexTerm .
  FILTER(STRSTARTS(STR(?netexTerm), STR(netex:)))
}
# -> https://eona-x.eu/ontology/netex/v0.2.0#powerRating
```

Reverse direction (NeTEx term → DATEX II equivalent):

```sparql
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX datex: <https://eona-x.eu/ontology/datex-ii/v0.3.0#>
PREFIX netex: <https://eona-x.eu/ontology/netex/v0.2.0#>

SELECT ?datexTerm WHERE {
  netex:powerRating skos:exactMatch|skos:closeMatch ?datexTerm .
  FILTER(STRSTARTS(STR(?datexTerm), STR(datex:)))
}
# -> https://eona-x.eu/ontology/datex-ii/v0.3.0#power
```

Both directions resolve directly because the crosswalk asserts each match in
both directions (no SKOS inference required).

## Idempotency

Each asset is written with HTTP `PUT` on the Graph Store Protocol (atomic
replace of the target graph). The default-graph rebuild drops and re-inserts the
union of all named graphs. Re-running the container reloads identical content
without producing duplicate triples.
