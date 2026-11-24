# osdm

RDF/OWL rendering of the UIC OSDM (Open Sales and Distribution Model) v3.11. `v3.11/ontology.ttl` is generated from the upstream JSON Schema and OpenAPI files, not edited by hand. Namespace: `https://vocabulary.eona-x.eu/ontology/osdm/v3.11#` (prefix `osdm`).

## Source

- Repository: <https://github.com/UnionInternationalCheminsdeFer/OSDM>, tag `v3.11` (2026-10-19), commit `d198a80259b9399754cec68cd60278892fe04cfe`. Licence: Apache-2.0.
- Files (sha256 pins in `tools/generators/sources.json`), all under `specification/`:
  - `OSDM-offline-model.json`: JSON Schema 2020-12, 84 `definitions`. Entry point: `FareDeliveryDef` (the root wrapper `fareDelivery` is not minted).
  - `OSDM-online-api.yml`: 495 `components.schemas`, each a `$ref` into `schemas/*.yml`. The `$ref` closure covers the 502 definitions of `schemas/*.yml` and `schemas/ojp/*.yml`.
- Excluded inputs: `OSDM-online-webhook.yml`, `paths/`, `components/` (parameters, responses, security schemes).
- Version caveat: at this tag, `info.version` in the online API reads `3.9.0` and the offline `$id` reads `.../eticket/v3.6/offlineOSDM.json`. The asset is named after the tag, 3.11.

## IRI forms

| Term | IRI |
|---|---|
| Class, enumeration scheme, named datatype | `osdm:<Name>` |
| Property `p` of class `C` | `osdm:<C>.<p>` (written as a full IRI in the Turtle) |
| Enumeration value | `osdm:<Scheme>/<value>`, `value` percent-encoded (`application/pdf` becomes `application%2Fpdf`) |
| Inline enumeration or object on property `C.p` | `osdm:<C><P>` (`P` = `p` with an upper-case first letter), e.g. `osdm:RelativeTimeDefTimeUnit` |
| Offline definition that is structurally different from the online one of the same name | `osdm:Offline<Name>`, with `rdfs:seeAlso osdm:<Name>` |
| Offline and online definitions of the same name that differ only in annotations | one term `osdm:<Name>`, annotations of both kept |

A property is scoped to its class: the same upstream property name with different ranges on different classes gives different properties (128 names have more than one range).

## Mapping

| OSDM schema | RDF |
|---|---|
| Object, type-less object, or `allOf` definition | `owl:Class` with `rdfs:label`, `rdfs:comment` (description), `rdfs:isDefinedBy`, `dcterms:source` (file on GitHub at the commit) |
| `allOf: [$ref X, inline]` | `rdfs:subClassOf osdm:X`; the inline member's properties belong to the class |
| `discriminator` | no mapping beyond `allOf`; `skos:scopeNote` names the discriminator property |
| Property with a primitive type | `owl:DatatypeProperty`, `rdfs:range` from the format table below |
| Property with `$ref` to a class or enumeration | `owl:ObjectProperty` |
| Property with `$ref` to a named primitive | `owl:DatatypeProperty` ranging over the named datatype |
| `type: array` | same as its items, never an `owl:FunctionalProperty`; a named array definition is unwrapped to its items and not minted |
| Named primitive definition | `rdfs:Datatype` with `owl:equivalentClass [ a rdfs:Datatype ; owl:onDatatype xsd:... ]` |
| `enum`, `x-extensible-enum` | `owl:Class` + `skos:ConceptScheme`; each value a `skos:Concept` typed with the scheme, with `skos:inScheme`, `skos:notation`, `skos:prefLabel` and, for `{VALUE: text}` items, `skos:definition`; an extensible list also has a `skos:scopeNote` |
| `required` | `rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ... ; owl:minCardinality 1 ]` |
| `example` | `skos:example` (JSON text when not a string) |
| `deprecated: true` | `owl:deprecated "true"^^xsd:boolean` on the property, class, enumeration scheme or datatype that carries it; an inline enumeration or object of a deprecated property is marked too. The flag is read on the definition body, on an inline `allOf` member, on the property schema and its array items, and on a named array definition (carried to the properties that reference it). `deprecated: false` leaves no trace |
| property listed in `required` and not an array | also `owl:FunctionalProperty` |

`owl:FunctionalProperty` only for a property that is required by the class that defines it and is not an array. A subclass that requires an inherited property does not make it functional. Optional properties are not functional.

Format table: string `xsd:string`; `date-time` `xsd:dateTime`; `date` `xsd:date`; `duration` `xsd:duration`; `uri`, `url` `xsd:anyURI`; `byte` `xsd:base64Binary`; integer `xsd:integer`; `int32` `xsd:int`; `int64` `xsd:long`; number `xsd:decimal`; `float` `xsd:float`; `double` `xsd:double`; boolean `xsd:boolean`. An unknown format fails the build.

Not supported, and the build fails if upstream starts using them: `oneOf`, `anyOf`, `not`, `patternProperties`, `additionalProperties` with a schema, `type` lists, unresolved `$ref`, unknown keywords.

Dropped without trace: `nullable`, `default`, `pattern`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `minLength`, `maxLength`, `minItems`, `maxItems`, `minitems`, `maxitems`, `uniqueItems`, `minProperties`, `maxProperties`, `readOnly`, `writeOnly`, `contentEncoding`, `examples`, `title`, `additionalProperties: false`, and `x-` extensions other than `x-extensible-enum`.

## Offline and online collisions

Ten names are defined in both the offline model and the online API. For each, the generator maps both definitions and compares the triples left after removing the annotation properties (`rdfs:label`, `rdfs:comment`, `rdfs:isDefinedBy`, `dcterms:source`, `skos:example`, `skos:definition`, `skos:prefLabel`).

- Same structure: one term with the bare name `osdm:<Name>`. Both comments, both examples (class and property level) and both `dcterms:source` values are kept, as separate triples. Structure covers superclasses, properties and their ranges, enumeration values, required cardinalities, functional and deprecated flags, and scope notes.
- Different structure: the online definition keeps `osdm:<Name>`, the offline one becomes `osdm:Offline<Name>` with `rdfs:seeAlso osdm:<Name>`. Offline properties that reference a renamed definition point to the `Offline` term. The build fails if `Offline<Name>` already exists.

Merged in v3.11 (4), they differ only in description text: ProductType, TripAllocationProcess, TripAllocationUnit, TripInterruptionProcess.

Renamed in v3.11 (6):

| Name | Structural difference |
|---|---|
| ConditionType | the online enumeration has an extra value (`PRE_SALE`) |
| FulfillmentOption | different properties (offline `fulfillmentType`, online `type` and `specification`) |
| LuggageConstraint | different properties (offline `id`, `luggageRules`; online `restrictionRules`) |
| LuggageDimension | `dimension` and `value` have other ranges |
| LuggageRestriction | different properties (offline `restrictions`; online `dimensionRestrictions`, `registrationIds`) |
| Product | different properties and `_links` only online |

## Not provided

- No `context.jsonld`.
- No SHACL shapes. `required` is expressed as OWL cardinality restrictions only.

## Regenerate

```sh
pip install -r tools/generators/requirements.txt
tools/generators/regenerate.sh osdm          # rewrite
tools/generators/regenerate.sh --check osdm  # exit 1 on drift
```

The script downloads the pinned files into an empty temporary directory, verifies their sha256 and reads them only as data.

## Licence

Source data: Apache-2.0 (UIC OSDM, LICENSE at commit d198a80). This asset is under the Apache-2.0 licence of this repository.
