"""Runs the generator on the real pinned NeTEx XSD. Skipped unless NETEXGEN_SOURCES names a directory that
holds the pinned files at their sources.json paths (the checkout root, containing xsd/)."""
import json
import os
import unittest

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from netexgen import netex_owl, v020_alignment
from netexgen.netex_owl import NS, to_turtle

SOURCES = os.environ.get("NETEXGEN_SOURCES")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE_BUDGET = 12 * 1024 * 1024


@unittest.skipUnless(SOURCES, "NETEXGEN_SOURCES is not set")
class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "sources.json"), encoding="utf-8") as f:
            pinned = [k[len("xsd/"):] for k in json.load(f)["netex"]["files"]]
        cls.text = to_turtle(os.path.join(SOURCES, "xsd"), pinned)
        cls.g = Graph().parse(data=cls.text, format="turtle")

    def count(self, rdf_type):
        return len(set(self.g.subjects(RDF.type, rdf_type)))

    def test_counts_are_in_the_expected_ranges(self):
        schemes = self.count(SKOS.ConceptScheme)
        values = len(set(self.g.subjects(SKOS.inScheme, None)))
        entities = self.count(OWL.Class) - schemes
        self.assertTrue(1040 <= schemes <= 1060, schemes)
        self.assertTrue(8700 <= values <= 8900, values)
        self.assertGreaterEqual(entities, 790)
        self.assertTrue(80000 <= len(self.g) <= 200000, len(self.g))

    def test_expected_terms_exist(self):
        for name in ("VehicleChargingEquipment", "RechargingStation", "PlugTypeEnumeration/type2", "ServiceJourney",
                     "StopPlace", "FareProduct", "CompositeFrame"):
            self.assertIn((URIRef(NS + name), None, None), self.g, name)

    def test_reference_ranges_follow_the_referenced_class_not_an_inherited_id_type(self):
        place_refs = [p for p in self.g.subjects(RDF.type, OWL.ObjectProperty) if str(p).endswith(".PlaceRef")]
        self.assertGreater(len(place_refs), 5)
        for p in place_refs:
            self.assertEqual(set(self.g.objects(p, RDFS.range)), {URIRef(NS + "Place")}, p)

    def test_every_alignment_subject_exists(self):
        for row in v020_alignment.ALIGNMENT:
            self.assertIn((URIRef(NS + row[0]), None, None), self.g, row[0])

    def test_size_budget(self):
        self.assertLess(len(self.text.encode("utf-8")), SIZE_BUDGET)

    def test_second_run_is_byte_identical(self):
        with open(os.path.join(HERE, "sources.json"), encoding="utf-8") as f:
            pinned = [k[len("xsd/"):] for k in json.load(f)["netex"]["files"]]
        self.assertEqual(to_turtle(os.path.join(SOURCES, "xsd"), pinned), self.text)

    def test_only_one_ontology_and_it_is_the_namespace(self):
        self.assertEqual(set(self.g.subjects(RDF.type, OWL.Ontology)), {URIRef(NS)})


if __name__ == "__main__":
    unittest.main()
