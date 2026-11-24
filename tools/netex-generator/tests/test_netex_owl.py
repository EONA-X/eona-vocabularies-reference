import unittest

from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from netexgen import netex_owl
from netexgen.netex_owl import NS, Mapper, NameCollision
from netexgen.turtle import Anon
from netexgen.xsd_load import UnsupportedSchema

from .helpers import fixture_model, inline_model, iri, objects

SKOS = "http://www.w3.org/2004/02/skos/core#"
DCT = "http://purl.org/dc/terms/"
SCHEME = URIRef(SKOS + "ConceptScheme")
CONCEPT = URIRef(SKOS + "Concept")


def skos(n):
    return URIRef(SKOS + n)


def equivalent_datatype(triples, s):
    (anon,) = objects(triples, s, OWL.equivalentClass)
    return dict(anon.pairs)


class SimpleTypeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triples = Mapper(fixture_model()).map_simple_types()

    def test_enumeration_is_a_class_and_a_concept_scheme(self):
        s = iri("PlugTypeEnumeration")
        self.assertEqual(objects(self.triples, s, RDF.type), {OWL.Class, SCHEME})
        self.assertEqual(objects(self.triples, s, RDFS.label), {Literal("PlugTypeEnumeration")})
        self.assertEqual(objects(self.triples, s, RDFS.isDefinedBy), {URIRef(NS)})
        self.assertEqual(objects(self.triples, s, RDFS.comment), {Literal("Allowed plug types.", lang="en")})

    def test_enumeration_values_are_concepts_of_the_scheme(self):
        scheme = iri("PlugTypeEnumeration")
        v = URIRef(str(scheme) + "/type2")
        self.assertEqual(objects(self.triples, v, RDF.type), {CONCEPT, scheme})
        self.assertEqual(objects(self.triples, v, skos("inScheme")), {scheme})
        self.assertEqual(objects(self.triples, v, skos("notation")), {Literal("type2")})
        self.assertEqual(objects(self.triples, v, skos("prefLabel")), {Literal("type2")})
        self.assertEqual(objects(self.triples, v, skos("definition")), {Literal("IEC 62196 type 2.", lang="en")})
        self.assertEqual(objects(self.triples, URIRef(str(scheme) + "/ac"), skos("definition")), set())

    def test_value_iris_stay_readable_and_are_percent_encoded(self):
        scheme = str(iri("PlugTypeEnumeration"))
        subjects = {str(s) for s, p, o in self.triples}
        self.assertIn(scheme + "/nema5-20", subjects)
        self.assertIn(scheme + "/1-PhaseAC", subjects)
        self.assertIn(scheme + "/a%2Fb", subjects)
        self.assertEqual(objects(self.triples, URIRef(scheme + "/a%2Fb"), skos("notation")), {Literal("a/b")})

    def test_named_restriction_resolves_the_chain_to_the_builtin(self):
        s = iri("TypeOfPlugIdType")  # TypeOfPlugIdType -> ObjectIdType -> xsd:normalizedString
        self.assertEqual(objects(self.triples, s, RDF.type), {RDFS.Datatype})
        self.assertEqual(equivalent_datatype(self.triples, s),
                         {RDF.type: RDFS.Datatype, OWL.onDatatype: XSD.normalizedString})

    def test_facets_other_than_enumeration_are_dropped(self):
        s = iri("WattageType")
        self.assertEqual(equivalent_datatype(self.triples, s)[OWL.onDatatype], XSD.decimal)
        self.assertEqual(objects(self.triples, s, RDFS.comment), {Literal("Power in watts.", lang="en")})
        self.assertFalse([t for t in self.triples if "minInclusive" in str(t[1])])

    def test_list_is_a_string_datatype_that_names_its_item_type(self):
        s = iri("PlugTypeList")
        self.assertEqual(objects(self.triples, s, RDF.type), {RDFS.Datatype})
        self.assertEqual(equivalent_datatype(self.triples, s)[OWL.onDatatype], XSD.string)
        self.assertEqual(objects(self.triples, s, RDFS.seeAlso), {iri("PlugTypeEnumeration")})
        self.assertEqual(objects(self.triples, s, skos("scopeNote")),
                         {Literal("Space-separated list of PlugTypeEnumeration.", lang="en")})
        t = iri("TokenList")
        self.assertEqual(objects(self.triples, t, RDFS.seeAlso), {XSD.NMTOKEN})
        self.assertEqual(objects(self.triples, t, skos("scopeNote")),
                         {Literal("Space-separated list of xsd:NMTOKEN.", lang="en")})

    def test_union_is_a_datatype_that_names_its_members(self):
        s = iri("PlugOrCurrentEnumeration")
        self.assertEqual(objects(self.triples, s, RDF.type), {RDFS.Datatype})
        self.assertEqual(objects(self.triples, s, OWL.equivalentClass), set())
        self.assertEqual(objects(self.triples, s, RDFS.seeAlso),
                         {iri("PlugTypeEnumeration"), iri("CurrentTypeEnumeration")})
        self.assertEqual(objects(self.triples, s, skos("scopeNote")),
                         {Literal("Union of CurrentTypeEnumeration, PlugTypeEnumeration.", lang="en")})

    def test_source_points_at_the_file_and_commit(self):
        s = iri("WattageType")
        self.assertEqual(objects(self.triples, s, URIRef(DCT + "source")), {URIRef(
            "https://github.com/TransmodelEcosystem/NeTEx/blob/%s/xsd/netex_framework/netex_base.xsd"
            % netex_owl.COMMIT)})

    def test_only_netex_namespace_types_are_minted(self):
        self.assertTrue(all(str(s).startswith(NS) for s, p, o in self.triples))
        self.assertEqual({s for s, p, o in self.triples if p == RDF.type and o == RDFS.Datatype} >= {iri("WattageType")}, True)

    def test_tabs_and_newlines_in_documentation_are_collapsed(self):
        # the fixture documentation of WattageType spans two lines
        self.assertNotIn("\n", str(next(iter(objects(self.triples, iri("WattageType"), RDFS.comment)))))


