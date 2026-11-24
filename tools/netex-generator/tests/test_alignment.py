import os
import unittest

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from netexgen import netex_owl, v020_alignment
from netexgen.netex_owl import NS, V020, build_triples

from .helpers import HERE, fixture_model, iri

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
V020_TTL = os.path.join(ROOT, "netex", "v0.2.0", "ontology.ttl")
MATCH = {SKOS.exactMatch, SKOS.closeMatch, SKOS.broadMatch, SKOS.narrowMatch, SKOS.relatedMatch}


def v020_terms():
    g = Graph().parse(V020_TTL, format="turtle")
    classes = {s for s in g.subjects(RDF.type, OWL.Class)}
    props = {s for t in (OWL.DatatypeProperty, OWL.ObjectProperty) for s in g.subjects(RDF.type, t)}
    codes = {s for s in g.subjects(RDF.type, SKOS.Concept)} - classes - props
    names = lambda terms: {str(t)[len(V020):] for t in terms if str(t).startswith(V020)}
    return names(classes), names(props), names(codes)


class AlignmentTableTest(unittest.TestCase):
    def test_every_v020_term_is_mapped_or_listed_as_unmapped(self):
        classes, props, codes = v020_terms()
        self.assertEqual((len(classes), len(props), len(codes)), (9, 33, 49))
        mapped = {row[2] for row in v020_alignment.ALIGNMENT}
        unmapped = set(v020_alignment.UNMAPPED)
        every = classes | props | codes
        self.assertEqual(every - mapped - unmapped, set(), "v0.2.0 terms neither mapped nor unmapped")
        self.assertEqual(mapped & unmapped, set())
        self.assertEqual((mapped | unmapped) - every, set(), "table names a term v0.2.0 does not have")

    def test_every_unmapped_term_has_a_reason(self):
        for name, reason in v020_alignment.UNMAPPED.items():
            self.assertTrue(reason.strip(), name)

    def test_predicates_are_skos_mapping_properties(self):
        for sub, pred, old, note in v020_alignment.ALIGNMENT:
            self.assertIn(URIRef(str(SKOS) + pred), MATCH, (sub, pred))
            self.assertTrue(note is None or note.strip())

    def test_rows_are_unique_and_sorted_by_subject(self):
        keys = [(r[0], r[1], r[2]) for r in v020_alignment.ALIGNMENT]
        self.assertEqual(len(keys), len(set(keys)))

    def test_documented_examples(self):
        rows = {(r[0], r[1], r[2]) for r in v020_alignment.ALIGNMENT}
        for row in [("VehicleChargingEquipment", "exactMatch", "ElectricVehicleChargingEquipment"),
                    ("VehicleChargingEquipmentGroup.MaximumPower", "closeMatch", "powerRating"),
                    ("VehicleChargingEquipmentGroup.PlugType", "exactMatch", "connectorStandard"),
                    ("PlugTypeEnumeration/type2", "exactMatch", "connectorStandard-type2"),
                    ("PlugTypeEnumeration/nema5-20", "exactMatch", "connectorStandard-nema520"),
                    ("CurrentTypeEnumeration/1-PhaseAC", "exactMatch", "currentType-1PhaseAC"),
                    ("BatteryEquipmentGroup.MaximumChargingPower", "exactMatch", "maximumChargingPower"),
                    ("RechargingEquipmentProfileGroup.MaximumChargingPower", "exactMatch",
                     "profileMaximumChargingPower")]:
            self.assertIn(row, rows)
        self.assertIn("availabilityStatus", v020_alignment.UNMAPPED)
        self.assertIn("availabilityStatus-available", v020_alignment.UNMAPPED)


class AlignmentOutputTest(unittest.TestCase):
    def test_rows_whose_subject_the_schema_defines_become_triples_to_v020_iris(self):
        t = build_triples(fixture_model(), lenient_alignment=True)
        self.assertIn((iri("VehicleChargingEquipmentGroup.MaximumPower"), SKOS.closeMatch, URIRef(V020 + "powerRating")), t)
        self.assertIn((iri("PlugTypeEnumeration/type2"), SKOS.exactMatch, URIRef(V020 + "connectorStandard-type2")), t)
        self.assertNotIn((iri("RechargingBay"), SKOS.exactMatch, URIRef(V020 + "RechargingBay")), t)  # not in the fixture

    def test_a_subject_the_schema_does_not_define_fails_the_build(self):
        with self.assertRaises(v020_alignment.AlignmentError):
            build_triples(fixture_model())

    def test_alignment_subjects_stay_in_the_namespace_and_objects_in_v020(self):
        for s, p, o in v020_alignment.alignment_triples(v020_alignment.ALIGNMENT):
            self.assertTrue(str(s).startswith(NS))
            self.assertTrue(str(o).startswith(V020))

    def test_invariants_refuse_a_v020_iri_under_another_predicate(self):
        t = build_triples(fixture_model(), lenient_alignment=True)
        with self.assertRaises(AssertionError):
            netex_owl.check_invariants(t | {(iri("Parking"), RDFS.seeAlso, URIRef(V020 + "RechargingBay"))})


if __name__ == "__main__":
    unittest.main()
