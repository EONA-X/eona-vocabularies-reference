import os
import random
import tempfile
import unittest

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from eonagen import schema_org_slice as so

HERE = os.path.dirname(os.path.abspath(__file__))
S = "https://schema.org/"
MINI = os.path.join(HERE, "fixtures", "schema-org-mini.ttl")
GOLDEN = os.path.join(HERE, "golden", "schema-org-mini.ttl")


def u(name):
    return URIRef(S + name)


def build():
    g = Graph().parse(MINI, format="turtle")
    return g, Graph().parse(data=so.slice_to_turtle(g, source_sha256="0" * 64, commit="c" * 40, version="30.1"), format="turtle")


class SliceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src, cls.out = build()

    def classes(self):
        return set(self.out.subjects(RDF.type, RDFS.Class))

    def test_seed_closure_is_transitive_with_two_parents(self):
        for n in ("Reservation", "FlightReservation", "TwoParents", "Trip", "Flight", "ProgramMembership"):
            self.assertIn((u(n), RDF.type, RDFS.Class), self.out)
        seeds = so.seed_classes(self.src)
        self.assertNotIn(u("Place"), seeds)
        self.assertEqual(len(seeds), 6)

    def test_two_parent_chain_reaches_other_as_super(self):
        self.assertIn((u("TwoParents"), RDFS.subClassOf, u("Other")), self.out)
        self.assertIn((u("Other"), RDF.type, RDFS.Class), self.out)

    def test_superclasses_carry_only_type_label_subclassof(self):
        for n in ("Intangible", "Thing", "Other"):
            preds = set(self.out.predicates(u(n), None))
            self.assertLessEqual(preds, {RDF.type, RDFS.label, RDFS.subClassOf}, n)
            self.assertIn(RDFS.label, preds)
        self.assertEqual(list(self.out.objects(u("Intangible"), RDFS.comment)), [])

    def test_seed_classes_keep_upstream_triples(self):
        for p, o in self.src.predicate_objects(u("Reservation")):
            self.assertIn((u("Reservation"), p, o), self.out)

    def test_properties_by_domain_keep_all_triples(self):
        for n in ("reservationFor", "reservationStatus", "tripNote", "inverseA"):
            for p, o in self.src.predicate_objects(u(n)):
                self.assertIn((u(n), p, o), self.out, n)
        self.assertEqual(list(self.out.triples((u("placeOnly"), None, None))), [])

    def test_range_and_domain_stubs(self):
        # Place is a range and an extra domain: stub, no comment
        self.assertIn((u("Place"), RDF.type, RDFS.Class), self.out)
        self.assertIn((u("Place"), RDFS.subClassOf, u("Thing")), self.out)
        self.assertEqual(list(self.out.objects(u("Place"), RDFS.comment)), [])
        # Text: all its upstream types kept
        self.assertIn((u("Text"), RDF.type, u("DataType")), self.out)
        self.assertEqual(list(self.out.objects(u("Text"), RDFS.comment)), [])
        # enumeration chain
        self.assertIn((u("StatusEnumeration"), RDFS.subClassOf, u("Enumeration")), self.out)
        self.assertEqual(list(self.out.objects(u("ReservationStatusType"), RDFS.comment)), [])

    def test_enumeration_members(self):
        for n in ("ReservationConfirmed", "ReservationHold"):
            self.assertIn((u(n), RDF.type, u("ReservationStatusType")), self.out)
            self.assertIn((u(n), RDFS.label, Literal(n)), self.out)
            self.assertTrue(list(self.out.objects(u(n), RDFS.comment)))

    def test_root_ontology(self):
        root = URIRef(S)
        self.assertIn((root, RDF.type, OWL.Ontology), self.out)
        self.assertIn((root, OWL.versionInfo, Literal("30.1")), self.out)
        self.assertIn((root, URIRef("http://purl.org/dc/terms/license"), URIRef("https://creativecommons.org/licenses/by-sa/3.0/")), self.out)
        src = next(self.out.objects(root, URIRef("http://purl.org/dc/terms/source")))
        self.assertIn("c" * 40, str(src))
        self.assertEqual(len(list(self.out.subjects(RDF.type, OWL.Ontology))), 1)

    def test_missing_seed_fails(self):
        for missing in ("Reservation", "Trip", "ProgramMembership"):
            g = Graph().parse(MINI, format="turtle")
            g.remove((u(missing), None, None))
            with self.assertRaises(so.MissingSeed):
                so.slice_to_turtle(g, source_sha256="0", commit="c", version="30.1")

    def test_golden(self):
        g = Graph().parse(MINI, format="turtle")
        out = so.slice_to_turtle(g, source_sha256="0" * 64, commit="c" * 40, version="30.1")
        with open(GOLDEN, encoding="utf-8") as f:
            self.assertEqual(out, f.read())

    def test_shuffled_input_same_bytes(self):
        triples = list(Graph().parse(MINI, format="turtle"))
        random.Random(3).shuffle(triples)
        g = Graph()
        for t in triples:
            g.add(t)
        a = so.slice_to_turtle(g, source_sha256="0" * 64, commit="c" * 40, version="30.1")
        b = so.slice_to_turtle(Graph().parse(MINI, format="turtle"), source_sha256="0" * 64, commit="c" * 40, version="30.1")
        self.assertEqual(a, b)


@unittest.skipUnless(os.environ.get("EONAGEN_SOURCES"), "needs the real pinned file")
class RealSmoke(unittest.TestCase):
    def test_counts(self):
        path = os.path.join(os.environ["EONAGEN_SOURCES"], "data/releases/30.1/schemaorg-current-https.ttl")
        g = Graph().parse(path, format="turtle")
        out = Graph().parse(data=so.slice_to_turtle(g, source_sha256="0", commit="c", version="30.1"), format="turtle")
        seeds = so.seed_classes(g)
        self.assertEqual(len(seeds), 18)
        self.assertEqual(len(so.slice_properties(g, seeds)), 73)
        self.assertGreater(len(out), 500)


if __name__ == "__main__":
    unittest.main()
