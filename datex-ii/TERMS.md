# DATEX II — EnergyInfrastructure (EV-charging subset) terms

Hub-curated RDF subset of the DATEX II EnergyInfrastructure model, scoped to EV
charging (IRVE) for the EMDS demo. Published as a SKOS `ConceptScheme` so the
terms are browsable in Prez and alignable by the crosswalk (#446).

Downstream issues #445 / #446 MUST read this file to stay consistent with the
exact IRIs and labels below.

- Namespace prefix: `datex:`
- Namespace URI: `https://eona-x.eu/ontology/datex-ii/v0.3.0#`
- Ontology IRI: `https://eona-x.eu/ontology/datex-ii/v0.3.0#`
- Version: `0.1.0`

## ConceptScheme

| IRI | prefLabel / title |
| --- | --- |
| `https://eona-x.eu/ontology/datex-ii/v0.3.0#energy-infrastructure` | DATEX II — EnergyInfrastructure (EV-charging subset) |

## Concepts (skos:Concept, skos:inScheme energy-infrastructure)

| IRI | skos:prefLabel |
| --- | --- |
| `https://eona-x.eu/ontology/datex-ii/v0.3.0#ElectricVehicleChargingPoint` | Electric Vehicle Charging Point |
| `https://eona-x.eu/ontology/datex-ii/v0.3.0#status` | Charging point status |
| `https://eona-x.eu/ontology/datex-ii/v0.3.0#power` | Rated power (kW) |
| `https://eona-x.eu/ontology/datex-ii/v0.3.0#connectorType` | Connector type |
| `https://eona-x.eu/ontology/datex-ii/v0.3.0#location` | Location (latitude/longitude) |

`datex:ElectricVehicleChargingPoint` is the scheme's `skos:topConceptOf` /
`skos:hasTopConcept`.

## OWL enrichment (class diagram)

`datex-ii.ttl` was originally SKOS-only (no `owl:Class`, no `rdfs:subClassOf`),
which rendered an empty UML class diagram in the Ontology Browser
(`containers/prez-ui/theme/app/utils/uml.ts` builds classes only from
Class-typed sections and generalization edges only from `rdfs:subClassOf`).
It has since been enriched, additively, with genuine OWL typing on top of the
existing SKOS structure — every original triple, IRI, label and definition is
unchanged; only new triples (dual `a` typing, `rdfs:domain`, and a few `#`
comments) were added. The crosswalk (`load-crosswalk-netex-datex`) and the
live Prez catalog loader both still resolve by the exact same IRIs.

Rules actually applied:

- Every `dcterms:type "Entity"` concept (5 of them) also got `a owl:Class`
  (kept alongside `a skos:Concept`), e.g.
  `datex:ElectricVehicleChargingPoint a skos:Concept, owl:Class ;`.
- Every `dcterms:type "Attribute"` concept (20 of them) also got
  `a owl:DatatypeProperty` or `a owl:ObjectProperty`, plus an `rdfs:domain`
  pointing at the Entity it's `skos:broader` of:
  - **`owl:DatatypeProperty`** (14): attributes whose `rdfs:range` is an
    `xsd:*` datatype (e.g. `brand`, `power`, `maxPowerAtSocket`, …), *and*
    the six enumeration-valued attributes whose `rdfs:range` is the
    attribute's own IRI (`status`, `authenticationAndIdentificationMethods`,
    `connectorType`, `chargingMode`, `connectorFormat`, `energySourceType` —
    this file's existing "self-referential enumeration root" convention, see
    the header comment). These are kept as `DatatypeProperty` rather than
    `ObjectProperty` because their "Code value" leaves are left as plain
    `skos:Concept`, not `owl:NamedIndividual` (see below) — an
    `ObjectProperty` ranging over a non-individual, non-class resource would
    be misleading. DATEX II's own XSD models these as string enumerations
    (simpleType + enumeration facets) anyway, so this is also the more
    faithful native typing.
  - **`owl:ObjectProperty`** (6): `connector` and `electricEnergyMix`, whose
    `rdfs:range` already pointed at another modelled Entity concept
    (`datex:Connector`, `datex:ElectricEnergyMix`) — these become the class
    diagram's two association arrows out of
    `ElectricVehicleChargingPoint`. Plus `entrance`, `operatingHours`,
    `energyProvider` and `location`, which are DATEX II object references
    (to `Location`, `OperatingHours`/`OverallPeriod`, `Organisation`) whose
    target type isn't modelled in this hub-curated subset — kept as
    `ObjectProperty` for semantic honesty (they're not literals) but with no
    invented `rdfs:range`, so the diagram correctly renders them as plain
    attributes rather than dangling arrows. Each of these four judgement
    calls has a short `# OWL enrichment note:` comment directly above the
    concept in `datex-ii.ttl`.
- **`dcterms:type "Code value"` concepts (61 of them) were left untouched** —
  no OWL typing added. They stay plain `skos:Concept` leaves (enum literals,
  e.g. connector/charging-mode/energy-source codes), out of scope for the
  class diagram, and are not modelled as `owl:NamedIndividual`: the thing
  they're notionally individuals *of* (their parent Attribute concept) is
  itself typed as a property, not a class, so minting them as individuals
  of it would be a type pun with no real payoff. Their DATEX II native
  enumeration literal remains in `skos:notation`, unchanged.
- **No `rdfs:subClassOf` was added.** All 5 Entity concepts are siblings —
  each is a `skos:topConceptOf` the scheme directly, and none is
  `skos:broader`/`skos:narrower` of another Entity concept in the source
  data. There is no genuine Entity-to-Entity hierarchy to mirror, so the
  class diagram renders as a flat set of 5 classes (this matches the
  DATEX II EnergyInfrastructure model itself, which doesn't relate these
  entities by subtyping either).

Validated with pyoxigraph 0.5.3 (matching
`pipelines/publish-vocabulary-catalog/requirements.txt`): the enriched file parses
cleanly (783 triples), with `owl:Class` = 5, `owl:DatatypeProperty` = 14,
`owl:ObjectProperty` = 6, `skos:Concept` = 86 (unchanged), `rdfs:subClassOf`
= 0, and all 20 `rdfs:domain` triples resolve to one of the 5 `owl:Class`
IRIs above.

## Full native-scope expansion (2026-08-18)

The file above described a deliberately hand-picked SUBSET (5 Entities / 20
Attributes / 61 Code values) curated for an earlier demo. It has since been
expanded, additively, to the FULL native scope of the DATEX II v3.7
EnergyInfrastructure model — every class and attribute defined directly in
`DATEXII_3_EnergyInfrastructure.xsd` — not just the EV-charging (IRVE)
corner of it. **Every triple described above is untouched**; the expansion
lives entirely in a new block appended after the original file content (only
`dcterms:modified`/`owl:versionInfo` on the `owl:Ontology` header were bumped
in place — file-level version metadata, not a modelled concept).

### Source

Fetched live and read directly — the primary schema WAS reachable (unlike
the ebucore precedent in `pipelines/tools/resolve-external-parents.py`,
which had to fall back because its source was unreachable; no such fallback
was needed here):

- `https://docs.datex2.eu/_static/data/v3.7/DATEXII_3_EnergyInfrastructure.xsd`
  (the exact same DATEX II v3.7 EnergyInfrastructure namespace already cited
  by this file's ontology header)
- Cross-referenced `DATEXII_3_Facilities.xsd` and `DATEXII_3_Common.xsd`
  (also fetched from the same `/_static/data/v3.7/` path) to resolve
  inherited/external type names (`fac:Organisation`, `fac:Rates`,
  `fac:DurationValue`, `fac:AmountOfMoney`, `fac:_UserTypeEnum`,
  `fac:_ReservationTypeEnum`, `com:Seconds`, etc.) cited in scope notes.
- Narrative context/definitions cross-checked against the DATEX II
  Documentation Portal's Mastering-level "Energy" pages
  (`docs.datex2.eu/levels/mastering/energy/`).

### Scope rule

Every complexType defined directly in `DATEXII_3_EnergyInfrastructure.xsd`
is modelled, EXCEPT:

- the 4 exchange-message *envelope* complexTypes (`EnergyInfrastructureTable`,
  `EnergyInfrastructureTablePublication`,
  `EnergyInfrastructureStatusPublication`, and the
  `_EnergyInfrastructureTableVersionedReference` helper) — transport
  wrappers, not domain concepts, matching this file's pre-existing choice
  not to model `com:PayloadPublication`/`HeaderInformation` either;
- the "`_XyzEnum`" extensibility wrapper complexTypes (one per enum, an
  `_extendedValue` open-enumeration escape hatch) — not real classes;
- the `_extended` enumeration literal on every native enum — matches the
  pre-existing choice to omit it from the original 6 enumerations;
- the AFIR-branded sibling namespace (`AfirEnergyInfrastructure`,
  `DATEXII_3_AfirEnergyInfrastructure.xsd`) — confirmed (via
  `docs.datex2.eu/downloads/modelv37/`) to be a SEPARATE DATEX II
  extension/namespace, not part of "the EnergyInfrastructure model" this
  file scopes to;
- attributes/types living in the imported Facilities/Common/
  LocationReferencing namespaces (`fac:`/`com:`/`loc:`) — kept out of scope
  exactly like the pre-existing `entrance`/`operatingHours`/`energyProvider`/
  `location` precedent: `owl:ObjectProperty` or `owl:DatatypeProperty` with
  NO invented `rdfs:range`/code values, plus a "(external, out of scope)"
  scopeNote and, where the pattern needed re-explaining, a
  `# OWL enrichment note:` comment.

This pulled in a genuine `RefillPoint` (abstract) → `ElectricVehicleChargingPoint`
/ `DieselRefillPoint` / `PetrolRefillPoint` / `OrganicGasRefillPoint` /
`HydrogenRefillPoint` generalisation — DATEX II's EnergyInfrastructure model
covers refuelling in general, not just electric charging, and all five
specialisations live in the same XSD file/extension as the original 5
entities. `rdfs:subClassOf` is used for the first time in this file for
these 6 edges (one of them — `ElectricVehicleChargingPoint rdfs:subClassOf
RefillPoint` — is a NEW triple added to the pre-existing entity, per the
"add a missing attribute/edge, never touch an existing triple" rule).

### Attribute-naming collisions

DATEX II XSD element names are locally scoped per complexType, so several
native names recur across more than one class in this extension (e.g.
`energyProvider` on both `EnergyInfrastructureStation` and
`ElectricEnergyMix`; `serviceType` on `EnergyInfrastructureStation`,
`RefillPoint`, AND as `ServiceType`'s own scalar field; `status` on the
pre-existing hub-curated `ElectricVehicleChargingPoint.status` AND natively
again on the new `RefillPointStatus` class). Since this file's convention is
one bare-name IRI per attribute with a single `rdfs:domain`, a second/third
use of the same native name is disambiguated with a short, readable suffix,
documented per-attribute with a `# Naming note:` comment, e.g.:

| Native name | First/bare-name usage | Disambiguated as |
| --- | --- | --- |
| `energyProvider` | `datex:energyProvider` (EnergyInfrastructureStation, pre-existing) | `datex:energyMixProvider` (ElectricEnergyMix) |
| `serviceType` | `datex:serviceType` (RefillPoint) | `datex:stationServiceType` (EnergyInfrastructureStation), `datex:serviceTypeCode` (ServiceType's own enum field) |
| `status` | `datex:status` (ElectricVehicleChargingPoint, pre-existing, hub-curated OCPI-style simplification, untouched) | `datex:refillPointStatusCode` (RefillPointStatus, faithful native `RefillPointStatusEnum`, 13 values) |
| `refillPointStatus` | `datex:refillPointStatus` (EnergyInfrastructureStationStatus — only one usage, no collision) | — |

One reuse rather than rename: `ElectricEnergySourceRatio.energySource`
reuses the pre-existing `datex:energySourceType` enumeration ROOT as its
`rdfs:range` (kept `owl:DatatypeProperty`, per this file's existing rule for
enumeration-valued attributes) instead of duplicating its 10 code values
under a new IRI.

### Also filled in on the ORIGINAL enumerations (still additive)

Two of the original 6 enumerations were themselves incomplete relative to
the native XSD; the missing literals are added as new `skos:narrower` code
values on the pre-existing attribute concept (a new statement — the
original `skos:narrower` list is untouched):

- `authenticationAndIdentificationMethods`: native `AuthenticationAndIdentificationEnum`
  has 19 literals, the original subset had 10 — the missing 9
  (`activeRFIDChip`, `calypso`, `mifareClassic`, `mifareDesfire`, `overTheAir`,
  `phoneDialog`, `phoneSMS`, `pinpad`, `plc`) are added.
- `connectorType`: native `ConnectorTypeEnum` also defines 15 regional
  domestic-socket variants (`domesticA`–`domesticO`); the original subset's
  `connectorType-domestic` code value's definition text explicitly said
  these were "omitted here for brevity" (that pre-existing text is left
  untouched) — all 15 are now added as their own code values.

### Before/after counts

| dcterms:type | Before | After |
| --- | --- | --- |
| Entity (`owl:Class`) | 5 | 20 |
| Attribute (`owl:DatatypeProperty` + `owl:ObjectProperty`) | 20 | 89 |
| Code value | 61 | 171 |
| **Total skos:Concept** | **86** | **280** |

`owl:DatatypeProperty` = 65, `owl:ObjectProperty` = 24 (65+24 = 89, matches
Attribute count). `rdfs:subClassOf` = 6 (was 0). All 89 `rdfs:domain`
triples resolve to one of the 20 `owl:Class` IRIs; all in-namespace
`rdfs:range` triples resolve to an in-file `skos:Concept`. Validated with
pyoxigraph 0.5.3: the expanded file parses cleanly (2622 triples). Diffed
against `git show HEAD~1:pipelines/load-datex-ii/datex-ii.ttl` (the version
before this expansion): only two original lines change
(`dcterms:modified`/`owl:versionInfo` on the ontology header, bumped from
`2026-06-26`/`0.2.0` to `2026-08-18`/`0.3.0`) and every other original line
(1–44, 47–941) is byte-identical; everything else is pure insertion after
line 941.

### Deliberately left out

Same 4 envelope classes + `_XyzEnum` wrappers + `_extended` literals +
AFIR namespace listed under "Scope rule" above, plus (as before) the
Facilities/Common/LocationReferencing external types kept as bare
`ObjectProperty`/`DatatypeProperty` with no invented range.
