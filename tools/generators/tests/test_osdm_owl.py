import json
import os
import random
import tempfile
import unittest

import yaml
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from eonagen import osdm_owl as o
from eonagen.turtle import Anon

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "fixtures", "osdm", "specification")
GOLDEN = os.path.join(HERE, "golden", "osdm-mini.ttl")
SKOS = "http://www.w3.org/2004/02/skos/core#"
NS = o.NS


def u(n):
    return URIRef(NS + n)


def sk(n):
    return URIRef(SKOS + n)


def graph():
    g = Graph()
    for t in o.build_triples(SPEC)[0]:
        s, p, ob = t
        if isinstance(ob, Anon):
            from rdflib import BNode
            b = BNode()
            g.add((s, p, b))
            for pp, oo in ob.pairs:
                g.add((b, pp, oo))
        else:
            g.add(t)
    return g


def write_spec(tmp, online=None, offline=None, extra_files=None):
    """Minimal spec dir; online maps Name -> body in schemas/a.yml."""
    os.makedirs(os.path.join(tmp, "schemas"), exist_ok=True)
    online = online or {}
    api = {"openapi": "3.0.3", "paths": {}, "components": {"schemas": {
        n: {"$ref": "./schemas/a.yml#/" + n} for n in online}}}
    with open(os.path.join(tmp, "OSDM-online-api.yml"), "w") as f:
        yaml.safe_dump(api, f)
    with open(os.path.join(tmp, "schemas", "a.yml"), "w") as f:
        yaml.safe_dump(online, f)
    for rel, content in (extra_files or {}).items():
        os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
        with open(os.path.join(tmp, rel), "w") as f:
            yaml.safe_dump(content, f)
    with open(os.path.join(tmp, "OSDM-offline-model.json"), "w") as f:
        json.dump({"definitions": offline or {}}, f)
    return tmp


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = graph()

    def has(self, s, p, ob):
        self.assertIn((s, p, ob), self.g)

    def restriction_props(self, cls):
        out = set()
        for r in self.g.objects(cls, RDFS.subClassOf):
            if (r, RDF.type, OWL.Restriction) in self.g:
                self.assertEqual(self.g.value(r, OWL.minCardinality), Literal(1, datatype=XSD.nonNegativeInteger))
                out.add(self.g.value(r, OWL.onProperty))
        return out


