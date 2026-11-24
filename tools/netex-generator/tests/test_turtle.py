import random
import unittest

from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS, XSD

from netexgen.turtle import Anon, write_turtle

EX = "https://example.org/ns#"
PREFIXES = {"ex": EX, "owl": str(OWL), "rdfs": str(RDFS), "rdf": str(RDF),
            "xsd": str(XSD), "unused": "https://unused.example/"}


def sample():
    root = URIRef(EX)
    return [
        (URIRef(EX + "B"), RDF.type, OWL.Class),
        (URIRef(EX + "B"), RDFS.label, Literal("B")),
        (URIRef(EX + "B"), RDFS.subClassOf, URIRef(EX + "A")),
        (URIRef(EX + "A"), RDF.type, OWL.Class),
        (URIRef(EX + "A"), RDFS.comment, Literal("line1\nline2 \"q\" \\ \t", lang="en")),
        (URIRef(EX + "A"), RDFS.seeAlso, Literal("3", datatype=XSD.int)),
        (root, RDF.type, OWL.Ontology),
        (root, RDFS.label, Literal("Root")),
    ]


class TurtleTest(unittest.TestCase):
    def render(self, triples, **kw):
        return write_turtle(triples, PREFIXES, header=["generated", "second line"], root=URIRef(EX), **kw)

    def test_shuffled_inputs_are_byte_identical(self):
        a = sample()
        b = list(a)
        random.Random(7).shuffle(b)
        self.assertEqual(self.render(a), self.render(b))

    def test_roundtrip_with_escaping(self):
        out = self.render(sample())
        g = Graph().parse(data=out, format="turtle")
        self.assertEqual(len(g), len(sample()))
        self.assertIn((URIRef(EX + "A"), RDFS.comment, Literal("line1\nline2 \"q\" \\ \t", lang="en")), g)

    def test_unsafe_local_name_uses_full_iri(self):
        iri = URIRef(EX + "Name/with%2Fslash.x")
        out = self.render([(iri, RDF.type, OWL.Class)])
        self.assertIn("<" + str(iri) + ">", out)
        self.assertNotIn("ex:Name/with", out)
        self.assertIn("ex:", self.render([(URIRef(EX + "Safe-1"), RDF.type, OWL.Class)]))

    def test_anon_is_inline_and_isomorphic(self):
        anon = Anon(frozenset({(RDF.type, OWL.Restriction), (OWL.onProperty, URIRef(EX + "p"))}))
        triples = sample() + [(URIRef(EX + "A"), RDFS.subClassOf, anon)]
        out = self.render(triples)
        self.assertIn("[ ", out)
        expected = Graph()
        for s, p, o in sample():
            expected.add((s, p, o))
        from rdflib import BNode
        b = BNode()
        expected.add((URIRef(EX + "A"), RDFS.subClassOf, b))
        expected.add((b, RDF.type, OWL.Restriction))
        expected.add((b, OWL.onProperty, URIRef(EX + "p")))
        self.assertTrue(isomorphic(expected, Graph().parse(data=out, format="turtle")))

    def test_prefix_table_sorted_and_only_used(self):
        out = self.render(sample())
        prefixes = [l.split()[1] for l in out.splitlines() if l.startswith("@prefix")]
        self.assertEqual(prefixes, sorted(prefixes))
        self.assertNotIn("unused:", out)

    def test_layout(self):
        out = self.render(sample())
        self.assertTrue(out.startswith("# generated\n# second line\n"))
        self.assertTrue(out.endswith(".\n"))
        self.assertFalse(out.endswith("\n\n"))
        # root ontology first, rdf:type written as 'a' first, label next
        body = out.split("\n\n", 1)[1] if "\n\n" in out else out
        first_subject = [l for l in out.splitlines() if l and not l.startswith(("@", "#", " "))][0]
        self.assertTrue(first_subject.startswith("ex: a owl:Ontology") or first_subject.startswith("<" + EX + "> a"))
        self.assertIn("a owl:Class ;\n    rdfs:label \"B\" ;", out)


if __name__ == "__main__":
    unittest.main()
