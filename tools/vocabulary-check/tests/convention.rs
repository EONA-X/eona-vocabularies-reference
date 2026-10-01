use std::fs;
use std::path::Path;

use eona_vocabulary_check::{SITE_BASE, VENDORED_BASE, discover};

/// An asset version: `<dir>/v<owl:versionInfo>/ontology.ttl` (`v0` without one).
fn vocab(root: &Path, dir: &str, ontology_ttl: &str) {
  let version = ontology_ttl.split("owl:versionInfo \"").nth(1).and_then(|r| r.split('"').next()).unwrap_or("0");
  let version_dir = root.join(dir).join(format!("v{version}"));
  fs::create_dir_all(&version_dir).unwrap();
  fs::write(version_dir.join("ontology.ttl"), ontology_ttl).unwrap();
}

/// The single version directory of `dir`.
fn version_dir(root: &Path, dir: &str) -> std::path::PathBuf {
  fs::read_dir(root.join(dir)).unwrap().map(|e| e.unwrap().path()).find(|p| p.is_dir()).unwrap()
}

/// The DCAT/ADMS self-description upstream ships next to each ontology, with
/// its EU asset-classification `dcat:type`.
fn metadata(root: &Path, dir: &str, asset_type: &str) {
  fs::write(
    version_dir(root, dir).join("metadata.ttl"),
    format!(
      r#"@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix assettype: <http://publications.europa.eu/resource/authority/asset-classification/> .
<> a dcat:Dataset ; dcat:type assettype:{asset_type} .
"#
    ),
  )
  .unwrap();
}

fn ontology(namespace: &str, version_info: &str) -> String {
  format!(
    r#"@prefix ex: <{namespace}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex: a owl:Ontology ; owl:versionInfo "{version_info}" ; rdfs:label "Example"@en .
ex:Thing rdfs:label "Thing"@en ; rdfs:isDefinedBy ex: .
"#
  )
}

fn concept_scheme(namespace: &str, version_info: &str) -> String {
  format!(
    r#"@prefix ex: <{namespace}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
ex: a skos:ConceptScheme ; owl:versionInfo "{version_info}" ; skos:prefLabel "Example codes"@en .
ex:A a skos:Concept ; skos:inScheme ex: ; skos:prefLabel "A"@en .
"#
  )
}

#[test]
fn a_vocabulary_minted_under_the_site_base_is_published_at_its_asset_type_slug_and_version() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "eonax-odrl-profile",
    &ontology("https://eona-x.eu/vocabulary/odrl-profile/v0.0.1#", "0.0.1"),
  );

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert_eq!(found.published.len(), 1);
  let v = &found.published[0];
  assert_eq!(v.dir_name, "eonax-odrl-profile/v0.0.1");
  assert_eq!(v.namespace, "https://eona-x.eu/vocabulary/odrl-profile/v0.0.1#");
  assert_eq!(v.kind, "vocabulary");
  assert_eq!(v.slug, "odrl-profile");
  assert_eq!(v.version, "v0.0.1");
  assert_eq!(v.triples.len(), 5);
  assert!(
    v.prefixes
      .iter()
      .any(|(p, iri)| p == "ex" && iri == "https://eona-x.eu/vocabulary/odrl-profile/v0.0.1#")
  );
}

#[test]
fn every_asset_type_of_the_convention_is_accepted() {
  let root = tempfile::tempdir().unwrap();
  for asset_type in ["ontology", "shape", "crosswalk", "vocabulary", "codelist"] {
    vocab(
      root.path(),
      &format!("eonax-{asset_type}"),
      &ontology(&format!("https://eona-x.eu/{asset_type}/x/v1.0.0#"), "1.0.0"),
    );
  }

  let found = discover(root.path(), SITE_BASE).unwrap();

  let mut types: Vec<_> = found.published.iter().map(|v| v.kind.as_str()).collect();
  types.sort();
  assert_eq!(types, ["codelist", "crosswalk", "ontology", "shape", "vocabulary"]);
}

#[test]
fn a_code_list_rooted_in_a_skos_concept_scheme_is_published() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "eonax-roles", &concept_scheme("https://eona-x.eu/codelist/roles/v1.0.0#", "1.0.0"));

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert_eq!(found.published.len(), 1);
  assert_eq!(found.published[0].kind, "codelist");
  assert_eq!(found.published[0].slug, "roles");
}

#[test]
fn a_vocabulary_still_minted_elsewhere_is_skipped_with_its_namespace_as_the_reason() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "eonax-credentials", &ontology("https://w3id.org/eonax/credentials/", "0.1.0"));

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert!(found.published.is_empty());
  assert_eq!(found.skipped.len(), 1);
  assert_eq!(found.skipped[0].dir_name, "eonax-credentials/v0.1.0");
  assert!(
    found.skipped[0].reason.contains("https://w3id.org/eonax/credentials/"),
    "{}",
    found.skipped[0].reason
  );
}

