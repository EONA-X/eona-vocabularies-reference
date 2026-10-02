# NeTEx/Transmodel — EV charging & alternative-fuel (subset) terms

Hub-curated SKOS rendering of the NeTEx (CEN/TS 16614, Transmodel-based) vehicle
charging / alternative-fuel / recharging subset, scoped for the EMDS demo. NeTEx
proper is published natively as XSD and is PT-scoped, but it *does* carry a real
(adjacent) model for charging and alternative fuel — the entities, attributes and
enumerations below use the verbatim NeTEx v2.0 names. The SKOS framing
(Entity / Attribute / Code value) is the hub's rendering, not a NeTEx-native
artefact. Published as a SKOS `ConceptScheme` so the terms are browsable in Prez
and alignable by the crosswalk (#446).

The crosswalk issue #446 MUST read this file to align these IRIs directly against
the DATEX II counterparts (see `pipelines/load-datex-ii/TERMS.md`).

- Namespace prefix: `netex:`
- Namespace URI: `https://vocabulary.eona-x.eu/ontology/netex/v0.2.0#`
- Ontology IRI: `https://vocabulary.eona-x.eu/ontology/netex/v0.2.0#`
- Version: `0.2.0`

## Sources (NeTEx v2.0, github.com/TransmodelEcosystem/NeTEx, branch v2.0)

- `xsd/netex_framework/netex_reusableComponents/netex_nm_equipmentEnergy_version.xsd` — `VehicleChargingEquipment`, `RefuellingEquipment`, `BatteryEquipment`, `TypeOfPlug`, `TypeOfBatteryChemistry`
- `xsd/netex_framework/netex_reusableComponents/netex_nm_equipmentEnergy_support.xsd` — `PlugTypeEnumeration`, `CurrentTypeEnumeration`, `PowerCouplingTypeEnumeration`, `FuelTypeEnumeration`
- `xsd/netex_framework/netex_reusableComponents/netex_nm_chargingEquipmentProfile_version.xsd` — `RechargingEquipmentProfile`
- `xsd/netex_part_1/part1_ifopt/netex_rechargingPointAssignment_version.xsd` — `RechargingStation`, `RechargingBay`, `RechargingPointAssignment`
- `xsd/netex_framework/netex_utility/netex_units.xsd` — `WattageType` / `VoltageType` / `WattHoursType` (all `xsd:decimal`, SI W / V / Wh)
- Standard docs: https://netex-cen.eu/ , http://www.transmodel-cen.eu/

## ConceptScheme

| IRI | prefLabel / title |
| --- | --- |
| `https://vocabulary.eona-x.eu/ontology/netex/v0.2.0#ev-charging` | NeTEx/Transmodel — EV charging & alternative-fuel (subset) |

## Entities (skos:Concept, dcterms:type "Entity", skos:topConceptOf)

| NeTEx IRI | NeTEx element | prefLabel |
| --- | --- | --- |
| `netex:ElectricVehicleChargingEquipment` | VehicleChargingEquipment | Electric Vehicle Charging Equipment |
| `netex:RefuellingEquipment` | RefuellingEquipment | Refuelling Equipment |
| `netex:BatteryEquipment` | BatteryEquipment | Battery Equipment |
| `netex:RechargingStation` | RechargingStation | Recharging Station |
| `netex:RechargingPointAssignment` | RechargingPointAssignment | Recharging Point Assignment |
| `netex:RechargingEquipmentProfile` | RechargingEquipmentProfile | Recharging Equipment Profile |

## Attributes (skos:Concept, dcterms:type "Attribute", skos:broader <entity>)

Value type carried via `skos:scopeNote "Value type: ..."` + `rdfs:range`
(an xsd datatype, or — for enumeration-valued attributes — the attribute's own
concept which roots the code values).

| Attribute IRI | Entity | Value type |
| --- | --- | --- |
| `netex:availabilityStatus` | ElectricVehicleChargingEquipment | enumeration (hub-curated; 5 codes) |
| `netex:powerRating` | ElectricVehicleChargingEquipment | xsd:decimal (kW; NeTEx MaximumPower is W) |
| `netex:connectorStandard` | ElectricVehicleChargingEquipment | enumeration PlugTypeEnumeration (16 codes) |
| `netex:location` | ElectricVehicleChargingEquipment | structured (Transmodel Point/Location) |
| `netex:freeRecharging` | ElectricVehicleChargingEquipment | xsd:boolean |
| `netex:reservationRequired` | ElectricVehicleChargingEquipment | xsd:boolean |
| `netex:reservationUrl` | ElectricVehicleChargingEquipment | xsd:anyURI |
| `netex:gridVoltage` | ElectricVehicleChargingEquipment | xsd:decimal (V) |
| `netex:currentType` | ElectricVehicleChargingEquipment | enumeration CurrentTypeEnumeration (4 codes) |
| `netex:powerCouplingType` | ElectricVehicleChargingEquipment | enumeration PowerCouplingTypeEnumeration (6 codes) |
| `netex:fuelType` | RefuellingEquipment | enumeration FuelTypeEnumeration (18 codes) |
| `netex:batteryCapacity` | BatteryEquipment | xsd:decimal (Wh) |
| `netex:batteryUsableCapacity` | BatteryEquipment | xsd:decimal (Wh) |
| `netex:nominalVoltage` | BatteryEquipment | xsd:decimal (V) |
| `netex:maximumChargingPower` | BatteryEquipment | xsd:decimal (W) |
| `netex:typeOfBatteryChemistry` | BatteryEquipment | classification reference |
| `netex:totalPower` | RechargingStation | xsd:decimal (W) |
| `netex:servedScheduledStopPoints` | RechargingPointAssignment | reference list (ScheduledStopPoint) |
| `netex:chargingVoltage` | RechargingEquipmentProfile | xsd:decimal (V) |
| `netex:profileMaximumChargingPower` | RechargingEquipmentProfile | xsd:decimal (W) |
| `netex:preparationDuration` | RechargingEquipmentProfile | xsd:duration |
| `netex:finalisationDuration` | RechargingEquipmentProfile | xsd:duration |
| `netex:profilePlugType` | RechargingEquipmentProfile | enumeration PlugTypeEnumeration (range → connectorStandard) |
| `netex:profileCurrentType` | RechargingEquipmentProfile | enumeration CurrentTypeEnumeration (range → currentType) |
| `netex:profilePowerCouplingType` | RechargingEquipmentProfile | enumeration PowerCouplingTypeEnumeration (range → powerCouplingType) |

## Code values (skos:Concept, dcterms:type "Code value", skos:broader <attribute>)

Each carries `skos:notation` with the verbatim NeTEx enumeration token.

- `connectorStandard` (PlugTypeEnumeration): undefined, type1, type2, type3, typeE, typeF, typeG, typeJ, combinedChargingSystem, ccsCombo1Plug, ccsCombo2Plug, tesla, nema5-20, avcon, CHAdeMO, shockproof
- `currentType` (CurrentTypeEnumeration): undefined, 1-PhaseAC, 3-PhaseAC, DC
- `powerCouplingType` (PowerCouplingTypeEnumeration): undefined, plug, pantographAbove, pantograph, induction, other
- `fuelType` (FuelTypeEnumeration): battery, biodiesel, diesel, dieselBatteryHybrid, electricContact, electricity, ethanol, hydrogen, liquidGas, tpg, methane, naturalGas, petrol, petrolBatteryHybrid, petrolLeaded, petrolUnleaded, none, other
- `availabilityStatus` (hub-curated; NeTEx static schema has no equipment availability — real-time status is a SIRI concern): available, occupied, reserved, outOfService, unknown

## Crosswalk mappings (#446) — DATEX II counterparts

The 5 preserved IRIs below are referenced verbatim by the crosswalk and MUST NOT
be renamed. The newly added entities/attributes/codes are not yet mapped (the
DATEX II subset only carries the 5 counterparts).

| NeTEx IRI | DATEX II counterpart |
| --- | --- |
| `netex:ElectricVehicleChargingEquipment` | `datex:ElectricVehicleChargingPoint` |
| `netex:availabilityStatus` | `datex:status` |
| `netex:powerRating` | `datex:power` |
| `netex:connectorStandard` | `datex:connectorType` |
| `netex:location` | `datex:location` |

`netex:ElectricVehicleChargingEquipment` and the other 5 entities are the
scheme's `skos:topConceptOf` / `skos:hasTopConcept`.

## OWL enrichment (class-diagram publishing)

`netex.ttl` was originally SKOS-only (no `owl:Class`, no `rdfs:subClassOf`),
so it would have rendered an empty UML class diagram in the Ontology
Browser (`buildUmlDiagram` in `containers/prez-ui/theme/app/utils/uml.ts`
only draws boxes for `owl:Class`/`rdfs:Class`-typed terms, and
generalisation edges only from `rdfs:subClassOf`). The following rules were
applied, purely additively — every pre-existing triple, IRI, label and
definition is unchanged; only new `rdf:type` values and `rdfs:domain`
triples were added:

- **Entities** (`dcterms:type "Entity"`, the 6 `skos:topConceptOf` concepts)
  additionally get `a owl:Class`, kept alongside `a skos:Concept` (the same
  dual-typing pattern already used by ODRL's vocabulary in this hub). The
  frontend's `primaryKind()` checks `owl:Class`/`rdfs:Class` before any SKOS
  or property type, so dual-typing resolves unambiguously to a UML class box.
- **Attributes** (`dcterms:type "Attribute"`, `skos:broader` an Entity)
  additionally get `a owl:DatatypeProperty` (kept alongside `a skos:Concept`)
  plus `rdfs:domain <the Entity it is skos:broader of>`. **All 25 attributes
  ended up `owl:DatatypeProperty`, none `owl:ObjectProperty`**: an
  `ObjectProperty` would only be justified if an attribute's value were
  clearly one of the 6 Entity-classes above, and none are — every
  attribute's value is either a literal (`xsd:decimal`/`xsd:boolean`/
  `xsd:anyURI`/`xsd:duration`), a hub-curated or NeTEx enumeration (whose
  code values are leaf SKOS concepts, not classes — see below), or a
  reference to a NeTEx concept that isn't modelled as an Entity in this
  subset. Three attributes are judgement calls worth flagging explicitly,
  because their value is structurally a reference rather than a plain
  literal, yet nothing in this subset gives that reference's target its own
  Entity/`owl:Class`:
  - `netex:location` — a Transmodel POINT/LOCATION (WGS84 lat/lon); no
    `netex:Location` Entity exists in this subset.
  - `netex:typeOfBatteryChemistry` — a NeTEx `TypeOfBatteryChemistry`
    classification reference; not rendered as an Entity here.
  - `netex:servedScheduledStopPoints` — a reference list of NeTEx
    `ScheduledStopPoint`; out of scope for this EV-charging subset.

  All three were kept `owl:DatatypeProperty` (the documented default) rather
  than inventing an unmodelled `owl:Class` for their target just to justify
  an `ObjectProperty` — that would go beyond "genuine" typing into fabricated
  structure not actually present in the curated data.
- **Code values** (`dcterms:type "Code value"`, `skos:broader` an Attribute
  — enum members like plug/current/fuel codes) were **left as plain
  `skos:Concept`, untouched**. Reasoning: the "enumeration type" each code
  value belongs to (e.g. `netex:connectorStandard`) is itself now typed
  `owl:DatatypeProperty`, not `owl:Class` — properties don't have
  `owl:NamedIndividual` members in OWL, so typing the code values as
  individuals of their attribute would be incoherent. Minting a *new*,
  separate `owl:Class` per enumeration (e.g. a `netex:ConnectorStandardCode`
  class) purely to hang `owl:NamedIndividual`s off of was judged out of
  scope: it isn't a "genuine" class present in the NeTEx source model, and
  the class diagram doesn't need it — code values are leaf enum values, not
  structural classes, and are already fully browsable as SKOS concepts via
  `skos:broader`/`skos:notation`.
- **`rdfs:subClassOf`**: none were added. All 6 Entities are `skos:broader`
  of nothing (they are the scheme's top concepts with no Entity-to-Entity
  `skos:broader`/`narrower` edges between them in the source data), so the
  class diagram is a correct, honest flat set of 6 unrelated classes rather
  than an invented hierarchy.

Validated with `pyoxigraph==0.5.3` (matching
`pipelines/publish-vocabulary-catalog/requirements.txt`'s pin): the file parses
cleanly; `owl:Class` = 6 (all still also `skos:Concept`); `owl:DatatypeProperty`
= 25 (all still also `skos:Concept`, all with `rdfs:domain` resolving to one
of the 6 in-file classes); `owl:ObjectProperty` = 0; `rdfs:subClassOf` = 0;
`dcterms:type` counts unchanged (Entity 6 / Attribute 25 / Code value 49).

## 2026-08-18 full-scope expansion

The hand-curated subset above (6 Entities / 25 Attributes / 49 Code values)
was extended, additively, to cover the FULL native scope of the same 5 NeTEx
v2.0 XSD modules already cited above (re-fetched in full from
`github.com/TransmodelEcosystem/NeTEx`, branch `v2.0`):
`netex_nm_equipmentEnergy_version.xsd`, `netex_nm_equipmentEnergy_support.xsd`,
`netex_nm_chargingEquipmentProfile_version.xsd`,
`netex_rechargingPointAssignment_version.xsd`, `netex_units.xsd`.

Every original triple, IRI, label and definition in `netex.ttl` is unchanged
— `git diff --stat` for this pass is 213 insertions / **0 deletions**. New
material was appended as new blocks (new Entities before the `ATTRIBUTES`
header, new Attributes before the `CODE VALUES` header, a new
`CROSS-LINKS` section at the end of the file for the new
`skos:narrower`/`skos:hasTopConcept` edges *from* pre-existing subjects,
written as standalone triples rather than edits to the original comma-lists).
The ontology header (`dcterms:modified`, `owl:versionInfo "0.2.0"`, the
"subset" wording in the title/description) was deliberately left untouched
for the same reason, matching how the prior OWL-enrichment pass (2026-08-17)
also left it alone — a version/date bump is a reasonable follow-up but wasn't
made here to keep the preservation guarantee unambiguous; worth doing by hand
if the hub wants the header to reflect the now-full scope.

### New Entities (3): `owl:Class` 6 → 9

- `netex:TypeOfPlug` — NeTEx element `TypeOfPlug` (substitutionGroup
  `TypeOfEntity`, complexType `TypeOfPlug_ValueStructure`,
  `netex_nm_equipmentEnergy_version.xsd`). An extensible classification for
  plugs, alongside the closed `PlugTypeEnumeration`.
- `netex:TypeOfBatteryChemistry` — NeTEx element `TypeOfBatteryChemistry`
  (same file/pattern). An extensible classification for battery chemistry.
- `netex:RechargingBay` — NeTEx element `RechargingBay` (substitutionGroup
  `ParkingBay_Dummy`, complexType `RechargingBay_VersionStructure`,
  `netex_rechargingPointAssignment_version.xsd`). Its own
  `RechargingBayGroup` is an **empty** `xsd:sequence` in these 5 files (all
  behaviour is inherited from the out-of-scope `ParkingBay_VersionStructure`
  base type) — included anyway for completeness since it is a genuine
  complexType in-file, even though it carries zero Attribute children here.

### New Attributes (8): `owl:DatatypeProperty` 25 → 30, `owl:ObjectProperty` 0 → 3

| Attribute IRI | Entity | Value type | Source element |
| --- | --- | --- | --- |
| `netex:typeOfPlug` | ElectricVehicleChargingEquipment | ObjectProperty → `netex:TypeOfPlug` | `TypeOfPlugRef`, `VehicleChargingEquipmentGroup` |
| `netex:profileTypeOfPlug` | RechargingEquipmentProfile | ObjectProperty → `netex:TypeOfPlug` | `TypeOfPlugRef`, `RechargingEquipmentProfileGroup` |
| `netex:vehicleChargingEquipment` | RechargingPointAssignment | ObjectProperty → `netex:ElectricVehicleChargingEquipment` | `VehicleChargingEquipmentRef`, `RechargingPointAssignmentGroup` |
| `netex:compatibleWith` | RechargingEquipmentProfile | reference list (choice of Vehicle­ChargingEquipmentRef \| RefuellingEquipmentRef \| BatteryEquipmentRef) | `compatibleWith`, type `compatibleEquipmentRefs_RelStructure` |
| `netex:siteComponent` | RechargingPointAssignment | reference (SiteComponent out of scope) | `SiteComponentRef` |
| `netex:equipmentPlace` | RechargingPointAssignment | reference (EquipmentPlace out of scope) | `EquipmentPlaceRef` |
| `netex:plugNameOfClassifiedEntityClass` | TypeOfPlug | xsd:string (NeTEx `NameOfClass`) | `nameOfClassifiedEntityClass` |
| `netex:batteryChemistryNameOfClassifiedEntityClass` | TypeOfBatteryChemistry | xsd:string (NeTEx `NameOfClass`) | `nameOfClassifiedEntityClass` |

`typeOfPlug`, `profileTypeOfPlug` and `vehicleChargingEquipment` are this
file's first `owl:ObjectProperty`s: unlike every attribute in the original
subset, their value is unambiguously a single reference to one of the
in-file Entity classes, so (unlike the judgement calls already recorded above
for `location`/`typeOfBatteryChemistry`/`servedScheduledStopPoints`) an
`ObjectProperty` is the honest typing here.

The **pre-existing** `netex:typeOfBatteryChemistry` attribute (documented
above as a deliberate `owl:DatatypeProperty` judgement call from the prior
pass, made when no `TypeOfBatteryChemistry` Entity existed) was **left
completely untouched** — it does not get a new `rdfs:range
netex:TypeOfBatteryChemistry` triple, even though that Entity now exists.
This keeps "never touch existing triples" unambiguous; reconciling it (either
by adding `rdfs:range` or by retyping to `owl:ObjectProperty`, which *would*
require removing the existing `owl:DatatypeProperty` triple) is flagged as a
follow-up, not done here.

### No new Code values (`Code value` count unchanged at 49)

All 4 native XSD enumerations were re-verified value-for-value against the
re-fetched XSDs and were already complete:

- `PlugTypeEnumeration` — 16/16 values already present under `connectorStandard`.
- `CurrentTypeEnumeration` — 4/4 values already present under `currentType`.
- `PowerCouplingTypeEnumeration` — 6/6 values already present under `powerCouplingType` (including the deprecated `pantographAbove`, which the XSD still defines).
- `FuelTypeEnumeration` — 18/18 values already present under `fuelType`.

`units.xsd`'s one real enumeration, `SystemOfUnits` (`SiMetres`,
`SiKilometresAndMetres`, `Other`), is **not** referenced by any element in
the other 4 scoped files (it's a general NeTEx frame-level unit-system
declaration) — left unmodelled to avoid manufacturing an unused code list.
`units.xsd`'s other simpleTypes (`WattageType`, `VoltageType`,
`WattHoursType`, `LengthType`, `DistanceType`, `WeightType`, `SpeedType`,
`CurrencyAmountType`, `NumberOfVehicles`, `NumberOfPassengers`,
`PassengersPerMinute`) are plain `xsd:decimal`/`xsd:nonNegativeInteger`
restrictions with no complexType and no enumeration — the 3 actually used
within scope (`WattageType`/`VoltageType`/`WattHoursType`) were already fully
captured via `rdfs:range xsd:decimal` + `skos:editorialNote` on the
attributes that use them; `units.xsd` contributes zero new concepts.

