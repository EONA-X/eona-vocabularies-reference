"""RDF/OWL rendering of the NeTEx v2.0 XML Schema (publication closure).

python -I run.py netexgen.netex_owl --xsd-dir DIR --out FILE
DIR is the `xsd/` directory of the pinned NeTEx checkout. Its files are parsed as
data (xml.etree.ElementTree) and never executed. The mapping rules are documented
in netex/TERMS.md.
"""
import argparse
import sys
import urllib.parse

from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS as SKOS_NS, XSD

from netexgen import v020_alignment
from netexgen.turtle import Anon, write_turtle
from netexgen.xsd_load import (GML, NETEX, SIRI, XS, XSD_NS, UnsupportedSchema, documentation, load, local,
                               walk_complex)

NS = "https://vocabulary.eona-x.eu/ontology/netex/v1.0.0#"
VERSION = "1.0.0"
COMMIT = "11d40b5e94684fa2ddea0222702b220d7d93760b"
REPO_BLOB = "https://github.com/TransmodelEcosystem/NeTEx/blob/%s/xsd/" % COMMIT

SKOS = "http://www.w3.org/2004/02/skos/core#"
DCTERMS = "http://purl.org/dc/terms/"

XSD_BUILTINS = frozenset("""string normalizedString token language NMTOKEN NMTOKENS Name NCName ID IDREF IDREFS
    boolean decimal integer nonNegativeInteger positiveInteger negativeInteger nonPositiveInteger long int short byte
    unsignedLong unsignedInt unsignedShort unsignedByte float double duration dateTime date time gYear gYearMonth
    gMonth gMonthDay gDay anyURI base64Binary hexBinary QName anySimpleType""".split())
# facets that are dropped on purpose (listed in netex/TERMS.md)
FACETS = frozenset("""pattern minInclusive maxInclusive minExclusive maxExclusive length minLength maxLength
    totalDigits fractionDigits whiteSpace""".split())


class NameCollision(Exception):
    pass


def sk(n):
    return URIRef(SKOS + n)


def dc(n):
    return URIRef(DCTERMS + n)


def pct(v):
    return urllib.parse.quote(str(v), safe="-_.~")


def builtin(name, where):
    if name not in XSD_BUILTINS:
        raise UnsupportedSchema("%s: unsupported XSD built-in type %r" % (where, name))
    return URIRef(str(XSD) + name)


def body_of(node):
    """The restriction, list or union child of a simpleType."""
    kids = [c for c in node if local(c) != "annotation"]
    if len(kids) != 1 or local(kids[0]) not in ("restriction", "list", "union"):
        raise UnsupportedSchema("unsupported simpleType content %r" % [local(c) for c in kids])
    return kids[0]


