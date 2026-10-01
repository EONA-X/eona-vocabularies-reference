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
<> a dcat:Dataset ; {title} dcat:version "1.0.0" ; dcat:type assettype:{asset_type} .
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
  write(root, "a/v1.0.0/metadata.ttl", &metadata(Some("A"), FORMAL_ONTOLOGY));
  write(
    root,
    "a/v1.0.0/ontology.ttl",
    &ontology("https://example.org/a", "<https://example.org/a/Thing> a owl:Class ."),
  );
  write(root, "b/v1.0.0/metadata.ttl", &metadata(Some("B"), FORMAL_ONTOLOGY));
  write(
    root,
    "b/v1.0.0/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:subClassOf <https://example.org/a/Thing> .",
    ),
  );
  write(root, "shapes/v1.0.0/metadata.ttl", &metadata(Some("Shapes"), MARKUP_SCHEMA));
  write(
    root,
    "shapes/v1.0.0/ontology.ttl",
    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n<https://example.org/s/S> a sh:NodeShape .\n",
  );
  write(root, "crosswalk-a-b/v1.0.0/metadata.ttl", &metadata(Some("A to B"), ALIGNMENT));
  write(
    root,
    "crosswalk-a-b/v1.0.0/alignment.ttl",
    r#"@prefix void: <http://rdfs.org/ns/void#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<https://example.org/x/a-b> a void:Linkset ; rdfs:seeAlso <https://example.org/a/Thing>, <https://example.org/b/Other> .
"#,
  );
  write(root, "eonax-p/v1.0.0/metadata.ttl", &metadata(Some("P"), TERMINOLOGY));
  write(
    root,
    "eonax-p/v1.0.0/ontology.ttl",
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
  write(root.path(), "a/v1.0.0/catalog-fragment.ttl", "this is not turtle");

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("a/v1.0.0: catalog-fragment.ttl"), "{found:?}");
}

#[test]
fn metadata_without_a_title_is_a_finding() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(root.path(), "a/v1.0.0/metadata.ttl", &metadata(None, FORMAL_ONTOLOGY));

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("a/v1.0.0: ") && found[0].contains("dcterms:title"), "{found:?}");
}

#[test]
fn a_formal_ontology_must_declare_an_owl_ontology_but_a_shapes_graph_need_not() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "a/v1.0.0/ontology.ttl",
    "<https://example.org/a/Thing> a <http://www.w3.org/2002/07/owl#Class> .\n",
  );

  let found = messages(root.path());

  assert!(found.iter().any(|f| f.starts_with("a/v1.0.0: ") && f.contains("owl:Ontology")), "{found:?}");
  assert!(!found.iter().any(|f| f.starts_with("shapes/v1.0.0: ")), "{found:?}");
}

#[test]
fn a_crosswalk_must_link_at_least_two_published_vocabularies() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "crosswalk-a-b/v1.0.0/alignment.ttl",
    r#"@prefix void: <http://rdfs.org/ns/void#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<https://example.org/x/a-b> a void:Linkset ; rdfs:seeAlso <https://example.org/a/Thing>, <https://example.org/nowhere/X> .
"#,
  );

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("crosswalk-a-b/v1.0.0: ") && found[0].contains("2"), "{found:?}");
}

#[test]
fn a_crosswalk_needs_an_alignment_graph_with_a_void_linkset() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "crosswalk-a-b/v1.0.0/alignment.ttl",
    "<https://example.org/x/a-b> a <http://www.w3.org/2004/02/skos/core#ConceptScheme> .\n",
  );
  write(root.path(), "c/v1.0.0/metadata.ttl", &metadata(Some("C"), ALIGNMENT));

  let found = messages(root.path());

  assert!(
    found.iter().any(|f| f.starts_with("crosswalk-a-b/v1.0.0: ") && f.contains("void:Linkset")),
    "{found:?}"
  );
  assert!(found.iter().any(|f| f.starts_with("c/v1.0.0: ") && f.contains("alignment.ttl")), "{found:?}");
}

#[test]
fn referencing_an_unpublished_hub_ontology_is_a_finding() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // An ontology in the repository without metadata.ttl: part of the hub, not published.
  write(root.path(), "hidden/ontology.ttl", &ontology("https://example.org/hidden", ""));
  write(
    root.path(),
    "b/v1.0.0/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:subClassOf <https://example.org/hidden/Base> .",
    ),
  );

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(
    found[0].starts_with("b/v1.0.0: ") && found[0].contains("https://example.org/hidden") && found[0].contains("hidden/"),
    "{found:?}"
  );
}

#[test]
fn the_eona_x_eu_publication_rules_apply_to_every_directory_and_all_findings_are_reported() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // Not an eonax-* directory, yet minted under eona-x.eu: the convention applies.
  write(root.path(), "q/v1.0.0/metadata.ttl", &metadata(Some("Q"), TERMINOLOGY));
  write(
    root.path(),
    "q/v1.0.0/ontology.ttl",
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://eona-x.eu/vocabulary/q/v2.0.0#> a owl:Ontology ; owl:versionInfo \"1.0.0\" .\n",
  );
  write(root.path(), "a/v1.0.0/metadata.ttl", &metadata(None, FORMAL_ONTOLOGY));

  let found = messages(root.path());

  assert_eq!(found.len(), 2, "{found:?}");
  assert!(
    found.iter().any(|f| f.starts_with("q/v1.0.0: ") && f.contains("v2.0.0") && f.contains("1.0.0")),
    "{found:?}"
  );
  assert!(found.iter().any(|f| f.starts_with("a/v1.0.0: ")), "{found:?}");
}

