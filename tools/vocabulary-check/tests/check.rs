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
  write(
    root.path(),
    "a/v1.0.0/metadata.ttl",
    &metadata(Some("A"), FORMAL_ONTOLOGY).replace("dcat:version \"1.0.0\" ;", ""),
  );
  write(root.path(), "b/v2.0.0/metadata.ttl", &metadata(Some("B2"), FORMAL_ONTOLOGY));
  write(root.path(), "b/v2.0.0/ontology.ttl", &ontology("https://example.org/b2", ""));

  let found = messages(root.path());

  assert!(found.iter().any(|f| f.starts_with("a/v1.0.0: ") && f.contains("dcat:version")), "{found:?}");
  assert!(
    found
      .iter()
      .any(|f| f.starts_with("b/v2.0.0: ") && f.contains("v1.0.0") && f.contains("v2.0.0")),
    "{found:?}"
  );
  assert_eq!(found.len(), 2, "{found:?}");
}

#[test]
fn several_versions_of_an_asset_are_checked_side_by_side() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "a/v2.0.0/metadata.ttl",
    &metadata(Some("A"), FORMAL_ONTOLOGY).replace("\"1.0.0\"", "\"2.0.0\""),
  );
  write(
    root.path(),
    "a/v2.0.0/ontology.ttl",
    &ontology(
      "https://example.org/a2",
      "<https://example.org/a2/Thing> rdfs:subClassOf <https://example.org/a/Thing> .",
    ),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

#[test]
fn an_eona_x_eu_version_must_agree_with_the_metadata() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "eonax-p/v1.0.0/metadata.ttl",
    &metadata(Some("P"), TERMINOLOGY).replace("\"1.0.0\"", "\"1.0.1\""),
  );

  let found = messages(root.path());

  // Directory v1.0.0, IRI v1.0.0 and owl:versionInfo 1.0.0, but dcat:version 1.0.1.
  assert!(found.iter().any(|f| f.starts_with("eonax-p/v1.0.0: ") && f.contains("1.0.1")), "{found:?}");
}

fn vendored(root: &Path, slug: &str, ns: &str) {
  write(
    root,
    &format!("{slug}/v1.0.0/metadata.ttl"),
    &format!(
      "{}<> dcterms:creator [ a <http://xmlns.com/foaf/0.1/Agent> ; <http://xmlns.com/foaf/0.1/name> \"CEN\" ] .\n",
      metadata(Some(slug), FORMAL_ONTOLOGY)
    ),
  );
  write(
    root,
    &format!("{slug}/v1.0.0/ontology.ttl"),
    &format!("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<{ns}> a owl:Ontology ; owl:versionInfo \"1.0.0\" .\n<{ns}Stop> a owl:Class .\n"),
  );
}

#[test]
fn a_vendored_representation_on_the_vocabulary_host_is_fine() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  vendored(root.path(), "netex", "https://vocabulary.eona-x.eu/ontology/netex/v1.0.0#");

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

#[test]
fn one_asset_type_and_slug_cannot_be_on_both_hosts() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // eonax-p publishes https://eona-x.eu/vocabulary/p/…; a vendored "p" may not take the same path.
  write(
    root.path(),
    "other-p/v1.0.0/metadata.ttl",
    &format!(
      "{}<> dcterms:creator [ <http://xmlns.com/foaf/0.1/name> \"X\" ] .\n",
      metadata(Some("Other P"), TERMINOLOGY)
    ),
  );
  write(
    root.path(),
    "other-p/v1.0.0/ontology.ttl",
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://vocabulary.eona-x.eu/vocabulary/p/v1.0.0#> a owl:Ontology ; owl:versionInfo \"1.0.0\" .\n",
  );

  let found = messages(root.path());

  assert!(found.iter().any(|f| f.contains("vocabulary/p") && f.contains("both")), "{found:?}");
}

#[test]
fn the_hub_build_accepts_every_repository_the_gate_accepts() {
  // vocabulary-hub-build runs `discover` on what this gate let through: a green
  // gate must never leave the hub unable to build.
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  assert_eq!(messages(root.path()), Vec::<String>::new());

  let found = eona_vocabulary_check::discover(root.path(), eona_vocabulary_check::SITE_BASE);

  assert!(found.is_ok(), "{}", found.err().unwrap_or_default());
}

