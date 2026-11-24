"""Load the include/import closure of an XML Schema and expose its components.

The schema files are data: they are parsed with xml.etree.ElementTree (no
external entities, no network access) and never executed.
"""
import os
import posixpath
import xml.etree.ElementTree as ET

XS = "{http://www.w3.org/2001/XMLSchema}"
XSD_NS = "http://www.w3.org/2001/XMLSchema"
NETEX = "http://www.netex.org.uk/netex"
SIRI = "http://www.siri.org.uk/siri"
GML = "http://www.opengis.net/gml/3.2"

KINDS = {"element": "element", "complexType": "type", "simpleType": "type", "group": "group",
         "attributeGroup": "attributeGroup", "attribute": "attribute"}


class UnsupportedSchema(Exception):
    """A schema construct the generator does not map. Raised instead of guessing."""


class ClosureError(Exception):
    """The include/import closure is unsafe, incomplete or differs from the pinned set."""


def local(node):
    return node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""


def parse(path):
    """(root element, prefix map declared on the root element)."""
    it = ET.iterparse(path, events=("start-ns", "start"))
    nsmap, root = {}, None
    for event, value in it:
        if event == "start-ns" and root is None:
            nsmap[value[0]] = value[1]
        elif event == "start" and root is None:
            root = value
    return it.root, nsmap


def resolve_location(rel_from, location, confine=None):
    if location is None:
        raise ClosureError("%s: include or import without schemaLocation" % rel_from)
    if "://" in location or location.startswith("/") or "\\" in location or "\0" in location:
        raise ClosureError("%s: unsafe schemaLocation %r" % (rel_from, location))
    rel = posixpath.normpath(posixpath.join(posixpath.dirname(rel_from), location))
    if rel == ".." or rel.startswith("../") or (confine and not rel.startswith(confine + "/")):
        raise ClosureError("%s: schemaLocation %r leaves the schema directory" % (rel_from, location))
    return rel


def _parse_closure(root, entry, confine=None):
    seen, todo = {}, [posixpath.normpath(entry)]
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        path = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(path):
            raise ClosureError("missing schema file: %s" % rel)
        tree, nsmap = parse(path)
        seen[rel] = (tree, nsmap)
        for child in tree:
            tag = local(child)
            if tag in ("include", "import"):
                todo.append(resolve_location(rel, child.get("schemaLocation"), confine))
            elif tag in ("redefine", "override"):
                raise ClosureError("%s: xsd:%s is not supported" % (rel, tag))
    return seen


def closure(root, entry, confine=None):
    """Sorted paths (relative to root) of the entry file and everything it includes or imports."""
    return sorted(_parse_closure(root, entry, confine))


class Schema:
    def __init__(self, rel, root, nsmap):
        self.rel, self.root, self.nsmap = rel, root, nsmap
        self.ns = root.get("targetNamespace")


class Component:
    def __init__(self, kind, ns, name, node, file):
        self.kind, self.ns, self.name, self.node, self.file = kind, ns, name, node, file


class Model:
    def __init__(self):
        self.schemas = {}
        self.components = {}

    def find(self, kind, ns, name):
        return self.components.get((kind, ns, name))

    def qname(self, file, text):
        """(namespace, local name) of a QName attribute value written in `file`."""
        text = text.strip()
        nsmap = self.schemas[file].nsmap
        if ":" in text:
            prefix, name = text.split(":", 1)
            if prefix not in nsmap:
                raise UnsupportedSchema("%s: undeclared prefix in %r" % (file, text))
            return nsmap[prefix], name
        return nsmap.get(""), text

    def lookup(self, kind, file, text):
        ns, name = self.qname(file, text)
        comp = self.find(kind, ns, name)
        if comp is None and ns != XSD_NS:
            raise UnsupportedSchema("%s: unresolved %s reference %r" % (file, kind, text))
        return comp


def load(xsd_dir, entry, pinned=None):
    """Parse the closure of `entry` (relative to xsd_dir) into a Model.

    `pinned`, when given, is the exact set of files the closure must consist of.
    """
    parsed = _parse_closure(xsd_dir, entry)
    if pinned is not None:
        got, want = set(parsed), set(pinned)
        if got != want:
            raise ClosureError("closure differs from the pinned files: unpinned %s, unreached %s"
                               % (sorted(got - want), sorted(want - got)))
    model = Model()
    for rel in sorted(parsed):
        tree, nsmap = parsed[rel]
        schema = model.schemas[rel] = Schema(rel, tree, nsmap)
        for child in tree:
            tag = local(child)
            if tag in ("annotation", "include", "import"):
                continue
            if tag not in KINDS:
                raise UnsupportedSchema("%s: unsupported top-level xsd:%s" % (rel, tag))
            name = child.get("name")
            if not name:
                raise UnsupportedSchema("%s: top-level xsd:%s without name" % (rel, tag))
            key = (KINDS[tag], schema.ns, name)
            if key in model.components:
                raise UnsupportedSchema("%s: %s %s declared twice (also in %s)"
                                        % (rel, KINDS[tag], name, model.components[key].file))
            model.components[key] = Component(KINDS[tag], schema.ns, name, child, rel)
    return model


