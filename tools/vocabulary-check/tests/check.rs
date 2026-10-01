//! The repository-wide gate: every finding, not just the first.

use std::fs;
use std::path::Path;

use eona_vocabulary_check::check;

const FORMAL_ONTOLOGY: &str = "c_89b4bdb7";
const MARKUP_SCHEMA: &str = "c_3948c2ed";
const ALIGNMENT: &str = "c_bba2bb35";
const TERMINOLOGY: &str = "c_64714767";

fn write(root: &Path, file: &str, content: &str) {
  let path = root.join(file);
  fs::create_dir_all(path.parent().unwrap()).unwrap();
  fs::write(path, content).unwrap();
}

fn metadata(title: Option<&str>, asset_type: &str) -> String {
  let title = title.map(|t| format!("dcterms:title \"{t}\"@en ;")).unwrap_or_default();
  format!(
    r#"@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix assettype: <http://publications.europa.eu/resource/authority/asset-classification/> .
<> a dcat:Dataset ; {title} dcat:type assettype:{asset_type} .
"#
  )
}

fn ontology(iri: &str, extra: &str) -> String {
  format!(
    r#"@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<{iri}> a owl:Ontology .
{extra}
"#
  )
}

/// A repository the gate accepts: two ontologies, a crosswalk between them,
/// a shapes graph without a root, an eona-x.eu vocabulary, and the
/// directories that are not vocabularies at all.
fn clean(root: &Path) {
  write(root, "a/metadata.ttl", &metadata(Some("A"), FORMAL_ONTOLOGY));
  write(
    root,
    "a/ontology.ttl",
    &ontology("https://example.org/a", "<https://example.org/a/Thing> a owl:Class ."),
  );
  write(root, "b/metadata.ttl", &metadata(Some("B"), FORMAL_ONTOLOGY));
  write(
    root,
    "b/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:subClassOf <https://example.org/a/Thing> .",
    ),
  );
  write(root, "shapes/metadata.ttl", &metadata(Some("Shapes"), MARKUP_SCHEMA));
  write(
    root,
    "shapes/ontology.ttl",
    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n<https://example.org/s/S> a sh:NodeShape .\n",
  );
  write(root, "crosswalk-a-b/metadata.ttl", &metadata(Some("A to B"), ALIGNMENT));
  write(
    root,
    "crosswalk-a-b/alignment.ttl",
    r#"@prefix void: <http://rdfs.org/ns/void#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<https://example.org/x/a-b> a void:Linkset ; rdfs:seeAlso <https://example.org/a/Thing>, <https://example.org/b/Other> .
"#,
  );
  write(root, "eonax-p/metadata.ttl", &metadata(Some("P"), TERMINOLOGY));
  write(
    root,
    "eonax-p/ontology.ttl",
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://eona-x.eu/vocabulary/p/v1.0.0#> a owl:Ontology ; owl:versionInfo \"1.0.0\" .\n",
  );
  write(root, "assets/README.md", "pictures");
  write(root, "tools/vocabulary-check/Cargo.toml", "[package]");
}

fn messages(root: &Path) -> Vec<String> {
  check(root).into_iter().map(|f| format!("{}: {}", f.dir, f.message)).collect()
}

#[test]
fn a_clean_repository_has_no_findings() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

#[test]
fn turtle_that_does_not_parse_is_a_finding_naming_the_file() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(root.path(), "a/catalog-fragment.ttl", "this is not turtle");

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("a: catalog-fragment.ttl"), "{found:?}");
}

#[test]
fn metadata_without_a_title_is_a_finding() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(root.path(), "a/metadata.ttl", &metadata(None, FORMAL_ONTOLOGY));

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("a: ") && found[0].contains("dcterms:title"), "{found:?}");
}

#[test]
fn a_formal_ontology_must_declare_an_owl_ontology_but_a_shapes_graph_need_not() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "a/ontology.ttl",
    "<https://example.org/a/Thing> a <http://www.w3.org/2002/07/owl#Class> .\n",
  );

  let found = messages(root.path());

  assert!(found.iter().any(|f| f.starts_with("a: ") && f.contains("owl:Ontology")), "{found:?}");
  assert!(!found.iter().any(|f| f.starts_with("shapes: ")), "{found:?}");
}

#[test]
fn a_crosswalk_must_link_at_least_two_published_vocabularies() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "crosswalk-a-b/alignment.ttl",
    r#"@prefix void: <http://rdfs.org/ns/void#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<https://example.org/x/a-b> a void:Linkset ; rdfs:seeAlso <https://example.org/a/Thing>, <https://example.org/nowhere/X> .
"#,
  );

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("crosswalk-a-b: ") && found[0].contains("2"), "{found:?}");
}

