import os
import subprocess
import sys
import tempfile
import unittest

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from netexgen import netex_owl
from netexgen.netex_owl import NS, SCHEMA_ORG, Mapper, NameCollision, build_triples, check_invariants, to_turtle
from netexgen.turtle import Anon
from netexgen.xsd_load import UnsupportedSchema

from .helpers import FIXTURE_XSD, HERE, fixture_model, inline_model, iri, objects

ROOT = os.path.dirname(HERE)

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


# ---------------------------------------------------------------- classes

def restrictions(triples, cls):
    out = {}
    for o in objects(triples, cls, RDFS.subClassOf):
        if isinstance(o, Anon):
            d = dict(o.pairs)
            out[d[OWL.onProperty]] = d
    return out


def supers(triples, cls):
    return {o for o in objects(triples, cls, RDFS.subClassOf) if not isinstance(o, Anon)}


def subjects(triples):
    return {s for s, p, o in triples}


class ClassTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triples = build_triples(fixture_model())

    def test_element_with_a_single_version_structure_folds_it(self):
        c = iri("VehicleChargingEquipment")
        self.assertEqual(objects(self.triples, c, RDF.type), {OWL.Class})
        self.assertEqual(objects(self.triples, c, skos("hiddenLabel")),
                         {Literal("VehicleChargingEquipment_VersionStructure")})
        self.assertNotIn(iri("VehicleChargingEquipment_VersionStructure"), subjects(self.triples))
        self.assertEqual(objects(self.triples, c, RDFS.label), {Literal("VehicleChargingEquipment")})
        self.assertEqual(objects(self.triples, c, RDFS.isDefinedBy), {URIRef(NS)})

    def test_documentation_keeps_version_markers_and_collapses_whitespace(self):
        c = iri("VehicleChargingEquipment")
        self.assertEqual(objects(self.triples, c, RDFS.comment),
                         {Literal("Specialisation of PLACE EQUIPMENT for vehicle charging. +v2.0", lang="en")})

    def test_superclass_from_type_and_substitution_group_is_deduplicated(self):
        self.assertEqual(supers(self.triples, iri("VehicleChargingEquipment")), {iri("PlaceEquipment")})

    def test_version_structure_shared_by_two_elements_is_minted(self):
        shared = iri("Parking_VersionStructure")
        self.assertEqual(objects(self.triples, shared, RDF.type), {OWL.Class})
        self.assertEqual(supers(self.triples, iri("Parking")) & {shared}, {shared})
        self.assertEqual(supers(self.triples, iri("ParkingArea")) & {shared}, {shared})
        self.assertEqual(supers(self.triples, shared), {iri("DataManagedObjectStructure")})

    def test_substitution_group_and_type_give_two_superclasses(self):
        self.assertEqual(supers(self.triples, iri("RechargingStation")),
                         {iri("Parking_VersionStructure"), iri("Parking")})
        self.assertNotIn(iri("RechargingStation_VersionStructure"), subjects(self.triples))

    def test_dummy_elements_are_not_minted_and_their_heads_are_skipped(self):
        self.assertNotIn(iri("ParkingBay_Dummy"), subjects(self.triples))
        self.assertNotIn(iri("TariffZone_Dummy"), subjects(self.triples))
        self.assertEqual(supers(self.triples, iri("ParkingBay")), {iri("PlaceEquipment")})
        self.assertEqual(objects(self.triples, iri("Zone"), skos("hiddenLabel")), {Literal("Zone_VersionStructure")})
        self.assertNotIn(iri("Zone_VersionStructure"), subjects(self.triples))

    def test_abstract_element_keeps_its_class_and_says_so(self):
        c = iri("PlaceEquipment")
        self.assertEqual(objects(self.triples, c, RDF.type), {OWL.Class})
        self.assertEqual(objects(self.triples, c, skos("scopeNote")), {Literal("Abstract in the XSD.", lang="en")})
        self.assertEqual(supers(self.triples, c), {iri("DataManagedObject"), iri("DataManagedObjectStructure")})

    def test_element_typed_by_a_named_type_is_a_subclass_of_it(self):
        self.assertEqual(supers(self.triples, iri("DataManagedObject")), {iri("DataManagedObjectStructure")})
        self.assertEqual(supers(self.triples, iri("DataManagedObjectStructure")), {iri("EntityInVersionStructure")})

    def test_ref_and_rel_structures_are_not_classes(self):
        for n in ("TypeOfPlugRef", "TypeOfPlugRefStructure", "VersionOfObjectRefStructure",
                  "rechargingStations_RelStructure", "MultilingualString", "TextType", "PrivateCodeStructure"):
            self.assertNotIn(iri(n), subjects(self.triples), n)

    def test_other_namespaces_are_not_minted(self):
        for s in subjects(self.triples):
            self.assertTrue(str(s).startswith(NS), s)
        self.assertEqual(objects(self.triples, iri("Point"), RDF.type), {OWL.Class})
        self.assertNotIn(iri("PointType"), subjects(self.triples))
        self.assertEqual(objects(self.triples, iri("Point"), RDFS.comment),
                         {Literal("A point (NeTEx). Clashes by name with the siri and gml ones.", lang="en")})

    def test_class_source_is_the_declaring_file(self):
        self.assertEqual(objects(self.triples, iri("Parking"), URIRef(DCT + "source")), {URIRef(
            "https://github.com/TransmodelEcosystem/NeTEx/blob/%s/xsd/netex_part_1/netex_equipment.xsd"
            % netex_owl.COMMIT)})