class SimpleTypes:
    """Mapping of XSD simple types (needs self.model, self.mint and self.common)."""

    # ------------------------------------------------------------ simple types
    def simple_kind(self, node):
        body = body_of(node)
        tag = local(body)
        if tag == "restriction" and any(local(c) == "enumeration" for c in body):
            return "enum"
        return {"restriction": "datatype", "list": "list", "union": "union"}[tag]

    def type_ref(self, file, text):
        """(namespace, name, component or None) of a type reference written in `file`."""
        ns, name = self.model.qname(file, text)
        if ns == XSD_NS:
            return ns, name, None
        comp = self.model.find("type", ns, name)
        if comp is None:
            raise UnsupportedSchema("%s: unresolved type %r" % (file, text))
        return ns, name, comp

    def builtin_of(self, node, file, depth=0):
        """The XSD built-in a simple type is finally derived from (lists and unions: xsd:string)."""
        if depth > 50:
            raise UnsupportedSchema("%s: restriction chain is too deep or cyclic" % file)
        body = body_of(node)
        if local(body) != "restriction":
            return XSD.string
        if body.get("base"):
            ns, name, comp = self.type_ref(file, body.get("base"))
            if comp is None:
                return builtin(name, file)
            if local(comp.node) != "simpleType":
                raise UnsupportedSchema("%s: simple type restricts complex type %s" % (file, name))
            return self.builtin_of(comp.node, comp.file, depth + 1)
        inline = [c for c in body if local(c) == "simpleType"]
        if len(inline) != 1:
            raise UnsupportedSchema("%s: restriction without base" % file)
        return self.builtin_of(inline[0], file, depth + 1)

    def map_simple_types(self):
        out = []
        for key in sorted(k for k in self.model.components if k[0] == "type" and k[1] == NETEX):
            comp = self.model.components[key]
            if local(comp.node) == "simpleType":
                out += self.map_simple(comp.name, comp.node, comp.file)
        return out

    def map_simple(self, name, node, file, owner=None):
        """Triples for the simple type `node` (named, or anonymous and given a name by the caller)."""
        iri = URIRef(NS + name)
        where = "%s#%s" % (file, name)
        owner = owner or name
        self.mint(iri, owner, where)
        kind = self.simple_kind(node)
        out = self.common(iri, file, node)
        body = body_of(node)
        if kind == "enum":
            out += self.enumeration(iri, owner, body, file, where)
        elif kind == "datatype":
            for c in body:
                tag = local(c)
                if tag not in FACETS and tag not in ("annotation", "simpleType"):
                    raise UnsupportedSchema("%s: unsupported facet xsd:%s" % (where, tag))
            out += [(iri, RDF.type, RDFS.Datatype),
                    (iri, OWL.equivalentClass, Anon({(RDF.type, RDFS.Datatype),
                                                     (OWL.onDatatype, self.builtin_of(node, file))}))]
        elif kind == "list":
            out += self.list_type(iri, body, file, where)
        else:
            out += self.union_type(iri, body, file, where)
        return out

    def enumeration(self, iri, owner, body, file, where):
        out = [(iri, RDF.type, OWL.Class), (iri, RDF.type, sk("ConceptScheme"))]
        for c in body:
            tag = local(c)
            if tag == "enumeration":
                value = c.get("value")
                if value is None:
                    raise UnsupportedSchema("%s: enumeration without value" % where)
                v = URIRef("%s/%s" % (iri, pct(value)))
                self.mint(v, owner, where)
                out += [(v, RDF.type, sk("Concept")), (v, RDF.type, iri), (v, sk("inScheme"), iri),
                        (v, sk("notation"), Literal(value)), (v, sk("prefLabel"), Literal(value))]
                text = documentation(c)
                if text:
                    out.append((v, sk("definition"), Literal(text, lang="en")))
            elif tag not in FACETS and tag not in ("annotation", "simpleType"):
                raise UnsupportedSchema("%s: unsupported facet xsd:%s" % (where, tag))
        return out

    def named_target(self, file, text):
        """IRI a type reference points to: a minted NeTEx type, an XSD built-in, or None (SIRI, GML)."""
        ns, name, comp = self.type_ref(file, text)
        if comp is None:
            return builtin(name, file)
        return URIRef(NS + name) if ns == NETEX else None

    def list_type(self, iri, body, file, where):
        item = body.get("itemType")
        if not item:
            raise UnsupportedSchema("%s: xsd:list without itemType" % where)
        out = [(iri, RDF.type, RDFS.Datatype),
               (iri, OWL.equivalentClass, Anon({(RDF.type, RDFS.Datatype), (OWL.onDatatype, XSD.string)})),
               (iri, sk("scopeNote"), Literal("Space-separated list of %s." % item, lang="en"))]
        target = self.named_target(file, item)
        if target is not None:
            out.append((iri, RDFS.seeAlso, target))
        return out

    def union_type(self, iri, body, file, where):
        members = (body.get("memberTypes") or "").split()
        if not members or any(local(c) == "simpleType" for c in body):
            raise UnsupportedSchema("%s: xsd:union is supported only with memberTypes" % where)
        out = [(iri, RDF.type, RDFS.Datatype),
               (iri, sk("scopeNote"), Literal("Union of %s." % ", ".join(sorted(members)), lang="en"))]
        for m in members:
            target = self.named_target(file, m)
            if target is not None:
                out.append((iri, RDFS.seeAlso, target))
        return out


# ---------------------------------------------------------------- classes and properties

PREFIXES = {"rdf": str(RDF), "rdfs": str(RDFS), "owl": str(OWL), "xsd": str(XSD), "skos": SKOS,
            "dcterms": DCTERMS, "schema": "http://schema.org/", "netex": NS}
SCHEMA_ORG = "http://schema.org/"
FOLD_SUFFIXES = ("_VersionStructure", "_VersionedChildStructure", "_ValueStructure", "_VersionFrameStructure",
                 "_DerivedViewStructure")
LANG_ATTRIBUTES = frozenset(["lang", "textIdType"])
FOREIGN = {GML: "GML", SIRI: "SIRI"}
V020 = "https://vocabulary.eona-x.eu/ontology/netex/v0.2.0#"
LICENSE = "http://spdx.org/licenses/GPL-3.0-only"
# The notice of NeTEx_publication.xsd (xsd:appinfo, Rights/Copyright). Individual files carry earlier years and,
# for some, "CEN, VDV, RTIG 2004-2012"; GPL-3.0 requires the notice to stay with the conveyed copy.
COPYRIGHT = "CEN, Crown Copyright 2009-2026"
RIGHTS = "Copyright %s (NeTEx upstream; some XSD files carry earlier years and CEN, VDV, RTIG 2004-2012)." % COPYRIGHT
# Reference types whose target class is not defined in the schema (checked against NeTEx 2.0). A reference
# type that is not listed here and cannot be resolved fails the build.
UNRESOLVED_REFS = frozenset("""AllCountriesRefStructure DriverRefStructure ExternalObjectRefStructure
    FacilityRefStructure LegRefStructure PassengerSeatRefStructure RidePartRefStructure
    TripPatternRefStructure TripRefStructure VersionOfObjectRefStructure PointInSequenceRefStructure
    SupplyContractRefStructure PassengerInformationRequestRefStructure SimpleObjectRefStructure
    SpotAllocationMethodRefStructure ParkingEntranceRefStructure
    ModeRefStructure TrainElementTypeRefStructure""".split())