#[test]
fn a_crosswalk_needs_an_alignment_graph_with_a_void_linkset() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "crosswalk-a-b/alignment.ttl",
    "<https://example.org/x/a-b> a <http://www.w3.org/2004/02/skos/core#ConceptScheme> .\n",
  );
  write(root.path(), "c/metadata.ttl", &metadata(Some("C"), ALIGNMENT));

  let found = messages(root.path());

  assert!(
    found.iter().any(|f| f.starts_with("crosswalk-a-b: ") && f.contains("void:Linkset")),
    "{found:?}"
  );
  assert!(found.iter().any(|f| f.starts_with("c: ") && f.contains("alignment.ttl")), "{found:?}");
}

#[test]
fn referencing_an_unpublished_hub_ontology_is_a_finding() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // An ontology in the repository without metadata.ttl: part of the hub, not published.
  write(root.path(), "hidden/ontology.ttl", &ontology("https://example.org/hidden", ""));
  write(
    root.path(),
    "b/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:subClassOf <https://example.org/hidden/Base> .",
    ),
  );

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(
    found[0].starts_with("b: ") && found[0].contains("https://example.org/hidden") && found[0].contains("hidden/"),
    "{found:?}"
  );
}

#[test]
fn the_eona_x_eu_publication_rules_apply_to_every_directory_and_all_findings_are_reported() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // Not an eonax-* directory, yet minted under eona-x.eu: the convention applies.
  write(root.path(), "q/metadata.ttl", &metadata(Some("Q"), TERMINOLOGY));
  write(
    root.path(),
    "q/ontology.ttl",
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://eona-x.eu/vocabulary/q/v2.0.0#> a owl:Ontology ; owl:versionInfo \"1.0.0\" .\n",
  );
  write(root.path(), "a/metadata.ttl", &metadata(None, FORMAL_ONTOLOGY));

  let found = messages(root.path());

  assert_eq!(found.len(), 2, "{found:?}");
  assert!(
    found.iter().any(|f| f.starts_with("q: ") && f.contains("v2.0.0") && f.contains("1.0.0")),
    "{found:?}"
  );
  assert!(found.iter().any(|f| f.starts_with("a: ")), "{found:?}");
}

#[test]
fn metadata_may_declare_its_graph_file_instead_of_ontology_ttl() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  let declared = format!(
    "{}<> dcat:distribution [ a dcat:Distribution ; dcat:downloadURL <cargo-model.ttl> ; dcat:mediaType \"text/turtle\" ] .\n",
    metadata(Some("Cargo"), FORMAL_ONTOLOGY)
  );
  write(root.path(), "cargo/metadata.ttl", &declared);
  write(
    root.path(),
    "cargo/cargo-model.ttl",
    &ontology("https://example.org/cargo", "<https://example.org/cargo/Item> a owl:Class ."),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());

  fs::remove_file(root.path().join("cargo/cargo-model.ttl")).unwrap();
  let found = messages(root.path());
  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("cargo: ") && found[0].contains("cargo-model.ttl"), "{found:?}");
}

#[test]
fn an_iri_on_an_eona_x_host_must_follow_the_publication_convention() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // Minted on the Hub UI's host, over http, without version (as a contribution did).
  write(root.path(), "mcv/metadata.ttl", &metadata(Some("MCV"), TERMINOLOGY));
  write(
    root.path(),
    "mcv/ontology.ttl",
    "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n<http://vocabulary.eona-x.eu/vocabulary/mcv> a skos:ConceptScheme .\n<http://vocabulary.eona-x.eu/vocabulary/mcv/a> a skos:Concept .\n",
  );
  // The pre-#677 hub namespace and the w3id.org/eonax redirector, used as objects.
  write(
    root.path(),
    "b/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:seeAlso <https://vocab.eona-x.eu/netex/Stop>, <https://w3id.org/eonax/credentials/MembershipCredential> .",
    ),
  );
  // An Eona-X predicate in metadata.ttl is an IRI like any other.
  write(
    root.path(),
    "a/metadata.ttl",
    &format!("{}<> <https://vocab.eona-x.eu/logo> \"a.png\" .\n", metadata(Some("A"), FORMAL_ONTOLOGY)),
  );

  let found = messages(root.path());

  for (dir, iri) in [
    ("mcv", "http://vocabulary.eona-x.eu/vocabulary/mcv"),
    ("b", "https://vocab.eona-x.eu/netex"),
    ("b", "https://w3id.org/eonax/credentials"),
    ("a", "https://vocab.eona-x.eu/logo"),
  ] {
    assert!(
      found
        .iter()
        .any(|f| f.starts_with(&format!("{dir}: ")) && f.contains(iri) && f.contains("<asset-type>/<slug>/<version>")),
      "{dir} {iri}: {found:?}"
    );
  }
  // One finding per file and namespace, not one per term.
  assert_eq!(found.iter().filter(|f| f.starts_with("mcv: ")).count(), 1, "{found:?}");
}

#[test]
fn convention_iris_and_the_bare_site_roots_are_fine() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "b/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:seeAlso <https://eona-x.eu/vocabulary/p/v1.0.0#Term>, <https://eona-x.eu/>, <https://vocabulary.eona-x.eu/> .",
    ),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());
}
