# schema-org-travel

Subset of schema.org v30.1 for travel: reservations, trips and programme memberships.
The Turtle in `v30.1/ontology.ttl` is generated, not edited by hand.

## Source

- Repository: <https://github.com/schemaorg/schemaorg>, tag `v30.1`, commit `5f2d8cdec99b7329459ef6584e94b6a840f88471`.
- File: `data/releases/30.1/schemaorg-current-https.ttl`, sha256 `7f15ca89398c4f235f478a4b3b8d1f975d63c5a860b77c8a8fce01f791b7ae2f`.
- The upstream file declares no `owl:Ontology`. The generator adds one, `<https://schema.org/>`, with `owl:versionInfo "30.1"`, `dcterms:source` and `dcterms:license`.

## Slice

1. Seed classes: `schema:Reservation` and `schema:Trip` with all their subclasses (transitive), plus `schema:ProgramMembership`. 18 classes.
2. Properties: every property with a `schema:domainIncludes` pointing at a seed class. 73 properties, kept with all their upstream triples (label, comment, `domainIncludes`, `rangeIncludes`, `supersededBy`, `inverseOf`, `isPartOf`, `source`, ...). 3 are superseded, 3 are pending (`schema:isPartOf <https://pending.schema.org>`; the fourth pending term is the seed class `schema:TouristTrip`), 4 carry `schema:inverseOf`.
3. Superclasses of the seeds (`schema:Intangible`, `schema:Thing`) and every class named as `rangeIncludes` or `domainIncludes` of a kept property, with their superclass chains: only `rdf:type`, `rdfs:label` and `rdfs:subClassOf`. Their comments and other properties are not copied, so they are not defined here, only named.
4. Members of the enumerations used as ranges (`?m a ?E`): type, label and comment. In v30.1 these are `ReservationCancelled`, `ReservationConfirmed`, `ReservationHold`, `ReservationPending`, `GroupBoardingPolicy`, `ZoneBoardingPolicy`.

The result has 79 classes (18 with a full description) and 73 properties.

## Licence

The data is schema.org's, licensed CC BY-SA 3.0 (<https://schema.org/docs/terms.html>). This asset keeps that licence with attribution to Schema.org and is not covered by the Apache-2.0 licence of the rest of this repository.

## http and https

schema.org terms occur in two schemes in this repository:

- `datatourisme/v3.2.2` and the `schema-org/` parent closure use `http://schema.org/`.
- `dpv/v2.x` and this asset use `https://schema.org/`.
- `metadata.ttl` files use `http://schema.org/` for `schema:logo`.

schema.org states that `http://schema.org/X` and `https://schema.org/X` denote the same term. Consumers compare terms after rewriting the scheme to `https`. No bridge triples (`owl:sameAs`, `owl:equivalentClass`) are emitted.

## Regenerate

```sh
pip install -r tools/generators/requirements.txt
tools/generators/regenerate.sh schema-org-travel          # rewrite
tools/generators/regenerate.sh --check schema-org-travel  # exit 1 on drift
```

The script downloads the pinned file into an empty temporary directory, verifies the sha256 and reads it only as data.