def documentation(node):
    """The xsd:documentation texts of a node, whitespace collapsed, joined by a blank line."""
    texts = []
    for ann in node:
        if local(ann) != "annotation":
            continue
        for doc in ann:
            if local(doc) == "documentation":
                text = " ".join("".join(doc.itertext()).split())
                if text:
                    texts.append(text)
    return "\n\n".join(texts) or None


# ---------------------------------------------------------------- content walking

class Occurrence:
    """One element, attribute or wildcard met while walking a content model.

    decl is the name of the nearest enclosing named group, attributeGroup or type.
    optional: the particle or an ancestor may be absent. repeating: it or an ancestor may repeat.
    choice: it is a direct or indirect member of an xsd:choice.
    """

    def __init__(self, kind, node, decl, file, optional, repeating, choice):
        self.kind, self.node, self.decl, self.file = kind, node, decl, file
        self.optional, self.repeating, self.choice = optional, repeating, choice

    @property
    def required_attribute(self):
        return self.kind == "attribute" and self.node.get("use") == "required"


def occurs(node, where):
    try:
        lo = int(node.get("minOccurs", "1"))
        hi = node.get("maxOccurs", "1")
        hi = None if hi == "unbounded" else int(hi)
    except ValueError:
        raise UnsupportedSchema("%s: bad occurrence bounds" % where)
    return lo, hi


def walk_group(model, comp):
    return _walk_children(model, comp.node, comp.file, comp.name, False, False, False, (comp.name,))


def walk_complex(model, node, file, decl):
    """Occurrences declared by a complexType node: its own content or its extension, not a restriction."""
    stack = ()
    for child in node:
        tag = local(child)
        if tag == "annotation" or tag == "simpleContent":
            continue
        if tag == "complexContent":
            for deriv in child:
                dtag = local(deriv)
                if dtag == "extension":
                    yield from _walk_children(model, deriv, file, decl, False, False, False, stack)
                elif dtag not in ("restriction", "annotation"):
                    raise UnsupportedSchema("%s#%s: unsupported xsd:%s in complexContent" % (file, decl, dtag))
        else:
            yield from _particle(model, child, file, decl, False, False, False, stack)


def _walk_children(model, node, file, decl, opt, rep, ch, stack):
    for child in node:
        if local(child) != "annotation":
            yield from _particle(model, child, file, decl, opt, rep, ch, stack)


def _particle(model, node, file, decl, opt, rep, ch, stack):
    tag = local(node)
    where = "%s#%s/%s" % (file, decl, tag)
    if tag in ("sequence", "choice"):
        lo, hi = occurs(node, where)
        yield from _walk_children(model, node, file, decl, opt or lo == 0, rep or hi is None or hi > 1,
                                  ch or tag == "choice", stack)
    elif tag == "group":
        lo, hi = occurs(node, where)
        comp = model.lookup("group", file, node.get("ref") or "")
        if comp is None or node.get("ref") is None:
            raise UnsupportedSchema("%s: group without resolvable ref" % where)
        if comp.name in stack:
            raise UnsupportedSchema("%s: group %s refers to itself" % (where, comp.name))
        yield from _walk_children(model, comp.node, comp.file, comp.name, opt or lo == 0,
                                  rep or hi is None or hi > 1, ch, stack + (comp.name,))
    elif tag == "element":
        lo, hi = occurs(node, where)
        yield Occurrence("element", node, decl, file, opt or lo == 0, rep or hi is None or hi > 1, ch)
    elif tag == "attribute":
        yield Occurrence("attribute", node, decl, file, opt or node.get("use") != "required", rep, ch)
    elif tag == "attributeGroup":
        comp = model.lookup("attributeGroup", file, node.get("ref") or "")
        if comp is None:
            raise UnsupportedSchema("%s: attributeGroup without resolvable ref" % where)
        if comp.name in stack:
            raise UnsupportedSchema("%s: attributeGroup %s refers to itself" % (where, comp.name))
        yield from _walk_children(model, comp.node, comp.file, comp.name, opt, rep, ch, stack + (comp.name,))
    elif tag in ("any", "anyAttribute"):
        yield Occurrence("any", node, decl, file, True, True, ch)
    else:
        raise UnsupportedSchema("%s: unsupported xsd:%s" % (where, tag))
