"""RDF/OWL rendering of the UIC OSDM JSON Schema / OpenAPI schemas.

python -I run.py eonagen.osdm_owl --spec-dir DIR --out FILE
DIR is the `specification/` directory of the pinned OSDM checkout. Its files are
parsed as data (yaml.safe_load / json.load) and never executed.
"""
import argparse
import json
import posixpath
import sys
import textwrap
import urllib.parse

import yaml
from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from eonagen.turtle import Anon, write_turtle

NS = "https://vocabulary.eona-x.eu/ontology/osdm/v3.11#"
VERSION = "3.11"
COMMIT = "d198a80259b9399754cec68cd60278892fe04cfe"
REPO_BLOB = "https://github.com/UnionInternationalCheminsdeFer/OSDM/blob/%s/specification/" % COMMIT
ONLINE_ROOT = "OSDM-online-api.yml"
OFFLINE_FILE = "OSDM-offline-model.json"

SKOS = "http://www.w3.org/2004/02/skos/core#"
DCTERMS = "http://purl.org/dc/terms/"
PREFIXES = {"rdf": str(RDF), "rdfs": str(RDFS), "owl": str(OWL), "xsd": str(XSD),
            "skos": SKOS, "dcterms": DCTERMS, "osdm": NS}


def sk(n):
    return URIRef(SKOS + n)


def dc(n):
    return URIRef(DCTERMS + n)


class UnsupportedSchema(Exception):
    pass


class NameCollision(Exception):
    pass


FORMATS = {
    "date-time": XSD.dateTime, "date": XSD.date, "duration": XSD.duration,
    "uri": XSD.anyURI, "url": XSD.anyURI, "byte": XSD.base64Binary,
    "int32": XSD.int, "int64": XSD.long, "float": XSD.float, "double": XSD.double,
}
TYPES = {"string": XSD.string, "integer": XSD.integer, "number": XSD.decimal, "boolean": XSD.boolean}

UNSUPPORTED = ("oneOf", "anyOf", "not", "patternProperties")
# keywords read by the mapping, plus keywords that are dropped on purpose (listed in osdm/TERMS.md)
USED = {"type", "format", "description", "properties", "required", "allOf", "$ref", "items", "enum",
        "x-extensible-enum", "discriminator", "example", "additionalProperties", "deprecated"}
DROPPED = {"nullable", "default", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
           "minLength", "maxLength", "minItems", "maxItems", "minitems", "maxitems", "uniqueItems",
           "minProperties", "maxProperties", "readOnly", "writeOnly", "contentEncoding",
           "examples", "title", "$comment"}


class Def:
    def __init__(self, origin, file, name, body):
        self.origin, self.file, self.name, self.body = origin, file, name, body

    @property
    def key(self):
        return (self.file, self.name)

    @property
    def pointer(self):
        return "%s#/%s" % (self.file, self.name)


def is_deprecated(schema):
    """`deprecated: true` on the schema or on an inline (non-$ref) allOf member."""
    return schema.get("deprecated") is True or any(
        isinstance(m, dict) and "$ref" not in m and m.get("deprecated") is True
        for m in schema.get("allOf") or [])


def pct(v):
    return urllib.parse.quote(str(v), safe="-_.~")


def clean(text):
    return textwrap.dedent(text).strip()


def upper_first(s):
    return s[:1].upper() + s[1:]


# ---------------------------------------------------------------- loading

def _read_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_online(ref, from_file, pointer):
    if not isinstance(ref, str) or "#/" not in ref and not ref.startswith("#"):
        raise UnsupportedSchema("%s: unsupported $ref %r" % (pointer, ref))
    path, _, frag = ref.partition("#")
    parts = [p for p in frag.split("/") if p]
    if len(parts) != 1 or "://" in path:
        raise UnsupportedSchema("%s: unsupported $ref %r" % (pointer, ref))
    if path:
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(from_file), path))
    else:
        rel = from_file
    return rel, parts[0]


