"""RDF/OWL rendering of the NeTEx v2.0 XML Schema (publication closure).

python -I run.py netexgen.netex_owl --xsd-dir DIR --out FILE
DIR is the `xsd/` directory of the pinned NeTEx checkout. Its files are parsed as
data (xml.etree.ElementTree) and never executed. The mapping rules are documented
in netex/TERMS.md.
"""
import urllib.parse

from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from netexgen.turtle import Anon
from netexgen.xsd_load import (NETEX, XSD_NS, UnsupportedSchema, documentation, local)

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


class Mapper:
    def __init__(self, model):
        self.model = model
        self.minted = {}   # iri -> owner, for collision detection

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

    def map_simple(self, name, node, file):
        """Triples for the simple type `node` (named, or anonymous and given a name by the caller)."""
        iri = URIRef(NS + name)
        where = "%s#%s" % (file, name)
        self.mint(iri, name, where)
        kind = self.simple_kind(node)
        out = self.common(iri, file, node)
        body = body_of(node)
        if kind == "enum":
            out += self.enumeration(iri, name, body, file, where)
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

    def enumeration(self, iri, name, body, file, where):
        out = [(iri, RDF.type, OWL.Class), (iri, RDF.type, sk("ConceptScheme"))]
        for c in body:
            tag = local(c)
            if tag == "enumeration":
                value = c.get("value")
                if value is None:
                    raise UnsupportedSchema("%s: enumeration without value" % where)
                v = URIRef("%s/%s" % (iri, pct(value)))
                self.mint(v, name, where)
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