/// `eonax-s`: a vocabulary whose terms live in the stable namespace
/// `https://eona-x.eu/vocabulary/s#`, released as `owl:versionIRI` (when given).
fn stable(root: &Path, version_iri: Option<&str>) {
  write(root, "eonax-s/v1.0.0/metadata.ttl", &metadata(Some("S"), TERMINOLOGY));
  let version_iri = version_iri.map(|v| format!("owl:versionIRI <{v}> ;")).unwrap_or_default();
  write(
    root,
    "eonax-s/v1.0.0/ontology.ttl",
    &format!(
      "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://eona-x.eu/vocabulary/s#> a owl:Ontology ; {version_iri} owl:versionInfo \"1.0.0\" .\n<https://eona-x.eu/vocabulary/s#GenericClaim> a owl:Class .\n"
    ),
  );
}

#[test]
fn a_stable_term_namespace_released_as_a_version_iri_is_fine_and_its_terms_may_be_used() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v1.0.0#"));
  write(
    root.path(),
    "b/v1.0.0/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:seeAlso <https://eona-x.eu/vocabulary/s#GenericClaim> .",
    ),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

#[test]
fn a_stable_term_namespace_without_a_version_iri_is_a_finding() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  stable(root.path(), None);

  let found = messages(root.path());

  assert!(
    found
      .iter()
      .any(|f| f.starts_with("eonax-s/v1.0.0: ") && f.contains("owl:versionIRI") && f.contains("https://eona-x.eu/vocabulary/s/v1.0.0#")),
    "{found:?}"
  );
}

#[test]
fn a_mismatched_version_iri_is_a_finding() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v2.0.0#"));

  let found = messages(root.path());

  assert!(found.iter().any(|f| f.starts_with("eonax-s/v1.0.0: ") && f.contains("v2.0.0")), "{found:?}");
}

#[test]
fn a_stable_release_must_agree_with_the_metadata() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  // versionIRI v1.0.1 and owl:versionInfo 1.0.1, but directory v1.0.0 and dcat:version 1.0.0.
  stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v1.0.1#"));
  let path = root.path().join("eonax-s/v1.0.0/ontology.ttl");
  let ttl = fs::read_to_string(&path).unwrap().replace("\"1.0.0\"", "\"1.0.1\"");
  fs::write(path, ttl).unwrap();

  let found = messages(root.path());

  assert!(
    found
      .iter()
      .any(|f| f.starts_with("eonax-s/v1.0.0: ") && f.contains("1.0.1") && f.contains("1.0.0")),
    "{found:?}"
  );
}

#[test]
fn a_stable_form_of_a_namespace_no_asset_mints_is_off_convention() {
  // eonax-p is published only as https://eona-x.eu/vocabulary/p/v1.0.0#: an
  // IRI that drops the version is a typo, not a stable term namespace.
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  write(
    root.path(),
    "b/v1.0.0/ontology.ttl",
    &ontology(
      "https://example.org/b",
      "<https://example.org/b/Other> rdfs:seeAlso <https://eona-x.eu/vocabulary/p#legalName> .",
    ),
  );

  let found = messages(root.path());

  assert!(
    found.iter().any(
      |f| f.starts_with("b/v1.0.0: ontology.ttl: 1 IRI(s) under <https://eona-x.eu/vocabulary>") && f.contains("vocabulary/p#legalName")
        // The finding names the stable form too, and where it is accepted.
        && f.contains("<asset-type>/<slug>#")
    ),
    "{found:?}"
  );
}

