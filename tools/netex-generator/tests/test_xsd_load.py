import os
import tempfile
import unittest

from netexgen.xsd_load import (ClosureError, UnsupportedSchema, documentation, load, walk_complex,
                               walk_group, NETEX, SIRI, GML)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "netex", "xsd")
SCHEMA = ('<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://www.netex.org.uk/netex" '
          'targetNamespace="http://www.netex.org.uk/netex">%s</xsd:schema>')


def tmp_model(body, extra=None):
    d = tempfile.TemporaryDirectory()
    with open(os.path.join(d.name, "a.xsd"), "w", encoding="utf-8") as f:
        f.write(SCHEMA % body)
    for rel, text in (extra or {}).items():
        with open(os.path.join(d.name, rel), "w", encoding="utf-8") as f:
            f.write(text)
    return d, lambda: load(d.name, "a.xsd")


class SymbolTableTest(unittest.TestCase):
    def setUp(self):
        self.m = load(FIXTURE, "NeTEx_publication.xsd")

    def test_components_are_keyed_by_namespace_and_name(self):
        for ns in (NETEX, SIRI, GML):
            self.assertIsNotNone(self.m.find("element", ns, "Point"), ns)
        files = {self.m.find("element", ns, "Point").file for ns in (NETEX, SIRI, GML)}
        self.assertEqual(len(files), 3)

    def test_namespaces_of_the_files(self):
        self.assertEqual(self.m.schemas["gml/gml_base.xsd"].ns, GML)
        self.assertEqual(self.m.schemas["siri/siri_base.xsd"].ns, SIRI)

    def test_qname_uses_the_prefixes_of_the_declaring_file(self):
        c = self.m.find("group", NETEX, "VehicleChargingEquipmentGroup")
        self.assertEqual(self.m.qname(c.file, "xsd:string"), ("http://www.w3.org/2001/XMLSchema", "string"))
        self.assertEqual(self.m.qname(c.file, "gml:Point"), (GML, "Point"))
        self.assertEqual(self.m.qname(c.file, "PlugTypeEnumeration"), (NETEX, "PlugTypeEnumeration"))

    def test_unknown_prefix_is_refused(self):
        with self.assertRaises(UnsupportedSchema):
            self.m.qname("NeTEx_publication.xsd", "nope:x")

    def test_documentation_collapses_whitespace(self):
        c = self.m.find("element", NETEX, "VehicleChargingEquipment")
        self.assertEqual(documentation(c.node), "Specialisation of PLACE EQUIPMENT for vehicle charging. +v2.0")
        c = self.m.find("type", NETEX, "WattageType")
        self.assertEqual(documentation(c.node), "Power in watts.")

    def test_appinfo_is_not_documentation(self):
        self.assertIsNone(documentation(self.m.schemas["NeTEx_publication.xsd"].root))

    def test_two_documentation_elements_are_joined_by_a_blank_line(self):
        d, mk = tmp_model('<xsd:element name="E" type="xsd:string"><xsd:annotation>'
                          '<xsd:documentation>one</xsd:documentation><xsd:documentation>two</xsd:documentation>'
                          '</xsd:annotation></xsd:element>')
        with d:
            self.assertEqual(documentation(mk().find("element", NETEX, "E").node), "one\n\ntwo")

    def test_duplicate_component_is_refused(self):
        d, mk = tmp_model('<xsd:element name="E" type="xsd:string"/><xsd:element name="E" type="xsd:string"/>')
        with d, self.assertRaises(UnsupportedSchema):
            mk()

    def test_unsupported_top_level_construct_is_refused(self):
        d, mk = tmp_model('<xsd:notation name="n" public="p"/>')
        with d, self.assertRaises(UnsupportedSchema):
            mk()

    def test_unreached_pinned_file_is_refused(self):
        with self.assertRaises(ClosureError):
            load(FIXTURE, "NeTEx_publication.xsd", pinned=["NeTEx_publication.xsd"])
        with self.assertRaises(ClosureError):
            load(FIXTURE, "NeTEx_publication.xsd", pinned=list(self.m.schemas) + ["siri/extra.xsd"])

    def test_pinned_set_equal_to_the_closure_loads(self):
        load(FIXTURE, "NeTEx_publication.xsd", pinned=list(self.m.schemas))