def upper_first(s):
    return s[:1].upper() + s[1:]


def schema_org(n):
    return URIRef(SCHEMA_ORG + n)


def derivation(node):
    """(kind, base QName text) of the complexContent / simpleContent derivation of a complexType, else (None, None)."""
    for c in node:
        if local(c) in ("complexContent", "simpleContent"):
            for d in c:
                if local(d) in ("extension", "restriction"):
                    return local(d), d.get("base")
    return None, None


class Shape:
    """What a property ranges over. kind: object | datatype. range: one IRI or None; includes: several IRIs."""

    def __init__(self, kind, range=None, includes=(), note=None, many=False):
        self.kind, self.range, self.includes, self.note = kind, range, tuple(sorted(includes)), note
        self.many = many    # a list-valued property (a relationship structure)

    def key(self):
        return (self.kind, self.range, self.includes)


class Prop:
    def __init__(self, iri, name, shape, doc, file, functional):
        self.iri, self.name, self.shape, self.doc, self.file = iri, name, shape, doc, file
        self.functional = functional
        self.owners = set()


class Element:
    """A top-level NeTEx element and what its type derives from."""

    def __init__(self, comp):
        self.comp, self.name, self.node = comp, comp.name, comp.node
        self.dummy = comp.name.endswith("_Dummy")
        self.abstract = comp.node.get("abstract") == "true"
        self.anon = next((c for c in comp.node if local(c) == "complexType"), None)
        self.anon_simple = next((c for c in comp.node if local(c) == "simpleType"), None)
        self.is_class = False
        self.base = None            # the named NeTEx complexType the element's type derives from, if any
        self.type_comp = None       # the named type of a `type=` element


