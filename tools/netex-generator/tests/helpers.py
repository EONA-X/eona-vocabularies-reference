"""Shared helpers: load the fixture schema, or a schema written inline for one rule."""
import os
import tempfile

from rdflib import URIRef

from netexgen import netex_owl
from netexgen.xsd_load import load

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_XSD = os.path.join(HERE, "fixtures", "netex", "xsd")
SCHEMA = ('<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://www.netex.org.uk/netex" '
          'xmlns:netex="http://www.netex.org.uk/netex" xmlns:gml="http://www.opengis.net/gml/3.2" '
          'targetNamespace="http://www.netex.org.uk/netex">%s</xsd:schema>')


def fixture_model():
    return load(FIXTURE_XSD, "NeTEx_publication.xsd")


def inline_model(body):
    """Model of one schema file made of `body`."""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.xsd"), "w", encoding="utf-8") as f:
            f.write(SCHEMA % body)
        return load(d, "a.xsd")


def iri(name):
    return URIRef(netex_owl.NS + name)


def objects(triples, s, p):
    return {o for ss, pp, o in triples if ss == s and pp == p}