#[test]
fn a_version_segment_that_disagrees_with_owl_version_info_fails_the_build() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "eonax-odrl-profile",
    &ontology("https://eona-x.eu/vocabulary/odrl-profile/v0.0.2#", "0.0.1"),
  );

  let err = discover(root.path(), SITE_BASE).err().expect("mismatched version must not publish");

  assert!(err.contains("v0.0.2") && err.contains("0.0.1"), "{err}");
}

#[test]
fn the_former_slug_version_form_without_an_asset_type_fails_the_build() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "eonax-odrl-profile", &ontology("https://eona-x.eu/odrl-profile/v0.0.1#", "0.0.1"));

  let err = discover(root.path(), SITE_BASE)
    .err()
    .expect("an IRI under the site base without an asset type must not publish");

  assert!(err.contains("<asset-type>/<slug>/<version>"), "{err}");
}

#[test]
fn an_unknown_asset_type_fails_the_build() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "eonax-x", &ontology("https://eona-x.eu/dataset/x/v1.0.0#", "1.0.0"));

  let err = discover(root.path(), SITE_BASE).err().expect("an unknown asset type must not publish");

  assert!(
    err.contains("dataset") && err.contains("ontology, shape, crosswalk, vocabulary, codelist"),
    "{err}"
  );
}

#[test]
fn a_concept_code_is_not_an_asset_type() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "eonax-odrl-profile",
    &ontology("https://eona-x.eu/c_89b4bdb7/odrl-profile/v0.0.1#", "0.0.1"),
  );

  let err = discover(root.path(), SITE_BASE).err().expect("a concept code is not a semantic segment");

  assert!(err.contains("c_89b4bdb7") && err.contains("vocabulary"), "{err}");
}

#[test]
fn the_asset_type_must_cover_the_eu_asset_classification_declared_in_metadata() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "eonax-roles", &ontology("https://eona-x.eu/codelist/roles/v1.0.0#", "1.0.0"));
  metadata(root.path(), "eonax-roles", "c_89b4bdb7"); // Formal ontology

  let err = discover(root.path(), SITE_BASE)
    .err()
    .expect("a codelist IRI on a Formal ontology must not publish");

  assert!(err.contains("codelist") && err.contains("c_89b4bdb7"), "{err}");
}

#[test]
fn a_code_list_is_not_a_vocabulary_even_though_the_eu_table_nests_it_under_terminology() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "eonax-roles", &ontology("https://eona-x.eu/vocabulary/roles/v1.0.0#", "1.0.0"));
  metadata(root.path(), "eonax-roles", "c_cdd11291"); // Code list

  let err = discover(root.path(), SITE_BASE).err().expect("a Code list must be published as codelist");

  assert!(err.contains("c_cdd11291") && err.contains("codelist"), "{err}");
}

#[test]
fn each_asset_type_covers_its_eu_asset_classification_concepts() {
  // asset type, a concept of the EU asset-classification table it covers
  let cases = [
    ("ontology", "c_89b4bdb7"),   // Formal ontology
    ("shape", "c_b37963b3"),      // Application profile
    ("shape", "c_3948c2ed"),      // Markup schema
    ("crosswalk", "c_bba2bb35"),  // Alignment
    ("vocabulary", "c_64714767"), // Terminology
    ("vocabulary", "c_a7773248"), // Thesaurus
    ("vocabulary", "c_ebfb658e"), // Glossary
    ("codelist", "c_cdd11291"),   // Code list
    ("codelist", "c_5b130cc6"),   // Authority file
  ];
  let root = tempfile::tempdir().unwrap();
  for (i, (asset_type, code)) in cases.iter().enumerate() {
    let dir = format!("eonax-{i}");
    vocab(root.path(), &dir, &ontology(&format!("https://eona-x.eu/{asset_type}/x{i}/v1.0.0#"), "1.0.0"));
    metadata(root.path(), &dir, code);
    if *code == "c_bba2bb35" {
      // A crosswalk's graph file defaults to alignment.ttl.
      let v = version_dir(root.path(), &dir);
      fs::rename(v.join("ontology.ttl"), v.join("alignment.ttl")).unwrap();
    }
  }

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert_eq!(found.published.len(), cases.len());
}

#[test]
fn published_vocabularies_come_out_in_directory_name_order() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "eonax-b", &ontology("https://eona-x.eu/ontology/b/v1.0.0#", "1.0.0"));
  vocab(root.path(), "eonax-a", &ontology("https://eona-x.eu/ontology/a/v1.0.0#", "1.0.0"));

  let found = discover(root.path(), SITE_BASE).unwrap();

  let slugs: Vec<_> = found.published.iter().map(|v| v.slug.as_str()).collect();
  assert_eq!(slugs, ["a", "b"]);
}

#[test]
fn code_lists_embedded_under_the_namespace_are_not_extra_roots() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "eonax-bp",
    r#"@prefix ex: <https://eona-x.eu/ontology/bp/v0.1.0#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
ex: a owl:Ontology ; owl:versionInfo "0.1.0" .
<https://eona-x.eu/ontology/bp/v0.1.0#StatusCodes> a skos:ConceptScheme .
<https://eona-x.eu/ontology/bp/v0.1.0#StatusCodes/active> a skos:Concept ; skos:inScheme <https://eona-x.eu/ontology/bp/v0.1.0#StatusCodes> .
"#,
  );

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert_eq!(found.published.len(), 1);
  assert_eq!(found.published[0].namespace, "https://eona-x.eu/ontology/bp/v0.1.0#");
}