class Mapper(SimpleTypes):
    UNRESOLVED_REFS = UNRESOLVED_REFS

    def __init__(self, model):
        self.model = model
        self.minted = {}            # iri -> owner, for collision detection
        self.props = {}
        self.required = set()       # (owner iri, property iri)
        self.triples = set()
        self.anon_done = set()
        self.dropped = {"any": 0, "id": 0}
        self.analyse()

    # ------------------------------------------------------------ helpers
    def mint(self, iri, owner, where):
        if self.minted.get(iri, owner) != owner:
            raise NameCollision("%s: IRI %s already minted by %s" % (where, iri, self.minted[iri]))
        self.minted[iri] = owner

    def common(self, iri, file, node, doc=None):
        out = [(iri, RDFS.label, Literal(str(iri)[len(NS):])),
               (iri, RDFS.isDefinedBy, URIRef(NS)),
               (iri, dc("source"), URIRef(REPO_BLOB + file))]
        text = doc or documentation(node)
        if text:
            out.append((iri, RDFS.comment, Literal(text, lang="en")))
        return out

    # ------------------------------------------------------------ analysis
    def netex_type(self, file, text):
        """The NeTEx complexType or simpleType component a type reference names; None for XSD, SIRI and GML."""
        ns, name = self.model.qname(file, text)
        if ns == XSD_NS:
            return None
        comp = self.model.find("type", ns, name)
        if comp is None:
            raise UnsupportedSchema("%s: unresolved type %r" % (file, text))
        return comp if ns == NETEX else None

    def complex_kind(self, comp):
        """class | ref | rel | simple | mixed for a named NeTEx complexType."""
        node = comp.node
        if any(local(c) == "simpleContent" for c in node):
            return "ref" if self.has_ref_attribute(comp) else "simple"
        if node.get("mixed") == "true":
            return "mixed"
        if comp.name.endswith("_RelStructure"):
            return "rel"
        return "class"

    def has_ref_attribute(self, comp, depth=0):
        return self.ref_id_type(comp, depth) is not None

    def ref_id_type(self, comp, depth=0):
        """(file, type text) of the `ref` attribute a reference type declares, searching its base chain."""
        if depth > 50:
            raise UnsupportedSchema("%s: derivation chain is too deep or cyclic" % comp.name)
        for c in comp.node.iter(XS + "attribute"):
            if c.get("name") == "ref":
                return comp.file, c.get("type")
        kind, base = derivation(comp.node)
        if base:
            parent = self.netex_type(comp.file, base)
            if parent is not None and local(parent.node) == "complexType":
                return self.ref_id_type(parent, depth + 1)
        return None

    def analyse(self):
        m = self.model
        self.elements = {}
        for (kind, ns, name), comp in sorted(m.components.items(), key=lambda kv: (kv[0][1] or "", kv[0][2])):
            if kind == "element" and ns == NETEX:
                self.elements[name] = Element(comp)
        users = {}
        for e in self.elements.values():
            self.classify(e)
            if e.is_class and not e.dummy and e.base is not None:
                users.setdefault(e.base.name, set()).add(e.name)
        # a *_VersionStructure-like type used by exactly one real element is folded into that element
        self.folded = {}
        for tname, es in users.items():
            if tname.endswith(FOLD_SUFFIXES) and len(es) == 1:
                self.folded[tname] = next(iter(es))
        self.types = {}
        for (kind, ns, name), comp in m.components.items():
            if kind == "type" and ns == NETEX and local(comp.node) == "complexType":
                self.types[name] = comp
        # classes: real class elements and the complexTypes that are not folded
        self.class_types = sorted(n for n, c in self.types.items()
                                  if self.complex_kind(c) == "class" and n not in self.folded)
        self.class_elements = sorted(n for n, e in self.elements.items() if e.is_class and not e.dummy)
        # IdType name -> the real class elements whose `id` attribute has that type
        self.id_owner = {}
        for n in self.class_elements:
            e = self.elements[n]
            if e.anon is None:
                continue
            for a in e.anon.iter(XS + "attribute"):
                if a.get("name") == "id" and a.get("type"):
                    self.id_owner.setdefault(m.qname(e.comp.file, a.get("type")), set()).add(n)

    def classify(self, e):
        file = e.comp.file
        if e.anon is not None:
            kind, base = derivation(e.anon)
            if base:
                comp = self.netex_type(file, base)
                if any(local(c) == "simpleContent" for c in e.anon) or (
                        comp is not None and local(comp.node) == "complexType"
                        and self.complex_kind(comp) in ("ref", "simple")):
                    return
                e.base = comp
            e.is_class = True
            return
        if e.node.get("type"):
            t = self.netex_type(file, e.node.get("type"))
            e.type_comp = t
            if t is not None and local(t.node) == "complexType" and self.complex_kind(t) == "class":
                e.is_class = True
                e.base = t

    def class_of_type(self, comp):
        """IRI of the class a named complexType is rendered as, or None."""
        if comp.name in self.folded:
            return URIRef(NS + self.folded[comp.name])
        if comp.name in self.types and self.complex_kind(comp) == "class":
            return URIRef(NS + comp.name)
        return None

    def head_class(self, ns, name, depth=0):
        """The nearest real class of a substitution group head: the head itself, or past `_Dummy` heads."""
        if ns != NETEX or depth > 50:
            return None
        e = self.elements.get(name)
        if e is None:
            return None
        if not e.dummy:
            return URIRef(NS + name) if e.is_class else None
        sub = e.node.get("substitutionGroup")
        if not sub:
            return None
        return self.head_class(*self.model.qname(e.comp.file, sub), depth + 1)

    def type_super(self, comp):
        """The class a (folded or minted) complexType derives from."""
        kind, base = derivation(comp.node)
        if not base:
            return None
        parent = self.netex_type(comp.file, base)
        if parent is None or local(parent.node) != "complexType":
            return None
        return self.class_of_type(parent)

    def element_supers(self, e):
        out = set()
        if e.base is not None:
            if e.base.name in self.folded and self.folded[e.base.name] == e.name:
                out.add(self.type_super(e.base))
            else:
                out.add(self.class_of_type(e.base))
        sub = e.node.get("substitutionGroup")
        if sub:
            out.add(self.head_class(*self.model.qname(e.comp.file, sub)))
        out.discard(None)
        out.discard(URIRef(NS + e.name))
        return out

    # ------------------------------------------------------------ running
    def run(self):
        self.triples = set(self.map_simple_types())
        for n in self.class_elements:
            self.element_class(self.elements[n])
        for n in self.class_types:
            self.type_class(self.types[n])
        for p in sorted(self.props.values(), key=lambda p: str(p.iri)):
            self.property_triples(p)
        for owner, p in sorted(self.required):
            self.triples.add((owner, RDFS.subClassOf, Anon({
                (RDF.type, OWL.Restriction), (OWL.onProperty, p),
                (OWL.minCardinality, Literal("1", datatype=XSD.nonNegativeInteger))})))
        return self.triples

    def element_class(self, e):
        iri = URIRef(NS + e.name)
        where = "%s#%s" % (e.comp.file, e.name)
        self.mint(iri, ("class", e.name), where)
        folded = e.base if e.base is not None and self.folded.get(e.base.name) == e.name else None
        doc = documentation(e.node) or (documentation(folded.node) if folded is not None else None)
        out = self.common(iri, e.comp.file, e.node, doc) + [(iri, RDF.type, OWL.Class)]
        if folded is not None:
            out.append((iri, sk("hiddenLabel"), Literal(folded.name)))
            if folded.file != e.comp.file:
                out.append((iri, dc("source"), URIRef(REPO_BLOB + folded.file)))
        if e.abstract:
            out.append((iri, sk("scopeNote"), Literal("Abstract in the XSD.", lang="en")))
        out += [(iri, RDFS.subClassOf, s) for s in sorted(self.element_supers(e))]
        self.triples.update(out)
        if e.anon is not None:
            self.collect(iri, walk_complex(self.model, e.anon, e.comp.file, e.name))
        if folded is not None:
            self.collect(iri, walk_complex(self.model, folded.node, folded.file, folded.name))

    def type_class(self, comp):
        iri = URIRef(NS + comp.name)
        self.mint(iri, ("class", comp.name), "%s#%s" % (comp.file, comp.name))
        out = self.common(iri, comp.file, comp.node) + [(iri, RDF.type, OWL.Class)]
        if comp.node.get("abstract") == "true":
            out.append((iri, sk("scopeNote"), Literal("Abstract in the XSD.", lang="en")))
        sup = self.type_super(comp)
        if sup is not None and sup != iri:
            out.append((iri, RDFS.subClassOf, sup))
        self.triples.update(out)
        self.collect(iri, walk_complex(self.model, comp.node, comp.file, comp.name))

    # ------------------------------------------------------------ properties
    def collect(self, owner, occurrences):
        for occ in occurrences:
            if occ.kind == "any":
                self.dropped["any"] += 1
            elif occ.kind == "element":
                self.element_property(owner, occ)
            else:
                self.attribute_property(owner, occ)

    def declare(self, owner, occ, name, make_shape, doc_node):
        """Register property `occ.decl.name` for `owner`; the shape is computed on first sight."""
        iri = URIRef("%s%s.%s" % (NS, occ.decl, pct(name)))
        self.mint(iri, (occ.kind, occ.decl), "%s#%s/%s" % (occ.file, occ.decl, name))
        p = self.props.get(iri)
        if p is None:
            shape, doc = make_shape()
            p = self.props[iri] = Prop(iri, name, shape, doc or documentation(doc_node), occ.file, True)
        if occ.repeating and occ.kind == "element":
            p.functional = False
        if p.shape.many:
            p.functional = False
        p.owners.add(owner)
        if occ.kind == "element" and not occ.optional and not occ.choice:
            self.required.add((owner, iri))
        return p

    def element_property(self, owner, occ):
        node, file = occ.node, occ.file
        if node.get("ref"):
            ns, name = self.model.qname(file, node.get("ref"))
            target = self.model.find("element", ns, name)
            if target is None:
                raise UnsupportedSchema("%s#%s: unresolved element ref %r" % (file, occ.decl, node.get("ref")))
            p = self.declare(owner, occ, name, lambda: (self.ref_shape(ns, target, file, occ.decl),
                                                        documentation(node) or documentation(target.node)), node)
            return p
        name = node.get("name")
        where = "%s#%s/%s" % (file, occ.decl, name)
        return self.declare(owner, occ, name, lambda: (self.local_shape(occ.decl, name, node, file, where), None), node)

    def attribute_property(self, owner, occ):
        node, file = occ.node, occ.file
        if node.get("ref"):
            if node.get("ref") == "xml:lang":
                self.dropped["id"] += 1
                return
            raise UnsupportedSchema("%s#%s: attribute ref %r is not supported" % (file, occ.decl, node.get("ref")))
        name = node.get("name")
        if name == "id":
            self.dropped["id"] += 1
            return
        where = "%s#%s/@%s" % (file, occ.decl, name)
        p = self.declare(owner, occ, name, lambda: (self.local_shape(occ.decl, name, node, file, where), None), node)
        p.functional = True

    # ------------------------------------------------------------ ranges
    def local_shape(self, decl, name, node, file, where):
        """Shape of a local element or attribute declaration with `type=` or an anonymous type."""
        if node.get("type"):
            return self.type_shape(file, node.get("type"), where)
        anon = next((c for c in node if local(c) in ("complexType", "simpleType")), None)
        if anon is None:
            if local(node) == "attribute":      # an attribute without a type is xsd:anySimpleType
                return Shape("datatype", builtin("anySimpleType", where))
            raise UnsupportedSchema("%s: declaration without a type" % where)
        gen = decl + upper_first(name)
        if local(anon) == "simpleType":
            if gen not in self.anon_done:
                self.anon_done.add(gen)
                self.triples.update(self.map_simple(gen, anon, file, ('anon', gen)))
            if self.simple_kind(anon) == "enum":
                return Shape("object", URIRef(NS + gen))
            return Shape("datatype", URIRef(NS + gen))
        shape = self.anon_value_shape(anon, file, where)
        if shape is not None:
            return shape
        iri = URIRef(NS + gen)
        if gen not in self.anon_done:
            self.anon_done.add(gen)
            self.mint(iri, ("anon", gen), where)
            out = self.common(iri, file, anon) + [(iri, RDF.type, OWL.Class)]
            kind, base = derivation(anon)
            if base:
                parent = self.netex_type(file, base)
                sup = self.class_of_type(parent) if parent is not None and local(parent.node) == "complexType" else None
                if sup is not None:
                    out.append((iri, RDFS.subClassOf, sup))
            self.triples.update(out)
            self.collect(iri, walk_complex(self.model, anon, file, gen))
        return Shape("object", iri)

    def type_shape(self, file, text, where):
        ns, name = self.model.qname(file, text)
        if ns == XSD_NS:
            if name == "anyType":
                return Shape("datatype", RDFS.Literal, note="xsd:anyType in the XSD: any content.")
            return Shape("datatype", builtin(name, where))
        comp = self.model.find("type", ns, name)
        if comp is None:
            raise UnsupportedSchema("%s: unresolved type %r" % (where, text))
        if ns != NETEX:
            if local(comp.node) == "simpleType":
                return Shape("datatype", self.builtin_of(comp.node, comp.file))
            return Shape("object", note="Range defined in the %s schema, not rendered." % FOREIGN.get(ns, ns))
        if local(comp.node) == "simpleType":
            iri = URIRef(NS + name)
            return Shape("object" if self.simple_kind(comp.node) == "enum" else "datatype", iri)
        kind = self.complex_kind(comp)
        if kind == "class":
            return Shape("object", self.class_of_type(comp))
        if kind == "ref":
            return self.ref_type_shape(comp, where)
        if kind == "rel":
            return self.rel_shape(comp, where)
        if kind == "mixed":
            return self.mixed_shape(comp, where)
        return self.simple_content_shape(comp, where)

    def mixed_shape(self, comp, where):
        names = {a.get("name") for a in comp.node if local(a) == "attribute"}
        if "lang" not in names:
            raise UnsupportedSchema("%s: mixed content type %s without a lang attribute" % (where, comp.name))
        return Shape("datatype", RDF.langString)

    def simple_content_shape(self, comp, where):
        kind, base = derivation(comp.node)
        names = {a.get("name") for a in comp.node.iter(XS + "attribute")}
        if names and names <= LANG_ATTRIBUTES:
            return Shape("datatype", RDF.langString)
        return Shape("datatype", self.simple_content_builtin(comp, where, 0))

    def simple_content_builtin(self, comp, where, depth):
        if depth > 50:
            raise UnsupportedSchema("%s: derivation chain is too deep or cyclic" % where)
        kind, base = derivation(comp.node)
        ns, name = self.model.qname(comp.file, base)
        if ns == XSD_NS:
            return builtin(name, where)
        parent = self.model.find("type", ns, name)
        if parent is None:
            raise UnsupportedSchema("%s: unresolved base type %r" % (where, base))
        if local(parent.node) == "simpleType":
            return self.builtin_of(parent.node, parent.file)
        return self.simple_content_builtin(parent, where, depth + 1)

    def ref_type_shape(self, comp, where):
        target = self.ref_target(comp, where)
        if target is None:
            return Shape("object", note="Reference type %s: no target class is defined in the schema." % comp.name)
        return Shape("object", target)

    def ref_target(self, comp, where):
        """The class a reference type points to, in this order:
        1. the `nameOfRefClass` default the type declares, when it names a class;
        2. the type name without the RefStructure suffix, when it names a class;
        3. the class whose `id` has the IdType of the `ref` attribute, only when the type declares that
           attribute itself (an inherited one carries the base type's IdType).

        None for the reference types listed in UNRESOLVED_REFS."""
        if comp.name in self.UNRESOLVED_REFS:
            return None
        classes = set(self.class_elements) | set(self.class_types)
        own = {a.get("name"): a for a in comp.node.iter(XS + "attribute")}
        default = own["nameOfRefClass"].get("default") if "nameOfRefClass" in own else None
        if default in classes:
            return URIRef(NS + default)
        stem = comp.name[:-len("RefStructure")] if comp.name.endswith("RefStructure") else None
        if stem in classes:
            return URIRef(NS + stem)
        candidates = set()
        if "ref" in own and own["ref"].get("type"):
            candidates = self.id_owner.get(self.model.qname(comp.file, own["ref"].get("type")), set())
        if len(candidates) == 1:
            return URIRef(NS + next(iter(candidates)))
        raise UnsupportedSchema("%s: cannot resolve the target class of %s (id type candidates: %s)"
                                % (where, comp.name, sorted(candidates)))

    def anon_value_shape(self, anon, file, where):
        """Shape of an anonymous complexType that is a reference or a value, not a class; else None."""
        kind, base = derivation(anon)
        if not base:
            return None
        ns, name = self.model.qname(file, base)
        if ns == XSD_NS:
            return Shape("datatype", builtin(name, where))
        comp = self.netex_type(file, base)
        if comp is None or local(comp.node) != "complexType":
            if any(local(c) == "simpleContent" for c in anon):
                raise UnsupportedSchema("%s: unsupported simple content base %r" % (where, base))
            return None
        ck = self.complex_kind(comp)
        if ck == "ref":
            return self.ref_type_shape(comp, where)
        if ck == "simple":
            return self.simple_content_shape(comp, where)
        return None

    def ref_shape(self, ns, target, file, decl):
        where = "%s#%s/ref=%s" % (file, decl, target.name)
        if ns != NETEX:
            return Shape("object", note="Range defined in the %s schema, not rendered." % FOREIGN.get(ns, ns))
        if self.elements[target.name].is_class:
            return Shape("object", self.head_class(ns, target.name))
        return self.element_value_shape(self.elements[target.name], where)

    def element_value_shape(self, e, where):
        """Shape of a top-level element that is not rendered as a class (a reference or a value)."""
        if e.node.get("type"):
            return self.type_shape(e.comp.file, e.node.get("type"), where)
        if e.anon is not None:
            shape = self.anon_value_shape(e.anon, e.comp.file, where)
            if shape is not None:
                return shape
        raise UnsupportedSchema("%s: cannot determine the type of element %s" % (where, e.name))

    def rel_shape(self, comp, where):
        classes = self.rel_members(comp, where, 0)
        if len(classes) == 1:
            return Shape("object", next(iter(classes)), many=True)
        return Shape("object", includes=classes, many=True)

    def rel_members(self, comp, where, depth):
        if depth > 50:
            raise UnsupportedSchema("%s: relationship chain is too deep or cyclic" % where)
        out = set()
        for occ in walk_complex(self.model, comp.node, comp.file, comp.name):
            if occ.kind != "element":
                continue
            node = occ.node
            if node.get("ref"):
                ns, name = self.model.qname(occ.file, node.get("ref"))
                target = self.model.find("element", ns, name)
                if target is None:
                    raise UnsupportedSchema("%s: unresolved element ref %r" % (where, node.get("ref")))
                shape = self.ref_shape(ns, target, occ.file, comp.name)
            elif node.get("type"):
                shape = self.type_shape(occ.file, node.get("type"), where)
            else:
                shape = self.anonymous_member_shape(occ, where)
            if shape.kind == "object" and shape.range is not None:
                out.add(shape.range)
            out.update(shape.includes)
        kind, base = derivation(comp.node)
        if base:
            parent = self.netex_type(comp.file, base)
            if parent is not None and local(parent.node) == "complexType" and self.complex_kind(parent) == "rel":
                out |= self.rel_members(parent, where, depth + 1)
        return out

    def anonymous_member_shape(self, occ, where):
        """An inline member of a relationship type counts as the class its type derives from."""
        anon = next((c for c in occ.node if local(c) == "complexType"), None)
        kind, base = derivation(anon) if anon is not None else (None, None)
        parent = self.netex_type(occ.file, base) if base else None
        cls = self.class_of_type(parent) if parent is not None and local(parent.node) == "complexType" else None
        if cls is None:
            raise UnsupportedSchema("%s: member %s of a relationship type has no resolvable class"
                                    % (where, occ.node.get("name")))
        return Shape("object", cls)

    def property_triples(self, p):
        s = p.shape
        out = [(p.iri, RDF.type, OWL.ObjectProperty if s.kind == "object" else OWL.DatatypeProperty),
               (p.iri, RDFS.label, Literal(p.name)), (p.iri, sk("notation"), Literal(p.name)),
               (p.iri, RDFS.isDefinedBy, URIRef(NS)), (p.iri, dc("source"), URIRef(REPO_BLOB + p.file))]
        if p.functional:
            out.append((p.iri, RDF.type, OWL.FunctionalProperty))
        if p.doc:
            out.append((p.iri, RDFS.comment, Literal(p.doc, lang="en")))
        if s.range is not None:
            out.append((p.iri, RDFS.range, s.range))
        out += [(p.iri, schema_org("rangeIncludes"), r) for r in s.includes]
        if s.note:
            out.append((p.iri, sk("scopeNote"), Literal(s.note, lang="en")))
        owners = sorted(p.owners)
        if len(owners) == 1:
            out.append((p.iri, RDFS.domain, owners[0]))
        else:
            out += [(p.iri, schema_org("domainIncludes"), o) for o in owners]
        self.triples.update(out)


