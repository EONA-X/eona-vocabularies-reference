"""Hand-maintained alignment of the v0.2.0 hub-curated EV-charging subset to the generated v1.0.0 terms.

Each row is (v1.0.0 term, SKOS mapping predicate, v0.2.0 term, note). Terms are local names:
a v1.0.0 term is relative to https://vocabulary.eona-x.eu/ontology/netex/v1.0.0#, a v0.2.0 term to
.../netex/v0.2.0#. The rows were seeded from the skos:editorialNote of the v0.2.0 terms, which name
the NeTEx source element. v0.2.0 stays published as it is; its IRIs are what the crosswalk uses.
"""
from rdflib import URIRef
from rdflib.namespace import SKOS

V1 = "https://vocabulary.eona-x.eu/ontology/netex/v1.0.0#"
V020 = "https://vocabulary.eona-x.eu/ontology/netex/v0.2.0#"
PREDICATES = frozenset(["exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch"])


class AlignmentError(Exception):
    pass


def _rows():
    rows = []

    def add(new, pred, old, note=None):
        rows.append((new, pred, old, note))

    # entities
    add("VehicleChargingEquipment", "exactMatch", "ElectricVehicleChargingEquipment",
        "v0.2.0 renamed NeTEx VehicleChargingEquipment")
    for name in ("BatteryEquipment", "RechargingBay", "RechargingEquipmentProfile", "RechargingPointAssignment",
                 "RechargingStation", "RefuellingEquipment", "TypeOfBatteryChemistry", "TypeOfPlug"):
        add(name, "exactMatch", name)

    # attributes
    for new, old in [
        ("BatteryEquipmentGroup.BatteryCapacity", "batteryCapacity"),
        ("BatteryEquipmentGroup.BatteryUsableCapacity", "batteryUsableCapacity"),
        ("BatteryEquipmentGroup.MaximumChargingPower", "maximumChargingPower"),
        ("BatteryEquipmentGroup.NominalVoltage", "nominalVoltage"),
        ("RechargingEquipmentProfileGroup.ChargingVoltage", "chargingVoltage"),
        ("RechargingEquipmentProfileGroup.CurrentType", "profileCurrentType"),
        ("RechargingEquipmentProfileGroup.FinalisationDuration", "finalisationDuration"),
        ("RechargingEquipmentProfileGroup.MaximumChargingPower", "profileMaximumChargingPower"),
        ("RechargingEquipmentProfileGroup.PlugType", "profilePlugType"),
        ("RechargingEquipmentProfileGroup.PowerCouplingType", "profilePowerCouplingType"),
        ("RechargingEquipmentProfileGroup.PreparationDuration", "preparationDuration"),
        ("RechargingEquipmentProfileGroup.TypeOfPlugRef", "profileTypeOfPlug"),
        ("RechargingPointAssignmentGroup.EquipmentPlaceRef", "equipmentPlace"),
        ("RechargingPointAssignmentGroup.SiteComponentRef", "siteComponent"),
        ("RechargingPointAssignmentGroup.VehicleChargingEquipmentRef", "vehicleChargingEquipment"),
        ("RechargingPointAssignmentGroup.servedScheduledStopPoints", "servedScheduledStopPoints"),
        ("RechargingStationGroup.TotalPower", "totalPower"),
        ("RefuellingEquipmentGroup.FuelType", "fuelType"),
        ("VehicleChargingEquipmentGroup.CurrentType", "currentType"),
        ("VehicleChargingEquipmentGroup.FreeRecharging", "freeRecharging"),
        ("VehicleChargingEquipmentGroup.GridVoltage", "gridVoltage"),
        ("VehicleChargingEquipmentGroup.PlugType", "connectorStandard"),
        ("VehicleChargingEquipmentGroup.PowerCouplingType", "powerCouplingType"),
        ("VehicleChargingEquipmentGroup.ReservationRequired", "reservationRequired"),
        ("VehicleChargingEquipmentGroup.ReservationUrl", "reservationUrl"),
        ("VehicleChargingEquipmentGroup.TypeOfPlugRef", "typeOfPlug"),
    ]:
        add(new, "exactMatch", old)
    add("VehicleChargingEquipmentGroup.MaximumPower", "closeMatch", "powerRating",
        "v0.2.0 exposes the value in kW, NeTEx in W")
    add("RechargingEquipmentProfileGroup.compatibleWith", "closeMatch", "compatibleWith",
        "v0.2.0 types it as a datatype property, NeTEx as a list of references")
    add("BatteryEquipmentGroup.TypeOfBatteryChemistryRef", "closeMatch", "typeOfBatteryChemistry",
        "v0.2.0 types it as a datatype property, NeTEx as a reference")
    for old in ("batteryChemistryNameOfClassifiedEntityClass", "plugNameOfClassifiedEntityClass"):
        add("TypeOfEntity_VersionStructure.nameOfClassifiedEntityClass", "narrowMatch", old,
            "v0.2.0 repeats the attribute per entity, NeTEx declares it once on TYPE OF ENTITY")

    # code values: (v0.2.0 prefix, v1.0.0 enumeration, {v0.2.0 value: v1.0.0 value or None when identical})
    for prefix, scheme, odd, values in [
        ("connectorStandard", "PlugTypeEnumeration", {"nema520": "nema5-20"},
         "CHAdeMO avcon ccsCombo1Plug ccsCombo2Plug combinedChargingSystem nema520 shockproof tesla type1 type2 "
         "type3 typeE typeF typeG typeJ undefined"),
        ("currentType", "CurrentTypeEnumeration", {"1PhaseAC": "1-PhaseAC", "3PhaseAC": "3-PhaseAC"},
         "1PhaseAC 3PhaseAC DC undefined"),
        ("fuelType", "FuelTypeEnumeration", {},
         "battery biodiesel diesel dieselBatteryHybrid electricContact electricity ethanol hydrogen liquidGas "
         "methane naturalGas none other petrol petrolBatteryHybrid petrolLeaded petrolUnleaded tpg"),
        ("powerCouplingType", "PowerCouplingTypeEnumeration", {},
         "induction other pantograph pantographAbove plug undefined"),
    ]:
        for v in values.split():
            add("%s/%s" % (scheme, odd.get(v, v)), "exactMatch", "%s-%s" % (prefix, v))
    return sorted(rows)


ALIGNMENT = _rows()

# v0.2.0 terms the hub added that the XSD has no counterpart for
UNMAPPED = {
    "availabilityStatus": "Hub-curated. NeTEx carries no equipment-level availability status; real-time status is conveyed through SIRI.",
    "availabilityStatus-available": "Code of the hub-curated availabilityStatus.",
    "availabilityStatus-occupied": "Code of the hub-curated availabilityStatus.",
    "availabilityStatus-outOfService": "Code of the hub-curated availabilityStatus.",
    "availabilityStatus-reserved": "Code of the hub-curated availabilityStatus.",
    "availabilityStatus-unknown": "Code of the hub-curated availabilityStatus.",
    "location": "Hub-curated shortcut. NeTEx places equipment through an EQUIPMENT PLACE or SITE COMPONENT, "
                "not through a location on the equipment.",
}


def alignment_triples(rows):
    return [(URIRef(V1 + new), getattr(SKOS, pred), URIRef(V020 + old)) for new, pred, old, note in rows]