#[test]
fn two_namespace_roots_are_still_an_error() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "eonax-bp",
    r#"@prefix owl: <http://www.w3.org/2002/07/owl#> .
<https://eona-x.eu/ontology/bp/v0.1.0#> a owl:Ontology ; owl:versionInfo "0.1.0" .
<https://eona-x.eu/ontology/other/v0.1.0#> a owl:Ontology ; owl:versionInfo "0.1.0" .
"#,
  );

  let err = discover(root.path(), SITE_BASE).err().expect("two namespaces in one asset must not publish");

  assert!(err.contains("more than one"), "{err}");
}

#[test]
fn several_versions_of_an_eona_x_eu_vocabulary_are_all_published() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "eonax-odrl-profile",
    &ontology("https://eona-x.eu/vocabulary/odrl-profile/v0.0.1#", "0.0.1"),
  );
  vocab(
    root.path(),
    "eonax-odrl-profile",
    &ontology("https://eona-x.eu/vocabulary/odrl-profile/v0.1.0#", "0.1.0"),
  );

  let found = discover(root.path(), SITE_BASE).unwrap();

  let versions: Vec<_> = found.published.iter().map(|v| (v.slug.as_str(), v.version.as_str())).collect();
  assert_eq!(versions, [("odrl-profile", "v0.0.1"), ("odrl-profile", "v0.1.0")]);
}

#[test]
fn a_vocabulary_minted_under_the_site_base_is_published_whatever_its_directory_is_called() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "battery-pass",
    &ontology("https://eona-x.eu/ontology/battery-pass/v0.1.0#", "0.1.0"),
  );

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert_eq!(found.published.len(), 1);
  assert_eq!(found.published[0].dir_name, "battery-pass/v0.1.0");
}

/// The metadata of an Eona-X representation of an external standard: it names
/// the standard's body as dcterms:creator.
fn vendored_metadata(root: &Path, dir: &str, asset_type: &str) {
  fs::write(
    version_dir(root, dir).join("metadata.ttl"),
    format!(
      r#"@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix assettype: <http://publications.europa.eu/resource/authority/asset-classification/> .
<> a dcat:Dataset ; dcat:type assettype:{asset_type} ; dcterms:creator [ a foaf:Agent ; foaf:name "CEN" ] .
"#
    ),
  )
  .unwrap();
}

#[test]
fn a_vendored_representation_is_published_on_the_vocabulary_host() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "netex", &ontology("https://vocabulary.eona-x.eu/ontology/netex/v0.2.0#", "0.2.0"));
  vendored_metadata(root.path(), "netex", "c_89b4bdb7");

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert_eq!(found.published.len(), 1);
  let v = &found.published[0];
  assert_eq!(v.base, VENDORED_BASE);
  assert_eq!((v.kind.as_str(), v.slug.as_str(), v.version.as_str()), ("ontology", "netex", "v0.2.0"));
}

#[test]
fn a_vendored_representation_minted_on_the_authored_host_fails_the_build() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "netex", &ontology("https://eona-x.eu/ontology/netex/v0.2.0#", "0.2.0"));
  vendored_metadata(root.path(), "netex", "c_89b4bdb7");

  let err = discover(root.path(), SITE_BASE)
    .err()
    .expect("a vendored representation belongs on vocabulary.eona-x.eu");

  assert!(err.contains("dcterms:creator") && err.contains(VENDORED_BASE), "{err}");
}

#[test]
fn an_eona_x_authored_vocabulary_minted_on_the_vocabulary_host_fails_the_build() {
  let root = tempfile::tempdir().unwrap();
  vocab(
    root.path(),
    "eonax-odrl-profile",
    &ontology("https://vocabulary.eona-x.eu/vocabulary/odrl-profile/v0.0.1#", "0.0.1"),
  );

  let err = discover(root.path(), SITE_BASE).err().expect("an authored vocabulary belongs on eona-x.eu");

  assert!(err.contains("dcterms:creator") && err.contains(SITE_BASE), "{err}");
}

#[test]
fn a_person_credited_as_creator_is_an_author_not_an_upstream_body() {
  let root = tempfile::tempdir().unwrap();
  vocab(root.path(), "mcv", &ontology("https://eona-x.eu/vocabulary/mcv/v0.1.0#", "0.1.0"));
  fs::write(
    version_dir(root.path(), "mcv").join("metadata.ttl"),
    r#"@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix assettype: <http://publications.europa.eu/resource/authority/asset-classification/> .
<> a dcat:Dataset ; dcat:type assettype:c_ebfb658e ; dcterms:creator [ a foaf:Person ; foaf:name "An Author" ] .
"#,
  )
  .unwrap();

  let found = discover(root.path(), SITE_BASE).unwrap();

  assert_eq!(found.published.len(), 1);
  assert_eq!(found.published[0].base, SITE_BASE);
}