### complexTypes deliberately NOT modelled as Entities

The 9 NeTEx `*_RefStructure` / `*_RelStructure` complexTypes present in
these 5 files are XML by-reference-linking / list-container scaffolding, not
domain entities, and were excluded — consistent with how the original subset
already treats reference targets (e.g. `servedScheduledStopPoints` is a
"reference list", not a modelled class):

- `VehicleChargingEquipmentRefStructure`, `RefuellingEquipmentRefStructure`,
  `BatteryEquipmentRefStructure`, `TypeOfBatteryChemistryRefStructure`,
  `TypeOfPlugRefStructure` (`netex_nm_equipmentEnergy_support.xsd`) — each is
  just a `ref` attribute plus versioning/modification metadata, the standard
  NeTEx idiom for a by-ID reference.
- `compatibleEquipmentRefs_RelStructure`
  (`netex_nm_equipmentEnergy_support.xsd`) — a list container for the
  `compatibleWith` choice; the choice itself is represented via
  `netex:compatibleWith`'s `skos:scopeNote`.
- `rechargingPointAssignments_RelStructure`, `rechargingStations_RelStructure`,
  `rechargingBays_RelStructure` (`netex_rechargingPointAssignment_version.xsd`)
  — frame-level list wrappers for `RechargingPointAssignment`/
  `RechargingStation`/`RechargingBay`. No element in these 5 files actually
  exposes one of these list types as an attribute of a modelled Entity (e.g.
  no in-scope "bays" element on `RechargingStation` — that relationship is
  declared in the out-of-scope `ParkingGroup`/`Parking_VersionStructure`
  base), so no corresponding attribute triple was added either.

### Validation (2026-08-18 pass)

Same `pyoxigraph==0.5.3` validation as the prior pass, re-run after the
expansion:

- File parses cleanly (874 triples total).
- `owl:Class` = 9, `owl:DatatypeProperty` = 30, `owl:ObjectProperty` = 3,
  `skos:Concept` = 91.
- `dcterms:type` counts: Entity 9, Attribute 33, Code value 49.
- Every `rdfs:domain` triple resolves to an in-file `owl:Class` (0 failures).
- `rdfs:subClassOf` = 0 (unchanged — still an honest flat class set; no
  Entity-to-Entity `skos:broader`/`narrower` exists in the source data for
  the 3 new Entities either).
- Every `skos:Concept` has `skos:inScheme netex:ev-charging`; every Entity is
  back-linked from the scheme's `skos:hasTopConcept`; every Attribute's
  `skos:broader` target is typed `Entity`; every Entity's `skos:narrower`
  attribute reciprocates with a matching `skos:broader` (0 mismatches on all
  four checks).
- `git diff --stat -- pipelines/load-netex/netex.ttl` for this pass: **213
  insertions(+), 0 deletions(-)** — every original line is byte-identical
  and present verbatim; only new lines were added.