class MappingRows(Fixture):
    def test_class(self):
        a = u("Animal")
        self.has(a, RDF.type, OWL.Class)
        self.has(a, RDFS.label, Literal("Animal"))
        self.has(a, RDFS.comment, Literal("An animal.", lang="en"))
        self.has(a, RDFS.isDefinedBy, URIRef(NS))
        self.assertTrue(str(self.g.value(a, URIRef(o.DCTERMS + "source"))).endswith("/specification/schemas/a.yml"))

    def test_allof_subclass_and_inline_properties(self):
        self.has(u("Dog"), RDFS.subClassOf, u("Animal"))
        self.has(u("Dog.bark"), RDFS.domain, u("Dog"))
        self.has(u("Dog.bark"), RDFS.range, XSD.boolean)
        self.has(u("Dog"), RDFS.comment, Literal("A dog.", lang="en"))

    def test_discriminator_scope_note(self):
        self.has(u("Animal"), sk("scopeNote"), Literal("Discriminator property: objectType.", lang="en"))
        self.has(u("Animal.objectType"), RDF.type, OWL.DatatypeProperty)

    def test_property_iri_label_notation_domain(self):
        p = u("Animal.name")
        self.has(p, RDFS.label, Literal("name"))
        self.has(p, sk("notation"), Literal("name"))
        self.has(p, RDFS.domain, u("Animal"))
        self.has(p, RDFS.comment, Literal("The name.", lang="en"))

    def test_datatype_properties_and_formats(self):
        for pname, dt in (("name", XSD.string), ("legs", XSD.int), ("born", XSD.dateTime)):
            p = u("Animal." + pname)
            self.has(p, RDF.type, OWL.DatatypeProperty)
            self.has(p, RDFS.range, dt)
        self.has(u("Person.site"), RDFS.range, XSD.anyURI)
        self.has(u("Link.href"), RDFS.range, XSD.anyURI)

    def test_ref_to_class_is_object_property(self):
        p = u("Animal.owner")
        self.has(p, RDF.type, OWL.ObjectProperty)
        self.has(p, RDFS.range, u("Person"))

    def test_named_primitive_is_datatype(self):
        p = u("Animal.size")
        self.has(p, RDF.type, OWL.DatatypeProperty)
        self.has(p, RDFS.range, u("Size"))
        self.has(u("Size"), RDF.type, RDFS.Datatype)
        eq = self.g.value(u("Size"), OWL.equivalentClass)
        self.has(eq, OWL.onDatatype, XSD.double)
        self.has(u("Size"), RDFS.comment, Literal("A size.", lang="en"))
        # sibling description on a $ref property
        self.has(u("Animal.age"), RDFS.comment, Literal("Age in years.", lang="en"))
        self.has(u("Animal.age"), RDFS.range, u("Count"))

    def test_array_is_not_functional(self):
        self.assertNotIn((u("Animal.tags"), RDF.type, OWL.FunctionalProperty), self.g)
        self.has(u("Animal.tags"), RDFS.range, XSD.string)
        self.has(u("Animal.name"), RDF.type, OWL.FunctionalProperty)

    def test_functional_only_when_required_and_not_array(self):
        F = OWL.FunctionalProperty
        for n in ("Animal.name", "Animal.objectType", "Dog.bark", "Note.text"):
            self.has(u(n), RDF.type, F)
        for n in ("Animal.legs", "Animal.born", "Animal.owner", "Animal.tags", "Note.tags", "Dog.bark.x"):
            self.assertNotIn((u(n), RDF.type, F), self.g)
        # the parent's property stays non-functional when only a subclass requires it
        with tempfile.TemporaryDirectory() as t:
            write_spec(t, online={
                "P": {"type": "object", "properties": {"a": {"type": "string"}}},
                "C": {"allOf": [{"$ref": "#/P"}, {"type": "object", "required": ["a", "l"],
                                                  "properties": {"l": {"type": "array", "items": {"type": "string"}}}}]}})
            g = Graph()
            for s, p, ob in o.build_triples(t)[0]:
                if not isinstance(ob, Anon):
                    g.add((s, p, ob))
            self.assertNotIn((u("P.a"), RDF.type, OWL.FunctionalProperty), g)
            self.assertNotIn((u("C.l"), RDF.type, OWL.FunctionalProperty), g)

    def test_deprecated_maps_to_owl_deprecated(self):
        true = Literal(True)
        for n in ("Animal.legs", "Animal.owner", "Person", "MediaType"):
            self.has(u(n), OWL.deprecated, true)
        self.assertEqual(list(self.g.objects(u("Person"), OWL.deprecated))[0].datatype, XSD.boolean)
        for n in ("Animal.name", "Animal", "Color"):
            self.assertNotIn((u(n), OWL.deprecated, None), self.g)
        self.assertIn("owl:deprecated \"true\"^^xsd:boolean", o.to_turtle(SPEC))

    def test_deprecated_false_is_not_emitted(self):
        with tempfile.TemporaryDirectory() as t:
            write_spec(t, online={"A": {"type": "object", "deprecated": False,
                                        "properties": {"p": {"type": "string", "deprecated": False}}}})
            self.assertNotIn(OWL.deprecated, {p for s, p, ob in o.build_triples(t)[0]})

    def test_deprecated_on_allof_members_and_named_arrays(self):
        with tempfile.TemporaryDirectory() as t:
            write_spec(t, online={
                "P": {"type": "object", "properties": {"a": {"type": "string"}}},
                "L": {"type": "array", "deprecated": True, "items": {"$ref": "#/P"}},
                "C": {"allOf": [{"$ref": "#/P"}, {"type": "object", "deprecated": True,
                                                  "properties": {"y": {"allOf": [{"$ref": "#/P"}, {"deprecated": True}]},
                                                                 "z": {"$ref": "#/L"},
                                                                 "w": {"type": "array", "items": {"allOf": [{"$ref": "#/P"}, {"deprecated": True}]}},
                                                                 "v": {"$ref": "#/P"}}}]}})
            g = Graph()
            for s, p, ob in o.build_triples(t)[0]:
                if not isinstance(ob, Anon):
                    g.add((s, p, ob))
            for n in ("C", "C.y", "C.z", "C.w"):
                self.assertIn((u(n), OWL.deprecated, Literal(True)), g, n)
            self.assertNotIn((u("C.v"), OWL.deprecated, None), g)
            self.assertNotIn((u("P"), OWL.deprecated, None), g)

    def test_named_array_unwrapped_to_items(self):
        self.has(u("Animal.links"), RDFS.range, u("Link"))
        self.assertNotIn((u("LinkList"), RDF.type, None), self.g)
        self.assertNotIn((u("Animal.links"), RDF.type, OWL.FunctionalProperty), self.g)

    def test_ojp_only_reachable_definition(self):
        self.has(u("Link"), RDF.type, OWL.Class)

    def test_named_enum(self):
        c = u("Color")
        self.has(c, RDF.type, OWL.Class)
        self.has(c, RDF.type, sk("ConceptScheme"))
        red = URIRef(str(c) + "/RED")
        self.has(red, RDF.type, sk("Concept"))
        self.has(red, RDF.type, c)
        self.has(red, sk("inScheme"), c)
        self.has(red, sk("notation"), Literal("RED"))
        self.has(red, sk("prefLabel"), Literal("RED"))
        self.assertEqual(list(self.g.objects(c, sk("scopeNote"))), [])
        self.has(u("Animal.color"), RDF.type, OWL.ObjectProperty)
        self.has(u("Animal.color"), RDFS.range, c)

    def test_extensible_enum_with_definitions_and_pct_iri(self):
        m = u("MediaType")
        self.has(m, sk("scopeNote"), Literal("Extensible list: other values may occur.", lang="en"))
        pdf = URIRef(str(m) + "/application%2Fpdf")
        self.has(pdf, sk("notation"), Literal("application/pdf"))
        self.has(pdf, sk("definition"), Literal("A PDF document", lang="en"))
        self.has(URIRef(str(m) + "/PLAIN"), sk("notation"), Literal("PLAIN"))

    def test_inline_enum_on_property(self):
        s = u("AnimalStatus")
        self.has(s, RDF.type, sk("ConceptScheme"))
        self.has(u("Animal.status"), RDFS.range, s)
        self.has(URIRef(str(s) + "/ALIVE"), sk("inScheme"), s)
        self.has(s, sk("scopeNote"), Literal("Extensible list: other values may occur.", lang="en"))
        self.has(u("RootDef.unit"), RDFS.range, u("RootDefUnit"))

    def test_inline_object_on_property(self):
        c = u("RootDefDetail")
        self.has(c, RDF.type, OWL.Class)
        self.has(u("RootDef.detail"), RDF.type, OWL.ObjectProperty)
        self.has(u("RootDef.detail"), RDFS.range, c)
        self.has(u("RootDefDetail.x"), RDFS.domain, c)
        self.assertIn(u("RootDefDetail.x"), self.restriction_props(c))

    def test_required_restrictions_and_inherited(self):
        self.assertEqual(self.restriction_props(u("Animal")), {u("Animal.objectType"), u("Animal.name")})
        self.assertEqual(self.restriction_props(u("Dog")), {u("Dog.bark")})

    def test_example(self):
        self.has(u("Animal.name"), sk("example"), Literal("Rex"))

    def test_allof_property_range_and_description(self):
        self.has(u("Animal.mate"), RDFS.range, u("Animal"))
        self.has(u("Animal.mate"), RDFS.comment, Literal("The mate.", lang="en"))

    def test_dropped_keywords_leave_no_trace(self):
        text = o.to_turtle(SPEC)
        self.assertNotIn("maxLength", text)
        self.assertNotIn("nullable", text)

    def test_root_wrapper_not_minted(self):
        self.assertNotIn((u("fareDelivery"), None, None), self.g)
        self.has(u("RootDef"), RDF.type, OWL.Class)

    def test_named_primitive_offline(self):
        self.has(u("IdDef"), RDF.type, RDFS.Datatype)
        self.has(u("RootDef.ids"), RDFS.range, u("IdDef"))


