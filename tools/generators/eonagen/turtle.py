"""Deterministic Turtle writer shared by the vocabulary generators.

Triples are (URIRef, URIRef, URIRef | Literal | Anon). Anonymous nodes are
passed as Anon(frozenset({(p, o), ...})) and written inline as [ ... ], so no
blank-node labels exist to churn between runs.
"""
import re

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS

_LOCAL = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")
_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}


class Anon:
    """An anonymous node described by a set of (predicate, object) pairs."""

    def __init__(self, pairs):
        self.pairs = frozenset(pairs)

    def __eq__(self, other):
        return isinstance(other, Anon) and self.pairs == other.pairs

    def __hash__(self):
        return hash(self.pairs)


def _escape(text):
    out = []
    for ch in text:
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ord(ch) < 0x20:
            out.append("\\u%04X" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


class _Writer:
    def __init__(self, prefixes):
        self.prefixes = sorted(prefixes.items(), key=lambda kv: -len(kv[1]))
        self.used = set()

    def iri(self, term):
        s = str(term)
        for prefix, ns in self.prefixes:
            if s.startswith(ns) and _LOCAL.match(s[len(ns):]):
                self.used.add(prefix)
                return prefix + ":" + s[len(ns):]
        return "<" + s + ">"

    def literal(self, lit):
        text = '"' + _escape(str(lit)) + '"'
        if lit.language:
            return text + "@" + lit.language
        if lit.datatype:
            return text + "^^" + self.iri(lit.datatype)
        return text

    def term(self, o):
        if isinstance(o, Anon):
            return self.anon(o)
        if isinstance(o, Literal):
            return self.literal(o)
        return self.iri(o)

    def anon(self, a):
        return "[ " + " ; ".join(self.pred_obj(p, objs) for p, objs in self.group(a.pairs)) + " ]"

    def group(self, pairs):
        by_p = {}
        for p, o in pairs:
            by_p.setdefault(p, []).append(o)
        return [(p, by_p[p]) for p in sorted(by_p, key=_pred_key)]

    def pred_obj(self, p, objs):
        rendered = sorted(self.term(o) for o in objs)
        name = "a" if p == RDF.type else self.iri(p)
        return name + " " + ", ".join(rendered)


def _pred_key(p):
    rank = 0 if p == RDF.type else 1 if p == RDFS.label else 2
    return (rank, str(p))


def write_turtle(triples, prefixes, header=(), root=None):
    w = _Writer(prefixes)
    by_s = {}
    for s, p, o in triples:
        by_s.setdefault(s, []).append((p, o))
    order = sorted(by_s, key=lambda s: (0 if s == root else 1, str(s)))
    blocks = []
    for s in order:
        lines = [w.pred_obj(p, objs) for p, objs in w.group(by_s[s])]
        blocks.append(w.iri(s) + " " + " ;\n    ".join(lines) + " .")
    parts = []
    if header:
        parts.append("\n".join("# " + h if h else "#" for h in header))
    if w.used:
        parts.append("\n".join("@prefix %s: <%s> ." % (p, prefixes[p]) for p in sorted(w.used)))
    parts += blocks
    return "\n\n".join(parts) + "\n"