#[test]
fn a_stable_term_whose_fragment_has_a_slash_is_fine() {
  // A code list embedded in the vocabulary: …#StatusCodes/active, the same
  // fragment the versioned form accepts.
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v1.0.0#"));
  let path = root.path().join("eonax-s/v1.0.0/ontology.ttl");
  let mut ttl = fs::read_to_string(&path).unwrap();
  ttl.push_str("<https://eona-x.eu/vocabulary/s#ConnectorSupport/pending> a <https://eona-x.eu/vocabulary/s#ConnectorSupport> .\n");
  fs::write(path, ttl).unwrap();

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

/// `crosswalk-a-b`'s void:Linkset, pointing at `targets`.
fn linkset(root: &Path, targets: &[&str]) {
  let targets = targets.iter().map(|t| format!("<{t}>")).collect::<Vec<_>>().join(", ");
  write(
    root,
    "crosswalk-a-b/v1.0.0/alignment.ttl",
    &format!(
      "@prefix void: <http://rdfs.org/ns/void#> .\n@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n<https://example.org/x/a-b> a void:Linkset ; rdfs:seeAlso {targets} .\n"
    ),
  );
}

#[test]
fn two_releases_of_one_stable_namespace_are_one_side_of_a_crosswalk() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v1.0.0#"));
  // A second release, v1.1.0, of the same stable namespace.
  write(
    root.path(),
    "eonax-s/v1.1.0/metadata.ttl",
    &metadata(Some("S"), TERMINOLOGY).replace("\"1.0.0\"", "\"1.1.0\""),
  );
  write(
    root.path(),
    "eonax-s/v1.1.0/ontology.ttl",
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://eona-x.eu/vocabulary/s#> a owl:Ontology ; owl:versionIRI <https://eona-x.eu/vocabulary/s/v1.1.0#> ; owl:priorVersion <https://eona-x.eu/vocabulary/s/v1.0.0#> ; owl:versionInfo \"1.1.0\" .\n<https://eona-x.eu/vocabulary/s#GenericClaim> a owl:Class .\n",
  );
  linkset(root.path(), &["https://eona-x.eu/vocabulary/s#"]);

  let found = messages(root.path());

  assert!(
    found.iter().any(|f| f.starts_with("crosswalk-a-b/v1.0.0: ") && f.contains("reach 1 published")),
    "{found:?}"
  );
}

#[test]
fn a_crosswalk_may_cite_a_stable_vocabulary_by_its_version_iri() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v1.0.0#"));
  linkset(root.path(), &["https://example.org/a/Thing", "https://eona-x.eu/vocabulary/s/v1.0.0#"]);

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

/// `eonax-<slug>/v<version>/`: a release of an eona-x.eu vocabulary, its root
/// `root` (the stable namespace, released as `owl:versionIRI`, when
/// `version_iri` is given), with `owl:priorVersion <prior>` when given.
fn release(root: &Path, slug: &str, version: &str, root_iri: &str, version_iri: Option<&str>, prior: Option<&str>) {
  write(
    root,
    &format!("eonax-{slug}/v{version}/metadata.ttl"),
    &metadata(Some(slug), TERMINOLOGY).replace("\"1.0.0\"", &format!("\"{version}\"")),
  );
  let version_iri = version_iri.map(|v| format!("owl:versionIRI <{v}> ;")).unwrap_or_default();
  let prior = prior.map(|p| format!("owl:priorVersion <{p}> ;")).unwrap_or_default();
  write(
    root,
    &format!("eonax-{slug}/v{version}/ontology.ttl"),
    &format!("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<{root_iri}> a owl:Ontology ; {version_iri} {prior} owl:versionInfo \"{version}\" .\n"),
  );
}

#[test]
fn a_prior_version_naming_the_previous_release_is_fine() {
  // Versioned v1.0.0, then the stable namespace from v1.1.0 on: each
  // owl:priorVersion names the previous directory's release IRI.
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  release(root.path(), "q", "1.0.0", "https://eona-x.eu/vocabulary/q/v1.0.0#", None, None);
  release(
    root.path(),
    "q",
    "1.1.0",
    "https://eona-x.eu/vocabulary/q#",
    Some("https://eona-x.eu/vocabulary/q/v1.1.0#"),
    Some("https://eona-x.eu/vocabulary/q/v1.0.0#"),
  );
  release(
    root.path(),
    "q",
    "1.2.0",
    "https://eona-x.eu/vocabulary/q#",
    Some("https://eona-x.eu/vocabulary/q/v1.2.0#"),
    Some("https://eona-x.eu/vocabulary/q/v1.1.0#"),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());
}