def _refs_in(node, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                acc.append(v)
            else:
                _refs_in(v, acc)
    elif isinstance(node, list):
        for v in node:
            _refs_in(v, acc)


def load_online(spec_dir):
    cache = {}

    def file(rel):
        if rel not in cache:
            cache[rel] = _read_yaml(posixpath.join(spec_dir, rel))
        return cache[rel]

    api = file(ONLINE_ROOT)
    todo, defs = [], {}
    for name, body in api["components"]["schemas"].items():
        if set(body) == {"$ref"}:
            todo.append(resolve_online(body["$ref"], ONLINE_ROOT, "%s#/components/schemas/%s" % (ONLINE_ROOT, name)))
        else:
            defs[(ONLINE_ROOT, name)] = Def("online", ONLINE_ROOT, name, body)
            refs = []
            _refs_in(body, refs)
            todo.extend(resolve_online(r, ONLINE_ROOT, defs[(ONLINE_ROOT, name)].pointer) for r in refs)
    while todo:
        rel, name = todo.pop()
        if (rel, name) in defs:
            continue
        doc = file(rel)
        if name not in doc:
            raise UnsupportedSchema("%s#/%s: unresolved $ref" % (rel, name))
        d = defs[(rel, name)] = Def("online", rel, name, doc[name])
        refs = []
        _refs_in(d.body, refs)
        todo.extend(resolve_online(r, d.file, d.pointer) for r in refs)
    by_name = {}
    for d in defs.values():
        if d.name in by_name:
            raise NameCollision("%s defined in %s and %s" % (d.name, by_name[d.name].file, d.file))
        by_name[d.name] = d
    return defs


def load_offline(spec_dir):
    with open(posixpath.join(spec_dir, OFFLINE_FILE), encoding="utf-8") as f:
        doc = json.load(f)
    return {(OFFLINE_FILE, n): Def("offline", OFFLINE_FILE, n, b) for n, b in doc["definitions"].items()}


def resolve_offline(ref, pointer):
    if not isinstance(ref, str) or not ref.startswith("#/definitions/") or "/" in ref[len("#/definitions/"):]:
        raise UnsupportedSchema("%s: unsupported $ref %r" % (pointer, ref))
    return OFFLINE_FILE, ref[len("#/definitions/"):]


# ---------------------------------------------------------------- mapping

def kind_of(d):
    b = d.body
    for k in UNSUPPORTED:
        if k in b:
            raise UnsupportedSchema("%s: %s is not supported" % (d.pointer, k))
    if "enum" in b or "x-extensible-enum" in b:
        return "enum"
    t = b.get("type")
    if t == "array":
        return "array"
    if t in TYPES:
        return "primitive"
    if t == "object" or "properties" in b or "allOf" in b:
        return "class"
    raise UnsupportedSchema("%s: cannot classify definition (type=%r)" % (d.pointer, t))


class Mapper:
    def __init__(self, defs, renames=frozenset()):
        self.defs = defs          # key -> Def, online and offline
        self.renames = renames    # names of offline definitions that get the Offline prefix
        self.minted = {}          # iri -> owner (for collision detection)

    # names / IRIs
    def eff(self, d):
        return "Offline" + d.name if d.origin == "offline" and d.name in self.renames else d.name

    def iri(self, d):
        return URIRef(NS + self.eff(d))

    def target(self, d, ref, pointer):
        key = resolve_offline(ref, pointer) if d.origin == "offline" else resolve_online(ref, d.file, pointer)
        if key not in self.defs:
            raise UnsupportedSchema("%s: unresolved $ref %r" % (pointer, ref))
        return self.defs[key]

    def mint(self, iri, owner, pointer):
        if self.minted.get(iri, owner) != owner:
            raise NameCollision("%s: IRI %s already minted by %s" % (pointer, iri, self.minted[iri]))
        self.minted[iri] = owner

    # building blocks
    def common(self, d, iri, body, owner):
        out = [(iri, RDFS.label, Literal(iri[len(NS):])),
               (iri, RDFS.isDefinedBy, URIRef(NS)),
               (iri, dc("source"), URIRef(REPO_BLOB + d.file))]
        desc = body.get("description")
        if isinstance(desc, str) and clean(desc):
            out.append((iri, RDFS.comment, Literal(clean(desc), lang="en")))
        if "example" in body:
            out.append((iri, sk("example"), _example(body["example"])))
        if is_deprecated(body):
            out.append((iri, OWL.deprecated, Literal(True)))
        return out

    def check_keys(self, body, pointer):
        for k in UNSUPPORTED:
            if k in body:
                raise UnsupportedSchema("%s: %s is not supported" % (pointer, k))
        if isinstance(body.get("additionalProperties"), dict):
            raise UnsupportedSchema("%s: additionalProperties with a schema is not supported" % pointer)
        if isinstance(body.get("type"), list):
            raise UnsupportedSchema("%s: type list is not supported" % pointer)
        for k in body:
            if k not in USED and k not in DROPPED and not k.startswith("x-"):
                raise UnsupportedSchema("%s: unknown keyword %r" % (pointer, k))

    def datatype(self, body, pointer):
        fmt = body.get("format")
        if fmt is not None:
            if fmt not in FORMATS:
                raise UnsupportedSchema("%s: unknown format %r" % (pointer, fmt))
            return FORMATS[fmt]
        t = body.get("type")
        if t not in TYPES:
            raise UnsupportedSchema("%s: unknown type %r" % (pointer, t))
        return TYPES[t]

    # definitions
    def map_def(self, d):
        self.check_keys(d.body, d.pointer)
        k = kind_of(d)
        if k == "array":
            return []
        iri = self.iri(d)
        self.mint(iri, self.eff(d), d.pointer)
        if k == "class":
            out = self.map_class(d, iri, d.body, d.pointer)
        elif k == "enum":
            out = self.map_enum(d, iri, d.body, d.pointer)
        else:
            out = self.common(d, iri, d.body, None)
            out += [(iri, RDF.type, RDFS.Datatype),
                    (iri, OWL.equivalentClass, Anon({(RDF.type, RDFS.Datatype),
                                                     (OWL.onDatatype, self.datatype(d.body, d.pointer))}))]
        return out

    def map_enum(self, d, iri, body, pointer):
        values = body.get("enum")
        extensible = False
        if values is None:
            values = body["x-extensible-enum"]
            extensible = True
        out = self.common(d, iri, body, None)
        out += [(iri, RDF.type, OWL.Class), (iri, RDF.type, URIRef(SKOS + "ConceptScheme"))]
        if extensible:
            out.append((iri, sk("scopeNote"), Literal("Extensible list: other values may occur.", lang="en")))
        for item in values:
            text = None
            if isinstance(item, dict):
                if len(item) != 1:
                    raise UnsupportedSchema("%s: unsupported enum item %r" % (pointer, item))
                (value, text), = item.items()
            else:
                value = item
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise UnsupportedSchema("%s: unsupported enum value %r" % (pointer, value))
            value = str(value)
            v = URIRef("%s/%s" % (iri, pct(value)))
            self.mint(v, self.eff(d), pointer)
            out += [(v, RDF.type, sk("Concept")), (v, RDF.type, iri), (v, sk("inScheme"), iri),
                    (v, sk("notation"), Literal(value)), (v, sk("prefLabel"), Literal(value))]
            if isinstance(text, str) and clean(text):
                out.append((v, sk("definition"), Literal(clean(text), lang="en")))
        return out

    def class_members(self, d, body, pointer):
        """Returns (parents, [(properties dict, required list, pointer)], description)."""
        parents, parts = [], []
        for i, m in enumerate(body.get("allOf") or []):
            mp = "%s/allOf/%d" % (pointer, i)
            if "$ref" in m:
                t = self.target(d, m["$ref"], mp)
                if kind_of(t) != "class":
                    raise UnsupportedSchema("%s: allOf $ref to a non-class" % mp)
                parents.append(t)
            else:
                self.check_keys(m, mp)
                parts.append((m, mp))
        return parents, parts

    def map_class(self, d, iri, body, pointer, owner=None):
        owner = owner or self.eff(d)
        cn = iri[len(NS):]
        out = self.common(d, iri, body, owner)
        out.append((iri, RDF.type, OWL.Class))
        parents, parts = self.class_members(d, body, pointer)
        if "description" not in body:
            for m, _ in parts:
                if "description" in m:
                    out.append((iri, RDFS.comment, Literal(clean(m["description"]), lang="en")))
                    break
        for t in parents:
            out.append((iri, RDFS.subClassOf, self.iri(t)))
        disc = body.get("discriminator")
        if disc is not None:
            out.append((iri, sk("scopeNote"),
                        Literal("Discriminator property: %s." % disc.get("propertyName"), lang="en")))
        own = {}
        required = []
        for src, sp in [(body, pointer)] + parts:
            required += src.get("required") or []
        for src, sp in [(body, pointer)] + parts:
            for pname, ps in (src.get("properties") or {}).items():
                out += self.map_property(d, iri, cn, pname, ps, "%s/properties/%s" % (sp, pname), owner,
                                         pname in required)
                own[pname] = iri
        for pname in required:
            holder = self.property_holder(d, iri, pname, own, pointer)
            p = URIRef("%s.%s" % (holder, pct(pname)))
            out.append((iri, RDFS.subClassOf, Anon({
                (RDF.type, OWL.Restriction), (OWL.onProperty, p),
                (OWL.minCardinality, Literal("1", datatype=XSD.nonNegativeInteger))})))
        return out

    def property_holder(self, d, iri, pname, own, pointer):
        if pname in own:
            return iri
        body = d.body if iri == self.iri(d) else None
        todo = list(self.class_members(d, body, pointer)[0]) if body is not None else []
        seen = set()
        while todo:
            t = todo.pop(0)
            if t.key in seen:
                continue
            seen.add(t.key)
            if pname in (t.body.get("properties") or {}) or any(
                    pname in (m.get("properties") or {}) for m in t.body.get("allOf") or [] if "$ref" not in m):
                return self.iri(t)
            todo += self.class_members(t, t.body, t.pointer)[0]
        raise UnsupportedSchema("%s: required property %r is not defined" % (pointer, pname))

    # properties
    def map_property(self, d, cls_iri, cn, pname, ps, pointer, owner, is_required=False):
        self.check_keys(ps, pointer)
        p = URIRef("%s.%s" % (cls_iri, pct(pname)))
        self.mint(p, owner, pointer)
        extra, is_array = [], False
        desc = ps.get("description")
        deprecated = is_deprecated(ps)
        schema = ps
        ip = pointer
        while schema.get("type") == "array":
            if "items" not in schema:
                raise UnsupportedSchema("%s: array without items" % ip)
            is_array = True
            schema = schema["items"]
            ip += "/items"
            self.check_keys(schema, ip)
            deprecated = deprecated or is_deprecated(schema)
            if desc is None:
                desc = schema.get("description")
        is_object, rng, arr, more = self.value_shape(d, schema, cn, pname, ip, owner)
        extra += more
        is_array = is_array or arr
        deprecated = deprecated or self.array_deprecated(d, schema, ip)
        if desc is None and "allOf" in schema:
            for m in schema["allOf"]:
                if "$ref" not in m and "description" in m:
                    desc = m["description"]
        out = [(p, RDF.type, OWL.ObjectProperty if is_object else OWL.DatatypeProperty),
               (p, RDFS.label, Literal(pname)), (p, sk("notation"), Literal(pname)),
               (p, RDFS.domain, cls_iri), (p, RDFS.range, rng)]
        if is_required and not is_array:
            out.append((p, RDF.type, OWL.FunctionalProperty))
        if deprecated:
            out.append((p, OWL.deprecated, Literal(True)))
        if isinstance(desc, str) and clean(desc):
            out.append((p, RDFS.comment, Literal(clean(desc), lang="en")))
        if "example" in ps:
            out.append((p, sk("example"), _example(ps["example"])))
        return out + extra

    def array_deprecated(self, d, schema, pointer):
        """True when the schema refers to a named array definition marked deprecated."""
        ref = schema.get("$ref")
        if ref is None:
            refs = [m["$ref"] for m in schema.get("allOf") or [] if "$ref" in m]
            ref = refs[0] if len(refs) == 1 else None
        for _ in range(9):
            if ref is None:
                return False
            t = self.target(d, ref, pointer)
            if kind_of(t) != "array":
                return False
            if is_deprecated(t.body):
                return True
            d, ref = t, (t.body.get("items") or {}).get("$ref")
        return False

    def value_shape(self, d, schema, cn, pname, pointer, owner):
        """(is_object, range, is_array, extra triples) for a non-array property schema."""
        if "allOf" in schema:
            refs = [m for m in schema["allOf"] if "$ref" in m]
            if len(refs) != 1:
                raise UnsupportedSchema("%s: allOf needs exactly one $ref" % pointer)
            return self.ref_shape(d, refs[0]["$ref"], pointer)
        if "$ref" in schema:
            return self.ref_shape(d, schema["$ref"], pointer)
        inline = URIRef(NS + cn + upper_first(pname))
        if "enum" in schema or "x-extensible-enum" in schema:
            self.mint(inline, owner, pointer)
            return True, inline, False, self.map_enum(d, inline, schema, pointer)
        if schema.get("type") == "object":
            if "properties" not in schema:
                raise UnsupportedSchema("%s: object without properties" % pointer)
            self.mint(inline, owner, pointer)
            return True, inline, False, self.map_class(d, inline, schema, pointer, owner)
        return False, self.datatype(schema, pointer), False, []

    def ref_shape(self, d, ref, pointer, depth=0):
        t = self.target(d, ref, pointer)
        k = kind_of(t)
        if k == "class" or k == "enum":
            return True, self.iri(t), False, []
        if k == "primitive":
            return False, self.iri(t), False, []
        if depth > 8 or "items" not in t.body:
            raise UnsupportedSchema("%s: unsupported array definition %s" % (pointer, t.name))
        items = t.body["items"]
        if "$ref" in items:
            o, r, _, e = self.ref_shape(t, items["$ref"], pointer, depth + 1)
            return o, r, True, e
        if items.get("type") == "object" or "enum" in items or "x-extensible-enum" in items:
            o, r, _, e = self.value_shape(t, items, self.eff(t), "Item", pointer, self.eff(t))
            return o, r, True, e
        return False, self.datatype(items, pointer), True, []


def _example(v):
    return Literal(v if isinstance(v, str) else json.dumps(v, sort_keys=True, ensure_ascii=False))


ANNOTATIONS = {RDFS.label, RDFS.comment, RDFS.isDefinedBy, dc("source"), sk("example"), sk("definition"),
               sk("prefLabel")}


def _structure(triples):
    """The triples left once the annotation properties are removed."""
    return {t for t in triples if t[1] not in ANNOTATIONS}


def decide_renames(online, offline):
    on_names = {d.name: d for d in online.values()}
    collisions = sorted(d.name for d in offline.values() if d.name in on_names)
    renames = set()
    taken = {d.name for d in online.values()} | {d.name for d in offline.values()}
    while True:
        m = Mapper({**online, **offline}, frozenset(renames))
        added = False
        for name in collisions:
            if name in renames:
                continue
            a = _structure(m.map_def(on_names[name]))
            b = _structure(m.map_def(offline[(OFFLINE_FILE, name)]))
            if a != b:
                if "Offline" + name in taken:
                    raise NameCollision("Offline%s is already taken" % name)
                renames.add(name)
                added = True
        if not added:
            return frozenset(renames), collisions


def build_triples(spec_dir):
    online = load_online(spec_dir)
    offline = load_offline(spec_dir)
    renames, collisions = decide_renames(online, offline)
    m = Mapper({**online, **offline}, renames)
    triples = set()
    for d in sorted(list(online.values()) + list(offline.values()), key=lambda x: (x.origin, x.file, x.name)):
        triples.update(m.map_def(d))
    for name in sorted(renames):
        triples.add((URIRef(NS + "Offline" + name), RDFS.seeAlso, URIRef(NS + name)))
    triples.update(root_triples())
    check_invariants(triples)
    return triples, renames, collisions


def root_triples():
    root = URIRef(NS)
    return [
        (root, RDF.type, OWL.Ontology),
        (root, OWL.versionInfo, Literal(VERSION)),
        (root, RDFS.label, Literal("OSDM 3.11 (Open Sales and Distribution Model)", lang="en")),
        (root, RDFS.comment, Literal("RDF rendering of the UIC OSDM v3.11 offline model and online API schemas. "
                                     "Upstream info.version reads 3.9.0 and the offline $id reads v3.6 at this tag.", lang="en")),
        (root, dc("source"), URIRef("https://github.com/UnionInternationalCheminsdeFer/OSDM/tree/%s/specification" % COMMIT)),
        (root, dc("license"), URIRef("https://www.apache.org/licenses/LICENSE-2.0")),
    ]


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
        if "eona-x" in host and not str(i).startswith(NS):
            raise AssertionError("Eona-X IRI outside the namespace: %s" % i)


def to_turtle(spec_dir, header_extra=()):
    triples, renames, collisions = build_triples(spec_dir)
    header = [
        "Generated by tools/generators (eonagen.osdm_owl). Do not edit by hand.",
        "Source: https://github.com/UnionInternationalCheminsdeFer/OSDM/tree/%s/specification" % COMMIT,
        "Source files and sha256: tools/generators/sources.json (osdm)",
        "Licence of the source data: Apache-2.0",
        "Regenerate: tools/generators/regenerate.sh osdm",
    ] + list(header_extra)
    return write_turtle(triples, PREFIXES, header=header, root=URIRef(NS))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    text = to_turtle(a.spec_dir)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