def prop(name):
    return iri(name)


def kinds(triples, p):
    return objects(triples, p, RDF.type)


class PropertyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triples = build_triples(fixture_model())

    def p(self, decl, name):
        return URIRef("%s%s.%s" % (NS, decl, name))

    def test_datatype_property_for_a_builtin(self):
        p = self.p("VehicleChargingEquipmentGroup", "FreeRecharging")
        self.assertEqual(kinds(self.triples, p), {OWL.DatatypeProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.label), {Literal("FreeRecharging")})
        self.assertEqual(objects(self.triples, p, skos("notation")), {Literal("FreeRecharging")})
        self.assertEqual(objects(self.triples, p, RDFS.range), {XSD.boolean})
        self.assertEqual(objects(self.triples, p, RDFS.comment), {Literal("Whether recharging is free.", lang="en")})
        self.assertEqual(objects(self.triples, p, RDFS.isDefinedBy), {URIRef(NS)})
        self.assertEqual(objects(self.triples, p, URIRef(DCT + "source")), {URIRef(
            "https://github.com/TransmodelEcosystem/NeTEx/blob/%s/xsd/netex_part_1/netex_equipment.xsd"
            % netex_owl.COMMIT)})

    def test_single_owner_gives_a_domain(self):
        p = self.p("VehicleChargingEquipmentGroup", "FreeRecharging")
        self.assertEqual(objects(self.triples, p, RDFS.domain), {iri("VehicleChargingEquipment")})
        self.assertEqual(objects(self.triples, p, URIRef(SCHEMA_ORG + "domainIncludes")), set())

    def test_several_owners_give_domain_includes_and_no_domain(self):
        p = self.p("PlaceEquipmentGroup", "Label")
        self.assertEqual(objects(self.triples, p, RDFS.domain), set())
        self.assertEqual(objects(self.triples, p, URIRef(SCHEMA_ORG + "domainIncludes")),
                         {iri("PlaceEquipment"), iri("ParkingBay")})

    def test_enumeration_typed_property_is_an_object_property_to_the_scheme(self):
        p = self.p("VehicleChargingEquipmentGroup", "PlugType")
        self.assertEqual(kinds(self.triples, p), {OWL.ObjectProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), {iri("PlugTypeEnumeration")})

    def test_list_and_union_typed_properties_are_datatype_properties(self):
        for n, r in (("SupportedPlugs", "PlugTypeList"), ("Current", "PlugOrCurrentEnumeration")):
            p = self.p("VehicleChargingEquipmentGroup", n)
            self.assertEqual(kinds(self.triples, p), {OWL.DatatypeProperty, OWL.FunctionalProperty}, n)
            self.assertEqual(objects(self.triples, p, RDFS.range), {iri(r)}, n)

    def test_multilingual_string_and_text_content_types_range_over_lang_string(self):
        p = self.p("EntityInVersionGroup", "Name")
        self.assertEqual(kinds(self.triples, p), {OWL.DatatypeProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), {RDF.langString})
        t = self.p("MultilingualString", "Text")
        self.assertNotIn(t, subjects(self.triples))  # MultilingualString is a datatype, not a class

    def test_simple_content_extension_ranges_over_its_base_datatype(self):
        p = self.p("DataManagedObjectGroup", "PrivateCode")
        self.assertEqual(kinds(self.triples, p), {OWL.DatatypeProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), {XSD.normalizedString})

    def test_class_typed_property_is_an_object_property(self):
        p = self.p("VehicleChargingEquipmentGroup", "Place")
        self.assertEqual(kinds(self.triples, p), {OWL.ObjectProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), {iri("PointStructure")})

    def test_ref_is_resolved_through_the_id_type(self):
        p = self.p("VehicleChargingEquipmentGroup", "TypeOfPlugRef")
        self.assertEqual(kinds(self.triples, p), {OWL.ObjectProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), {iri("TypeOfPlug")})

    def test_ref_to_an_entity_element_ranges_over_its_class(self):
        d = run(with_group('<xsd:element ref="Thing" minOccurs="0"/>', ENTITY))
        self.assertEqual(objects(d, iri("G.Thing"), RDFS.range), {iri("Thing")})
        self.assertEqual(kinds(d, iri("G.Thing")), {OWL.ObjectProperty, OWL.FunctionalProperty})

    def test_foreign_ref_is_an_object_property_without_range(self):
        p = self.p("PointStructure", "Point")
        self.assertEqual(kinds(self.triples, p), {OWL.ObjectProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), set())
        self.assertEqual(objects(self.triples, p, skos("scopeNote")),
                         {Literal("Range defined in the GML schema, not rendered.", lang="en")})

    def test_rel_structure_with_one_member_class_has_that_range(self):
        p = self.p("VehicleChargingEquipmentGroup", "rechargingStations")
        self.assertEqual(kinds(self.triples, p), {OWL.ObjectProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), {iri("RechargingStation")})

    def test_rel_structure_with_several_member_classes_lists_them_without_a_range(self):
        p = self.p("VehicleChargingEquipmentGroup", "mixedPlaces")
        self.assertEqual(kinds(self.triples, p), {OWL.ObjectProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), set())
        self.assertEqual(objects(self.triples, p, URIRef(SCHEMA_ORG + "rangeIncludes")),
                         {iri("ParkingBay"), iri("RechargingStation")})

    def test_anonymous_complex_type_becomes_a_class_with_its_own_properties(self):
        p = self.p("VehicleChargingEquipmentGroup", "Dimensions")
        c = iri("VehicleChargingEquipmentGroupDimensions")
        self.assertEqual(objects(self.triples, p, RDFS.range), {c})
        self.assertEqual(objects(self.triples, c, RDF.type), {OWL.Class})
        w = self.p("VehicleChargingEquipmentGroupDimensions", "Width")
        self.assertEqual(objects(self.triples, w, RDFS.domain), {c})
        self.assertIn(w, restrictions(self.triples, c))

    def test_anonymous_simple_type_becomes_an_enumeration(self):
        p = self.p("VehicleChargingEquipmentGroup", "Orientation")
        s = iri("VehicleChargingEquipmentGroupOrientation")
        self.assertEqual(objects(self.triples, p, RDFS.range), {s})
        self.assertEqual(kinds(self.triples, p), {OWL.ObjectProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, s, RDF.type), {OWL.Class, SCHEME})
        self.assertEqual(objects(self.triples, URIRef(str(s) + "/left"), skos("inScheme")), {s})

    def test_required_element_outside_a_choice_gives_min_cardinality_on_the_owner(self):
        r = restrictions(self.triples, iri("VehicleChargingEquipment"))
        p = self.p("VehicleChargingEquipmentGroup", "MaximumPower")
        self.assertEqual(r[p][OWL.minCardinality], Literal("1", datatype=XSD.nonNegativeInteger))
        self.assertEqual(r[p][RDF.type], OWL.Restriction)
        for n in ("FreeRecharging", "PlugType", "ChoiceA", "ChoiceB"):
            self.assertNotIn(self.p("VehicleChargingEquipmentGroup", n), r, n)

    def test_repeating_elements_are_not_functional(self):
        for n in ("Tag", "Alias", "rechargingStations", "mixedPlaces"):
            self.assertNotIn(OWL.FunctionalProperty, kinds(self.triples, self.p("VehicleChargingEquipmentGroup", n)), n)
        self.assertIn(OWL.FunctionalProperty, kinds(self.triples, self.p("VehicleChargingEquipmentGroup", "ChoiceA")))

    def test_attributes_are_functional_properties_and_id_is_dropped(self):
        p = self.p("BasicModificationDetailsGroup", "created")
        self.assertEqual(kinds(self.triples, p), {OWL.DatatypeProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(self.triples, p, RDFS.range), {XSD.dateTime})
        self.assertEqual(objects(self.triples, p, RDFS.domain), {iri("EntityInVersionStructure")})
        v = self.p("BasicModificationDetailsGroup", "version")
        self.assertEqual(objects(self.triples, v, RDFS.range), {iri("VersionIdType")})
        self.assertNotIn(self.p("EntityStructure", "id"), subjects(self.triples))

    def test_xsd_any_leaves_no_trace(self):
        self.assertEqual({s for s in subjects(self.triples) if str(s).startswith(NS + "ExtensionsStructure.")}, set())

    def test_properties_of_a_folded_type_are_scoped_by_the_declaring_component(self):
        self.assertIn(self.p("Parking_VersionStructure", "Capacity"), subjects(self.triples))
        self.assertIn(self.p("Zone_VersionStructure", "Area"), subjects(self.triples))
        self.assertEqual(objects(self.triples, self.p("Zone_VersionStructure", "Area"), RDFS.domain), {iri("Zone")})


ENTITY = ('<xsd:complexType name="Thing_VersionStructure"><xsd:sequence/></xsd:complexType>'
          '<xsd:element name="Thing"><xsd:complexType><xsd:complexContent><xsd:restriction base="Thing_VersionStructure"/>'
          '</xsd:complexContent></xsd:complexType></xsd:element>')


def with_group(members, extra=""):
    """A schema with group G holding `members`, used by the entity H, plus `extra` declarations."""
    return (extra + '<xsd:group name="G"><xsd:sequence>%s</xsd:sequence></xsd:group>' % members +
            '<xsd:complexType name="H_VersionStructure"><xsd:sequence><xsd:group ref="G"/></xsd:sequence></xsd:complexType>'
            '<xsd:element name="H"><xsd:complexType><xsd:complexContent><xsd:restriction base="H_VersionStructure"/>'
            '</xsd:complexContent></xsd:complexType></xsd:element>')


def run(body, mapper=Mapper):
    return mapper(inline_model(body)).run()


REF = ('<xsd:element name="%(n)sRef" type="%(n)sRefStructure"/><xsd:complexType name="%(n)sRefStructure">'
       '<xsd:simpleContent><xsd:restriction base="RefBase"><xsd:attribute name="ref" type="%(t)s" use="required"/>'
       '</xsd:restriction></xsd:simpleContent></xsd:complexType>'
       '<xsd:complexType name="RefBase"><xsd:simpleContent><xsd:extension base="xsd:normalizedString">'
       '<xsd:attribute name="ref" type="xsd:normalizedString"/></xsd:extension></xsd:simpleContent></xsd:complexType>')


def idclass(n, t):
    return ('<xsd:element name="%s"><xsd:complexType><xsd:attribute name="id" type="%s"/></xsd:complexType></xsd:element>'
            % (n, t))


def refstruct(n, base, t, default=None):
    return ('<xsd:complexType name="%sRefStructure"><xsd:simpleContent><xsd:restriction base="%s">'
            '<xsd:attribute name="nameOfRefClass" type="xsd:normalizedString"%s/>'
            '<xsd:attribute name="ref" type="%s" use="required"/></xsd:restriction></xsd:simpleContent></xsd:complexType>'
            '<xsd:element name="%sRef" type="%sRefStructure"/>'
            % (n, base, ' default="%s"' % default if default else "", t, n, n))


ZONES = (idclass("GroupOfPoints", "GroupOfPointsIdType") + idclass("Zone", "ZoneIdType") +
         '<xsd:complexType name="RefBase"><xsd:simpleContent><xsd:extension base="xsd:normalizedString">'
         '<xsd:attribute name="ref" type="xsd:normalizedString"/></xsd:extension></xsd:simpleContent></xsd:complexType>' +
         refstruct("GroupOfPoints", "RefBase", "GroupOfPointsIdType", "GroupOfPoints") +
         refstruct("Zone", "GroupOfPointsRefStructure", "GroupOfPointsIdType", "Zone"))
PLACES = (idclass("Place", "PlaceBaseIdType") + idclass("Garage", "PlaceIdType") +
          '<xsd:complexType name="RefBase"><xsd:simpleContent><xsd:extension base="xsd:normalizedString">'
          '<xsd:attribute name="ref" type="xsd:normalizedString"/></xsd:extension></xsd:simpleContent></xsd:complexType>' +
          refstruct("Place", "RefBase", "PlaceIdType"))
INHERITED = (idclass("Thing", "ThingIdType") +
             '<xsd:complexType name="ThingRefStructure"><xsd:simpleContent><xsd:extension base="xsd:normalizedString">'
             '<xsd:attribute name="ref" type="ThingIdType"/></xsd:extension></xsd:simpleContent></xsd:complexType>'
             '<xsd:complexType name="SubRefStructure"><xsd:simpleContent><xsd:restriction base="ThingRefStructure"/>'
             '</xsd:simpleContent></xsd:complexType><xsd:element name="SubRef" type="SubRefStructure"/>')


class RuleTest(unittest.TestCase):
    def test_folded_class_takes_the_type_documentation_when_the_element_has_none(self):
        t = run('<xsd:complexType name="Thing_VersionStructure"><xsd:annotation><xsd:documentation>From the type.'
                '</xsd:documentation></xsd:annotation></xsd:complexType>'
                '<xsd:element name="Thing"><xsd:complexType><xsd:complexContent>'
                '<xsd:restriction base="Thing_VersionStructure"/></xsd:complexContent></xsd:complexType></xsd:element>')
        self.assertEqual(objects(t, iri("Thing"), RDFS.comment), {Literal("From the type.", lang="en")})

    def test_reference_site_documentation_wins_over_the_referenced_element(self):
        extra = (ENTITY.replace('<xsd:element name="Thing">', '<xsd:element name="Thing"><xsd:annotation>'
                 '<xsd:documentation>Global.</xsd:documentation></xsd:annotation>') +
                 '<xsd:element name="Other" type="xsd:string"><xsd:annotation><xsd:documentation>Other global.'
                 '</xsd:documentation></xsd:annotation></xsd:element>')
        t = run(with_group('<xsd:element ref="Thing"><xsd:annotation><xsd:documentation>Local.'
                           '</xsd:documentation></xsd:annotation></xsd:element><xsd:element ref="Other"/>', extra))
        self.assertEqual(objects(t, iri("G.Thing"), RDFS.comment), {Literal("Local.", lang="en")})
        self.assertEqual(objects(t, iri("G.Other"), RDFS.comment), {Literal("Other global.", lang="en")})
        self.assertEqual(objects(t, iri("G.Other"), RDFS.range), {XSD.string})

    def test_ref_falls_back_to_the_name_without_ref_when_no_class_has_the_id_type(self):
        t = run(with_group('<xsd:element ref="ThingRef"/>', ENTITY + REF % {"n": "Thing", "t": "xsd:normalizedString"}))
        self.assertEqual(objects(t, iri("G.ThingRef"), RDFS.range), {iri("Thing")})

    def test_ref_default_name_of_ref_class_wins_over_the_inherited_id_type(self):
        # ZoneRef restricts GroupOfPointsRef and redeclares ref with the base's IdType
        t = run(with_group('<xsd:element ref="ZoneRef"/>', ZONES))
        self.assertEqual(objects(t, iri("G.ZoneRef"), RDFS.range), {iri("Zone")})

    def test_ref_stem_class_wins_over_the_id_type_owner(self):
        # Garage is the only class whose id has PlaceIdType, but PlaceRef points to Place
        t = run(with_group('<xsd:element ref="PlaceRef"/>', PLACES))
        self.assertEqual(objects(t, iri("G.PlaceRef"), RDFS.range), {iri("Place")})

    def test_inherited_ref_attribute_does_not_resolve_the_target(self):
        # SubRef inherits ref (and its IdType) from ThingRef; no default, no class Sub: the build fails
        with self.assertRaises(UnsupportedSchema):
            run(with_group('<xsd:element ref="SubRef"/>', INHERITED))

    def test_unresolvable_ref_target_fails_the_build(self):
        with self.assertRaises(UnsupportedSchema):
            run(with_group('<xsd:element ref="NoSuchRef"/>', REF % {"n": "NoSuch", "t": "xsd:normalizedString"}))

    def test_element_without_type_is_refused(self):
        with self.assertRaises(UnsupportedSchema):
            run(with_group('<xsd:element name="x"/>'))

    def test_attribute_ref_is_refused(self):
        with self.assertRaises(UnsupportedSchema):
            run('<xsd:complexType name="T"><xsd:attribute ref="other:x"/></xsd:complexType>')

    def test_known_reference_type_without_a_target_class_gets_a_note(self):
        class Known(Mapper):
            UNRESOLVED_REFS = frozenset(["NoSuchRefStructure"])

        t = run(with_group('<xsd:element ref="NoSuchRef"/>', REF % {"n": "NoSuch", "t": "xsd:normalizedString"}), Known)
        p = iri("G.NoSuchRef")
        self.assertEqual(objects(t, p, RDF.type), {OWL.ObjectProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(t, p, RDFS.range), set())
        self.assertEqual(objects(t, p, skos("scopeNote")), {Literal(
            "Reference type NoSuchRefStructure: no target class is defined in the schema.", lang="en")})

    def test_xsd_any_type_is_a_literal_with_a_note(self):
        t = run(with_group('<xsd:element name="Value" type="xsd:anyType"/>'))
        p = iri("G.Value")
        self.assertEqual(objects(t, p, RDF.type), {OWL.DatatypeProperty, OWL.FunctionalProperty})
        self.assertEqual(objects(t, p, RDFS.range), {RDFS.Literal})
        self.assertEqual(objects(t, p, skos("scopeNote")), {Literal("xsd:anyType in the XSD: any content.", lang="en")})

    def test_attribute_without_a_type_is_any_simple_type(self):
        t = run('<xsd:complexType name="T"><xsd:attribute name="order"/></xsd:complexType>')
        self.assertEqual(objects(t, iri("T.order"), RDFS.range), {URIRef(str(XSD) + "anySimpleType")})

    def test_reference_element_with_an_extension_of_a_reference_type_is_not_a_class(self):
        extra = (ENTITY + REF % {"n": "Thing", "t": "xsd:normalizedString"} +
                 '<xsd:element name="OtherRef"><xsd:complexType><xsd:complexContent>'
                 '<xsd:extension base="ThingRefStructure"/></xsd:complexContent></xsd:complexType></xsd:element>')
        t = run(with_group('<xsd:element ref="OtherRef"/>', extra))
        self.assertNotIn(iri("OtherRef"), subjects(t))
        self.assertEqual(objects(t, iri("G.OtherRef"), RDFS.range), {iri("Thing")})

    def test_local_element_with_simple_content_extending_a_reference_is_not_a_class(self):
        extra = ENTITY + REF % {"n": "Thing", "t": "xsd:normalizedString"}
        t = run(with_group('<xsd:element name="Inline"><xsd:complexType><xsd:simpleContent>'
                           '<xsd:extension base="ThingRefStructure"/></xsd:simpleContent></xsd:complexType></xsd:element>',
                           extra))
        self.assertNotIn(iri("GInline"), subjects(t))
        self.assertEqual(objects(t, iri("G.Inline"), RDFS.range), {iri("Thing")})

    def test_inline_member_of_a_relationship_type_counts_as_the_class_it_derives_from(self):
        extra = (ENTITY + '<xsd:complexType name="containmentAggregationStructure"/>'
                 '<xsd:complexType name="things_RelStructure"><xsd:complexContent>'
                 '<xsd:extension base="containmentAggregationStructure"><xsd:choice maxOccurs="unbounded">'
                 '<xsd:element name="Inline"><xsd:complexType><xsd:complexContent>'
                 '<xsd:restriction base="Thing_VersionStructure"/></xsd:complexContent></xsd:complexType></xsd:element>'
                 '</xsd:choice></xsd:extension></xsd:complexContent></xsd:complexType>')
        t = run(with_group('<xsd:element name="things" type="things_RelStructure"/>', extra))
        self.assertEqual(objects(t, iri("G.things"), RDFS.range), {iri("Thing")})

    def test_generated_anonymous_class_name_colliding_with_a_type_is_refused(self):
        with self.assertRaises(NameCollision):
            run('<xsd:group name="A"><xsd:sequence><xsd:element name="Dimensions"><xsd:complexType><xsd:sequence/>'
                '</xsd:complexType></xsd:element></xsd:sequence></xsd:group>'
                '<xsd:complexType name="T"><xsd:sequence><xsd:group ref="A"/></xsd:sequence></xsd:complexType>'
                '<xsd:complexType name="ADimensions"><xsd:sequence/></xsd:complexType>')

    def test_same_name_for_an_element_and_an_attribute_of_one_declaration_is_refused(self):
        with self.assertRaises(NameCollision):
            run('<xsd:complexType name="T"><xsd:sequence><xsd:element name="x" type="xsd:string"/></xsd:sequence>'
                '<xsd:attribute name="x" type="xsd:string"/></xsd:complexType>')


# ---------------------------------------------------------------- root, invariants, output

class OutputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triples = build_triples(fixture_model())

    def test_root_ontology(self):
        root = URIRef(NS)
        self.assertEqual(objects(self.triples, root, RDF.type), {OWL.Ontology})
        self.assertEqual(objects(self.triples, root, OWL.versionInfo), {Literal("1.0.0")})
        self.assertEqual(objects(self.triples, root, OWL.priorVersion),
                         {URIRef("https://vocabulary.eona-x.eu/ontology/netex/v0.2.0#")})
        self.assertEqual(objects(self.triples, root, RDFS.label), {Literal("NeTEx 2.0 (CEN/TS 16614)", lang="en")})
        self.assertEqual(objects(self.triples, root, URIRef(DCT + "license")),
                         {URIRef("http://spdx.org/licenses/GPL-3.0-only")})
        (rights,) = objects(self.triples, root, URIRef(DCT + "rights"))
        self.assertIn("CEN, Crown Copyright 2009-2026", str(rights))
        self.assertEqual(objects(self.triples, root, URIRef(DCT + "source")), {URIRef(
            "https://github.com/TransmodelEcosystem/NeTEx/tree/%s/xsd" % netex_owl.COMMIT)})
        (comment,) = objects(self.triples, root, RDFS.comment)
        self.assertIn(netex_owl.COMMIT, str(comment))
        self.assertEqual(objects(self.triples, root, OWL.imports), set())

    def test_invariants_accept_the_output_and_reject_violations(self):
        check_invariants(self.triples)
        with self.assertRaises(AssertionError):
            check_invariants(self.triples | {(URIRef("https://example.org/x"), RDF.type, OWL.Class)})
        with self.assertRaises(AssertionError):
            check_invariants(self.triples - {(URIRef(NS), RDF.type, OWL.Ontology)})
        with self.assertRaises(AssertionError):
            check_invariants(self.triples | {(iri("Parking"), RDFS.seeAlso,
                                              URIRef("https://eona-x.eu/ontology/other/v1#X"))})

    def test_output_is_deterministic_in_process(self):
        self.assertEqual(to_turtle(FIXTURE_XSD), to_turtle(FIXTURE_XSD))

    def test_output_is_deterministic_across_hash_seeds(self):
        outs = []
        for seed in ("1", "2"):
            r = subprocess.run([sys.executable, "-B", "-I", os.path.join(ROOT, "run.py"), "netexgen.netex_owl",
                                "--xsd-dir", FIXTURE_XSD, "--out", "-"],
                               capture_output=True, text=True, env={"PYTHONHASHSEED": seed}, check=True)
            outs.append(r.stdout)
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[0], to_turtle(FIXTURE_XSD))

    def test_header_states_licence_and_copyright(self):
        head = to_turtle(FIXTURE_XSD, lenient_alignment=True).split("\n\n")[0]
        self.assertIn("GPL-3.0-only", head)
        self.assertIn("Copyright CEN, Crown Copyright 2009-2026", head)

    def test_golden_file(self):
        with open(os.path.join(HERE, "golden", "netex-mini.ttl"), encoding="utf-8") as f:
            self.assertEqual(to_turtle(FIXTURE_XSD), f.read())

    def test_output_parses_as_turtle_with_the_expected_triple_count(self):
        g = Graph().parse(data=to_turtle(FIXTURE_XSD), format="turtle")
        self.assertGreater(len(g), 300)
        self.assertIn((iri("Parking"), RDFS.subClassOf, iri("Parking_VersionStructure")), g)

    def test_cli_writes_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.ttl")
            subprocess.run([sys.executable, "-B", "-I", os.path.join(ROOT, "run.py"), "netexgen.netex_owl",
                            "--xsd-dir", FIXTURE_XSD, "--out", out], check=True)
            with open(out, encoding="utf-8") as f:
                self.assertEqual(f.read(), to_turtle(FIXTURE_XSD))


if __name__ == "__main__":
    unittest.main()