def simple(body):
    return Mapper(inline_model(body)).map_simple_types()


class SimpleTypeEdgeTest(unittest.TestCase):
    def test_unknown_facet_is_refused(self):
        with self.assertRaises(UnsupportedSchema):
            simple('<xsd:simpleType name="T"><xsd:restriction base="xsd:string"><xsd:weird value="1"/>'
                   '</xsd:restriction></xsd:simpleType>')

    def test_unknown_builtin_is_refused(self):
        with self.assertRaises(UnsupportedSchema):
            simple('<xsd:simpleType name="T"><xsd:restriction base="xsd:nonsense"/></xsd:simpleType>')

    def test_unresolved_base_is_refused(self):
        with self.assertRaises(UnsupportedSchema):
            simple('<xsd:simpleType name="T"><xsd:restriction base="Missing"/></xsd:simpleType>')

    def test_restriction_of_an_enumeration_without_values_is_a_datatype(self):
        t = simple('<xsd:simpleType name="E"><xsd:restriction base="xsd:string"><xsd:enumeration value="a"/>'
                   '</xsd:restriction></xsd:simpleType>'
                   '<xsd:simpleType name="F"><xsd:restriction base="E"><xsd:pattern value="a"/></xsd:restriction></xsd:simpleType>')
        self.assertEqual(objects(t, iri("F"), RDF.type), {RDFS.Datatype})
        self.assertEqual(equivalent_datatype(t, iri("F"))[OWL.onDatatype], XSD.string)

    def test_union_with_inline_member_is_refused(self):
        with self.assertRaises(UnsupportedSchema):
            simple('<xsd:simpleType name="U"><xsd:union><xsd:simpleType><xsd:restriction base="xsd:string"/>'
                   '</xsd:simpleType></xsd:union></xsd:simpleType>')

    def test_mint_collision_between_owners_is_refused(self):
        m = Mapper(inline_model(""))
        m.mint(iri("X"), "a", "w")
        m.mint(iri("X"), "a", "w")
        with self.assertRaises(NameCollision):
            m.mint(iri("X"), "b", "w")


if __name__ == "__main__":
    unittest.main()