#[test]
fn metadata_may_declare_its_graph_file_instead_of_ontology_ttl() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  let declared = format!(
    "{}<> dcat:distribution [ a dcat:Distribution ; dcat:downloadURL <cargo-model.ttl> ; dcat:mediaType \"text/turtle\" ] .\n",
    metadata(Some("Cargo"), FORMAL_ONTOLOGY)
  );
  write(root.path(), "cargo/v1.0.0/metadata.ttl", &declared);
  write(
    root.path(),
    "cargo/v1.0.0/cargo-model.ttl",
    &ontology("https://example.org/cargo", "<https://example.org/cargo/Item> a owl:Class ."),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());

  fs::remove_file(root.path().join("cargo/v1.0.0/cargo-model.ttl")).unwrap();
  let found = messages(root.path());
  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("cargo/v1.0.0: ") && found[0].contains("cargo-model.ttl"), "{found:?}");
}

#[test]
fn an_iri_on_an_eona_x_host_must_follow_the_publication_convention() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // Minted on the Hub UI's host, over http, without version (as a contribution did).
  write(root.path(), "mcv/v1.0.0/metadata.ttl", &metadata(Some("MCV"), TERMINOLOGY));
  write(
    root.path(),
    "mcv/v1.0.0/ontology.ttl",
    "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n<http://vocabulary.eona-x.eu/vocabulary/mcv> a skos:ConceptScheme .\n<http://vocabulary.eona-x.eu/vocabulary/mcv/a> a skos:Concept .\n",
  );
  // The pre-#677 hub namespace and the w3id.org/eonax redirector, used as objects.
  write(
    root.path(),
    "b/v1.0.0/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:seeAlso <https://vocab.eona-x.eu/netex/Stop>, <https://w3id.org/eonax/credentials/MembershipCredential> .",
    ),
  );
  // An Eona-X predicate in metadata.ttl is an IRI like any other.
  write(
    root.path(),
    "a/v1.0.0/metadata.ttl",
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
        .any(|f| f.starts_with(&format!("{dir}/v1.0.0: ")) && f.contains(iri) && f.contains("<asset-type>/<slug>/<version>")),
      "{dir} {iri}: {found:?}"
    );
  }
  // One finding per file and namespace, not one per term.
  assert_eq!(found.iter().filter(|f| f.starts_with("mcv/v1.0.0: ")).count(), 1, "{found:?}");
}

#[test]
fn convention_iris_and_the_bare_site_roots_are_fine() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "b/v1.0.0/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:seeAlso <https://eona-x.eu/vocabulary/p/v1.0.0#Term>, <https://eona-x.eu/>, <https://vocabulary.eona-x.eu/> .",
    ),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

#[test]
fn an_asset_directly_under_its_slug_must_move_into_a_version_directory() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(root.path(), "old/metadata.ttl", &metadata(Some("Old"), FORMAL_ONTOLOGY));
  write(root.path(), "old/ontology.ttl", &ontology("https://example.org/old", ""));

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(found[0].starts_with("old: ") && found[0].contains("old/v1.0.0/"), "{found:?}");
}

#[test]
fn a_version_is_required_and_names_its_directory() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(root.path(), "a/v1.0.0/metadata.ttl", &metadata(Some("A"), FORMAL_ONTOLOGY).replace("dcat:version \"1.0.0\" ;", ""));
  write(root.path(), "b/v2.0.0/metadata.ttl", &metadata(Some("B2"), FORMAL_ONTOLOGY));
  write(root.path(), "b/v2.0.0/ontology.ttl", &ontology("https://example.org/b2", ""));

  let found = messages(root.path());

  assert!(found.iter().any(|f| f.starts_with("a/v1.0.0: ") && f.contains("dcat:version")), "{found:?}");
  assert!(found.iter().any(|f| f.starts_with("b/v2.0.0: ") && f.contains("v1.0.0") && f.contains("v2.0.0")), "{found:?}");
  assert_eq!(found.len(), 2, "{found:?}");
}

#[test]
fn several_versions_of_an_asset_are_checked_side_by_side() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(root.path(), "a/v2.0.0/metadata.ttl", &metadata(Some("A"), FORMAL_ONTOLOGY).replace("\"1.0.0\"", "\"2.0.0\""));
  write(root.path(), "a/v2.0.0/ontology.ttl", &ontology("https://example.org/a2", "<https://example.org/a2/Thing> rdfs:subClassOf <https://example.org/a/Thing> ."));

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

#[test]
fn an_eona_x_eu_version_must_agree_with_the_metadata() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(root.path(), "eonax-p/v1.0.0/metadata.ttl", &metadata(Some("P"), TERMINOLOGY).replace("\"1.0.0\"", "\"1.0.1\""));

  let found = messages(root.path());

  // Directory v1.0.0, IRI v1.0.0 and owl:versionInfo 1.0.0, but dcat:version 1.0.1.
  assert!(found.iter().any(|f| f.starts_with("eonax-p/v1.0.0: ") && f.contains("1.0.1")), "{found:?}");
}