def occ(items):
    return [(o.kind, o.node.get("name") or o.node.get("ref"), o.decl, o.optional, o.repeating, o.choice)
            for o in items]


class WalkTest(unittest.TestCase):
    def setUp(self):
        self.m = load(FIXTURE, "NeTEx_publication.xsd")

    def test_group_flattening_is_transitive(self):
        body = ('<xsd:group name="Outer"><xsd:sequence><xsd:element name="a" type="xsd:string"/>'
                '<xsd:group ref="Inner" minOccurs="0"/></xsd:sequence></xsd:group>'
                '<xsd:group name="Inner"><xsd:sequence><xsd:element name="b" type="xsd:string"/>'
                '</xsd:sequence></xsd:group>')
        d, mk = tmp_model(body)
        with d:
            m = mk()
            got = occ(walk_group(m, m.find("group", NETEX, "Outer")))
        self.assertEqual(got, [("element", "a", "Outer", False, False, False),
                               ("element", "b", "Inner", True, False, False)])

    def test_choice_and_repeating_flags(self):
        got = occ(walk_group(self.m, self.m.find("group", NETEX, "VehicleChargingEquipmentGroup")))
        flags = {name: (opt, rep, ch) for _, name, _, opt, rep, ch in got}
        self.assertEqual(flags["MaximumPower"], (False, False, False))
        self.assertEqual(flags["FreeRecharging"], (True, False, False))
        self.assertEqual(flags["ChoiceA"], (False, False, True))
        self.assertEqual(flags["Tag"], (False, True, False))
        self.assertEqual(flags["Alias"], (True, True, False))

    def test_restriction_content_is_skipped_and_extension_content_is_walked(self):
        e = self.m.find("element", NETEX, "VehicleChargingEquipment")
        self.assertEqual(list(walk_complex(self.m, e.node.find(
            "{http://www.w3.org/2001/XMLSchema}complexType"), e.file, "VehicleChargingEquipment")), [])
        t = self.m.find("type", NETEX, "VehicleChargingEquipment_VersionStructure")
        names = [o.node.get("name") or o.node.get("ref") for o in walk_complex(self.m, t.node, t.file, t.name)]
        self.assertIn("MaximumPower", names)
        self.assertNotIn("Name", names)  # inherited from the base, not repeated here

    def test_attribute_groups_are_flattened(self):
        t = self.m.find("type", NETEX, "EntityInVersionStructure")
        got = occ(walk_complex(self.m, t.node, t.file, t.name))
        self.assertEqual([(k, n, d) for k, n, d, *_ in got],
                         [("attribute", "created", "BasicModificationDetailsGroup"),
                          ("attribute", "version", "BasicModificationDetailsGroup")])

    def test_xsd_any_is_reported_as_dropped(self):
        t = self.m.find("type", NETEX, "ExtensionsStructure")
        self.assertEqual([o.kind for o in walk_complex(self.m, t.node, t.file, t.name)], ["any"])

    def test_group_cycle_is_refused(self):
        d, mk = tmp_model('<xsd:group name="G"><xsd:sequence><xsd:group ref="G"/></xsd:sequence></xsd:group>')
        with d:
            m = mk()
            with self.assertRaises(UnsupportedSchema):
                list(walk_group(m, m.find("group", NETEX, "G")))

    def test_unknown_particle_is_refused(self):
        d, mk = tmp_model('<xsd:group name="G"><xsd:all><xsd:element name="a" type="xsd:string"/></xsd:all></xsd:group>')
        with d:
            m = mk()
            with self.assertRaises(UnsupportedSchema):
                list(walk_group(m, m.find("group", NETEX, "G")))


if __name__ == "__main__":
    unittest.main()