# ---------------------------------------------------------------- root, invariants, output

def root_triples():
    root = URIRef(NS)
    return [
        (root, RDF.type, OWL.Ontology),
        (root, OWL.versionInfo, Literal(VERSION)),
        (root, OWL.priorVersion, URIRef(V020)),
        (root, RDFS.label, Literal("NeTEx 2.0 (CEN/TS 16614)", lang="en")),
        (root, RDFS.comment, Literal("RDF/OWL rendering of the complete NeTEx v2.0 XML Schema (publication closure), "
                                     "generated by tools/netex-generator. Upstream schema version 2.0 at commit %s."
                                     % COMMIT, lang="en")),
        (root, dc("source"), URIRef("https://github.com/TransmodelEcosystem/NeTEx/tree/%s/xsd" % COMMIT)),
        (root, dc("license"), URIRef(LICENSE)),
        (root, dc("rights"), Literal(RIGHTS)),
    ]


def build_triples(model, lenient_alignment=False):
    """All triples of the output. lenient_alignment skips the alignment rows whose subject the schema does not
    define (for the test fixture); otherwise such a row fails the build."""
    triples = set(Mapper(model).run())
    subjects = {s for s, p, o in triples}
    rows = []
    for row in v020_alignment.ALIGNMENT:
        if URIRef(NS + row[0]) in subjects:
            rows.append(row)
        elif not lenient_alignment:
            raise v020_alignment.AlignmentError("alignment subject %s is not defined by the schema" % row[0])
    triples.update(v020_alignment.alignment_triples(rows))
    triples.update(root_triples())
    check_invariants(triples)
    return triples