#[test]
fn a_release_after_another_without_a_prior_version_is_a_finding() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v1.0.0#"));
  release(
    root.path(),
    "s",
    "1.1.0",
    "https://eona-x.eu/vocabulary/s#",
    Some("https://eona-x.eu/vocabulary/s/v1.1.0#"),
    None,
  );

  let found = messages(root.path());

  assert_eq!(found.len(), 1, "{found:?}");
  assert!(
    found[0].starts_with("eonax-s/v1.1.0: ") && found[0].contains("owl:priorVersion") && found[0].contains("<https://eona-x.eu/vocabulary/s/v1.0.0#>"),
    "{found:?}"
  );
}

#[test]
fn a_prior_version_naming_another_release_is_a_finding_with_the_expected_iri() {
  // The stable namespace, or a release that is not the previous one, is not
  // the previous release's IRI.
  for wrong in ["https://eona-x.eu/vocabulary/s#", "https://eona-x.eu/vocabulary/s/v0.9.0#"] {
    let root = tempfile::tempdir().unwrap();
    clean(root.path());
    stable(root.path(), Some("https://eona-x.eu/vocabulary/s/v1.0.0#"));
    release(
      root.path(),
      "s",
      "1.1.0",
      "https://eona-x.eu/vocabulary/s#",
      Some("https://eona-x.eu/vocabulary/s/v1.1.0#"),
      Some(wrong),
    );

    let found = messages(root.path());

    assert_eq!(found.len(), 1, "{wrong}: {found:?}");
    assert!(
      found[0].starts_with("eonax-s/v1.1.0: ") && found[0].contains(&format!("<{wrong}>")) && found[0].contains("<https://eona-x.eu/vocabulary/s/v1.0.0#>"),
      "{found:?}"
    );
  }
}

#[test]
fn the_previous_release_of_a_versioned_namespace_is_the_namespace() {
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  release(
    root.path(),
    "p",
    "1.1.0",
    "https://eona-x.eu/vocabulary/p/v1.1.0#",
    None,
    // Itself, not the previous release.
    Some("https://eona-x.eu/vocabulary/p/v1.1.0#"),
  );

  let found = messages(root.path());

  // eonax-p/v1.0.0 (in the clean repository) is https://eona-x.eu/vocabulary/p/v1.0.0#.
  assert_eq!(found.len(), 1, "{found:?}");
  assert!(
    found[0].starts_with("eonax-p/v1.1.0: ") && found[0].contains("<https://eona-x.eu/vocabulary/p/v1.0.0#>"),
    "{found:?}"
  );
}

#[test]
fn releases_are_ordered_by_version_number_not_by_name() {
  // v1.10.0 follows v1.9.0, not v1.1.0 (which sorts between them by name).
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  let ns = "https://eona-x.eu/vocabulary/s#";
  let v = |n: &str| format!("https://eona-x.eu/vocabulary/s/v{n}#");
  stable(root.path(), Some(&v("1.0.0")));
  release(root.path(), "s", "1.9.0", ns, Some(&v("1.9.0")), Some(&v("1.0.0")));
  release(root.path(), "s", "1.10.0", ns, Some(&v("1.10.0")), Some(&v("1.9.0")));

  assert_eq!(messages(root.path()), Vec::<String>::new());

  release(root.path(), "s", "1.10.0", ns, Some(&v("1.10.0")), Some(&v("1.0.0")));
  let found = messages(root.path());
  assert_eq!(found.len(), 1, "{found:?}");
  assert!(
    found[0].starts_with("eonax-s/v1.10.0: ") && found[0].contains(&format!("<{}>", v("1.9.0"))),
    "{found:?}"
  );
}

#[test]
fn a_first_release_may_name_any_prior_version() {
  // An upstream release before this repository's first directory.
  let root = tempfile::tempdir().unwrap();
  clean(root.path());
  release(
    root.path(),
    "q",
    "1.0.0",
    "https://eona-x.eu/vocabulary/q/v1.0.0#",
    None,
    Some("https://example.org/q/releases/0.9/"),
  );

  assert_eq!(messages(root.path()), Vec::<String>::new());
}