class Collisions(Fixture):
    def test_equal_definitions_merge_with_both_sources(self):
        sources = {str(x) for x in self.g.objects(u("Shared"), URIRef(o.DCTERMS + "source"))}
        self.assertEqual(len(sources), 2)
        self.assertTrue(any(s.endswith("schemas/a.yml") for s in sources))
        self.assertTrue(any(s.endswith("OSDM-offline-model.json") for s in sources))
        self.assertEqual(len(list(self.g.objects(u("Shared"), RDFS.label))), 1)
        self.assertNotIn((u("OfflineShared"), RDF.type, None), self.g)
        self.has(u("RootDef.shared"), RDFS.range, u("Shared"))

    def test_annotation_only_differences_merge(self):
        n = u("Note")
        comments = {str(x) for x in self.g.objects(n, RDFS.comment)}
        self.assertEqual(comments, {"Online note.", "Offline note."})
        self.assertEqual({str(x) for x in self.g.objects(n, sk("example"))}, {"online example", "offline example"})
        self.assertEqual(len(list(self.g.objects(n, URIRef(o.DCTERMS + "source")))), 2)
        t = u("Note.text")
        self.assertEqual({str(x) for x in self.g.objects(t, RDFS.comment)}, {"Online text.", "Offline text."})
        self.assertEqual({str(x) for x in self.g.objects(t, sk("example"))}, {"online-text", "offline-text"})
        self.assertNotIn((u("OfflineNote"), RDF.type, None), self.g)
        self.has(u("RootDef.note"), RDFS.range, n)

    def test_deprecated_difference_is_structural(self):
        self.has(u("OfflineOldDiff"), RDFS.seeAlso, u("OldDiff"))
        self.has(u("OldDiff.code"), OWL.deprecated, Literal(True))
        self.assertNotIn((u("OfflineOldDiff.code"), OWL.deprecated, None), self.g)
        self.has(u("RootDef.olddiff"), RDFS.range, u("OfflineOldDiff"))

    def test_different_definitions_get_offline_prefix_and_seealso(self):
        self.has(u("Diff.code"), RDFS.range, XSD.string)
        self.has(u("OfflineDiff"), RDF.type, OWL.Class)
        self.has(u("OfflineDiff"), RDFS.seeAlso, u("Diff"))
        self.has(u("OfflineDiff.code"), RDFS.range, XSD.integer)
        self.has(u("RootDef.diff"), RDFS.range, u("OfflineDiff"))

    def test_offline_prefix_taken_raises(self):
        with tempfile.TemporaryDirectory() as t:
            write_spec(t, online={"D": {"type": "object", "properties": {"a": {"type": "string"}}},
                                  "OfflineD": {"type": "object"}},
                       offline={"D": {"type": "object", "properties": {"a": {"type": "integer"}}}})
            with self.assertRaises(o.NameCollision):
                o.build_triples(t)

    def test_duplicate_name_across_online_files(self):
        with tempfile.TemporaryDirectory() as t:
            write_spec(t, online={"X": {"type": "object", "properties": {"b": {"$ref": "./other.yml#/X"}}}},
                       extra_files={"schemas/other.yml": {"X": {"type": "object"}}})
            with self.assertRaises(o.NameCollision):
                o.build_triples(t)