def _iris(triples):
    for s, p, o in triples:
        yield s
        yield p
        if isinstance(o, Anon):
            for pp, oo in o.pairs:
                yield pp
                if isinstance(oo, URIRef):
                    yield oo
        elif isinstance(o, URIRef):
            yield o


def check_invariants(triples):
    for s, p, o in triples:
        if not str(s).startswith(NS):
            raise AssertionError("subject outside the namespace: %s" % s)
    ontologies = [s for s, p, o in triples if p == RDF.type and o == OWL.Ontology]
    if ontologies != [URIRef(NS)]:
        raise AssertionError("expected exactly the root ontology, got %s" % ontologies)
    for i in _iris(triples):
        host = urllib.parse.urlparse(str(i)).netloc
        if "eona-x" in host and not str(i).startswith(NS) and not str(i).startswith(V020):
            raise AssertionError("Eona-X IRI outside the namespace: %s" % i)
    allowed = {OWL.priorVersion} | {getattr(SKOS_NS, n) for n in v020_alignment.PREDICATES}
    for s, p, o in triples:
        if str(o).startswith(V020) and p not in allowed:
            raise AssertionError("v0.2.0 IRI used outside owl:priorVersion and the alignment predicates: %s" % o)


def to_turtle(xsd_dir, pinned=None, header_extra=(), lenient_alignment=False):
    model = load(xsd_dir, "NeTEx_publication.xsd", pinned)
    header = [
        "Generated by tools/netex-generator (netexgen.netex_owl). Do not edit by hand.",
        "Source: https://github.com/TransmodelEcosystem/NeTEx/tree/%s/xsd" % COMMIT,
        "Source files and sha256: tools/netex-generator/sources.json (netex)",
        "Licence of the source data and of this file: GPL-3.0-only",
        "Copyright %s (NeTEx upstream)" % COPYRIGHT,
        "Regenerate: tools/netex-generator/regenerate.sh netex",
    ] + list(header_extra)
    return write_turtle(build_triples(model, lenient_alignment), PREFIXES, header=header, root=URIRef(NS))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--xsd-dir", required=True, help="the xsd/ directory of the pinned NeTEx checkout")
    ap.add_argument("--out", required=True, help="output file, or - for standard output")
    ap.add_argument("--lenient-alignment", action="store_true",
                    help="skip v0.2.0 alignment rows the schema does not define (test fixture only)")
    ap.add_argument("--sources", help="sources.json: the pinned file set the schema closure must equal")
    a = ap.parse_args(argv)
    pinned = None
    if a.sources:
        import json
        with open(a.sources, encoding="utf-8") as f:
            pinned = [k[len("xsd/"):] for k in json.load(f)["netex"]["files"]]
    text = to_turtle(a.xsd_dir, pinned, lenient_alignment=a.lenient_alignment)
    if a.out == "-":
        sys.stdout.write(text)
    else:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