class Negative(unittest.TestCase):
    def run_online(self, defs):
        with tempfile.TemporaryDirectory() as t:
            write_spec(t, online=defs)
            return o.build_triples(t)

    def test_oneof_anyof_not_patternproperties(self):
        for kw in ("oneOf", "anyOf", "not", "patternProperties"):
            with self.subTest(kw):
                with self.assertRaises(o.UnsupportedSchema):
                    self.run_online({"A": {"type": "object", "properties": {"p": {kw: [{"type": "string"}]}}}})

    def test_unsupported_on_definition(self):
        with self.assertRaises(o.UnsupportedSchema):
            self.run_online({"A": {"oneOf": [{"type": "object"}]}})

    def test_additional_properties_schema_and_type_list(self):
        with self.assertRaises(o.UnsupportedSchema):
            self.run_online({"A": {"type": "object", "additionalProperties": {"type": "string"}}})
        with self.assertRaises(o.UnsupportedSchema):
            self.run_online({"A": {"type": "object", "properties": {"p": {"type": ["string", "null"]}}}})

    def test_unresolved_ref(self):
        with self.assertRaises(o.UnsupportedSchema):
            self.run_online({"A": {"type": "object", "properties": {"p": {"$ref": "#/Missing"}}}})

    def test_unknown_format(self):
        with self.assertRaises(o.UnsupportedSchema):
            self.run_online({"A": {"type": "object", "properties": {"p": {"type": "string", "format": "uuid"}}}})

    def test_inline_enum_collision(self):
        with self.assertRaises(o.NameCollision):
            self.run_online({"AP": {"type": "string", "enum": ["X"]},
                             "A": {"type": "object", "properties": {"p": {"type": "string", "enum": ["Y"]}}}})

    def test_unknown_keyword(self):
        with self.assertRaises(o.UnsupportedSchema):
            self.run_online({"A": {"type": "object", "properties": {"p": {"type": "string", "frobnicate": 1}}}})

    def test_required_property_not_defined(self):
        with self.assertRaises(o.UnsupportedSchema):
            self.run_online({"A": {"type": "object", "required": ["nope"], "properties": {"p": {"type": "string"}}}})


class Output(Fixture):
    def test_invariants(self):
        triples = o.build_triples(SPEC)[0]
        o.check_invariants(triples)
        for s, p, ob in triples:
            self.assertTrue(str(s).startswith(NS))
        self.assertEqual(list(self.g.subjects(RDF.type, OWL.Ontology)), [URIRef(NS)])

    def test_invariant_violation_raises(self):
        bad = {(URIRef("https://example.org/x"), RDF.type, OWL.Class), (URIRef(NS), RDF.type, OWL.Ontology)}
        with self.assertRaises(AssertionError):
            o.check_invariants(bad)

    def test_root(self):
        root = URIRef(NS)
        self.has(root, OWL.versionInfo, Literal("3.11"))
        self.assertTrue(str(self.g.value(root, URIRef(o.DCTERMS + "source"))).endswith(o.COMMIT + "/specification"))
        self.has(root, URIRef(o.DCTERMS + "license"), URIRef("https://www.apache.org/licenses/LICENSE-2.0"))
        self.assertIn("3.9.0", str(self.g.value(root, RDFS.comment)))

    def test_golden(self):
        with open(GOLDEN, encoding="utf-8") as f:
            self.assertEqual(o.to_turtle(SPEC), f.read())

    def test_parses_with_rdflib(self):
        Graph().parse(data=o.to_turtle(SPEC), format="turtle")

    def test_determinism_with_shuffled_dicts(self):
        with tempfile.TemporaryDirectory() as t:
            def shuffled(d):
                keys = list(d)
                random.Random(5).shuffle(keys)
                return {k: d[k] for k in keys}
            with open(os.path.join(SPEC, "schemas", "a.yml")) as f:
                a = yaml.safe_load(f)
            with open(os.path.join(SPEC, "OSDM-offline-model.json")) as f:
                off = json.load(f)["definitions"]
            write_spec(t, online=shuffled(a), offline=shuffled(off), extra_files={
                "schemas/ojp/b.yml": yaml.safe_load(open(os.path.join(SPEC, "schemas", "ojp", "b.yml")))})
            # same definitions, other order, other component order
            self.assertEqual(o.to_turtle(t), o.to_turtle(SPEC))


@unittest.skipUnless(os.environ.get("EONAGEN_SOURCES"), "needs the real pinned files")
class RealSmoke(unittest.TestCase):
    def test_real_spec(self):
        spec = os.path.join(os.environ["EONAGEN_SOURCES"], "specification")
        triples, renames, collisions = o.build_triples(spec)
        def count(kind):
            return len({s for s, p, ob in triples if p == RDF.type and ob == kind})

        schemes = URIRef("http://www.w3.org/2004/02/skos/core#ConceptScheme")
        concepts = URIRef("http://www.w3.org/2004/02/skos/core#Concept")
        self.assertEqual(len(collisions), 10)
        self.assertEqual(len(renames), 6)  # the other 4 merge
        self.assertEqual(count(OWL.Class), 587)  # includes the 133 schemes
        self.assertEqual(count(schemes), 133)
        self.assertEqual(count(concepts), 748)
        self.assertEqual(count(RDFS.Datatype), 26)
        self.assertEqual(count(OWL.ObjectProperty), 1147)
        self.assertEqual(count(OWL.DatatypeProperty), 1092)
        self.assertEqual(count(OWL.FunctionalProperty), 568)  # required and not an array
        deprecated = {s for s, p, ob in triples if p == OWL.deprecated}
        self.assertEqual(len(deprecated), 105)  # 104 upstream `deprecated: true` + the inline enum of one of them


if __name__ == "__main__":
    unittest.main()
