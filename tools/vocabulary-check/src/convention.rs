use std::fs;
use std::path::Path;

use oxrdf::{NamedOrBlankNode, Term, Triple};
use oxttl::TurtleParser;

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const OWL_ONTOLOGY: &str = "http://www.w3.org/2002/07/owl#Ontology";
const SKOS_CONCEPT_SCHEME: &str = "http://www.w3.org/2004/02/skos/core#ConceptScheme";
const DCAT_TYPE: &str = "http://www.w3.org/ns/dcat#type";
const DCTERMS_CREATOR: &str = "http://purl.org/dc/terms/creator";
const FOAF_PERSON: &str = "http://xmlns.com/foaf/0.1/Person";
const DCAT_DISTRIBUTION: &str = "http://www.w3.org/ns/dcat#distribution";
const DCAT_DOWNLOAD_URL: &str = "http://www.w3.org/ns/dcat#downloadURL";
const OWL_VERSION_INFO: &str = "http://www.w3.org/2002/07/owl#versionInfo";

/// The EU asset-classification authority table, whose concepts an asset's
/// `metadata.ttl` gives as `dcat:type`.
pub const ASSET_CLASSIFICATION: &str = "http://publications.europa.eu/resource/authority/asset-classification/";

/// The asset types of the IRI convention — the first path segment of every
/// published IRI, `{site_base}{asset-type}/{slug}/{version}#` — each with the
/// [`ASSET_CLASSIFICATION`] concepts it covers. An asset whose `metadata.ttl`
/// declares a `dcat:type` from that table must be published under the asset
/// type covering it. No concept is covered twice: a Code list is a
/// `codelist`, even though the EU table nests it under Terminology.
pub const ASSET_TYPES: [(&str, &[&str]); 5] = [
  ("ontology", &["c_89b4bdb7"]),            // Formal ontology
  ("shape", &["c_b37963b3", "c_3948c2ed"]), // Application profile, Markup schema
  ("crosswalk", &["c_bba2bb35"]),           // Alignment
  (
    "vocabulary",
    &[
      "c_64714767", // Terminology
      "c_a7773248", // Thesaurus
      "c_5796a20b", // Dictionary
      "c_ebfb658e", // Glossary
      "c_25e514f4", // Lexicon
      "c_d3bf7907", // Synonym ring
      "c_ecacbeba", // Folksonomy
      "c_b0bfba6e", // Categorisation
    ],
  ),
  ("codelist", &["c_cdd11291", "c_5b130cc6"]), // Code list, Authority file
];

/// `(ontology|shape|crosswalk|vocabulary|codelist)`: the asset types as the
/// Apache regex group the hand-installed router and dev overlay match.
pub fn asset_type_alternation() -> String {
  format!("({})", asset_type_names().join("|"))
}

fn asset_type_names() -> Vec<&'static str> {
  ASSET_TYPES.iter().map(|(name, _)| *name).collect()
}

/// One publishable vocabulary version.
pub struct Vocabulary {
  /// Source directory name in eona-vocabularies-reference, e.g. `eonax-odrl-profile`.
  pub dir_name: String,
  /// The host it is published on: [`crate::SITE_BASE`] for an Eona-X-authored
  /// vocabulary, [`crate::VENDORED_BASE`] for a representation of an external
  /// standard.
  pub base: String,
  /// The ontology IRI, which is also the term namespace, e.g. `https://eona-x.eu/odrl-profile/v0.0.1#`.
  pub namespace: String,
  /// First path segment under the site base: one of [`ASSET_TYPES`], e.g. `vocabulary`.
  pub kind: String,
  /// Second path segment, e.g. `odrl-profile`.
  pub slug: String,
  /// Second path segment, e.g. `v0.0.1`.
  pub version: String,
  pub triples: Vec<Triple>,
  /// The source file's own `@prefix` table, reused when re-serializing.
  pub prefixes: PrefixTable,
}

/// A candidate directory that is deliberately not published, and why.
pub struct Skipped {
  pub dir_name: String,
  pub reason: String,
}

pub struct Discovery {
  pub published: Vec<Vocabulary>,
  pub skipped: Vec<Skipped>,
}

/// Scans `vocabularies_root` (a checkout of eona-vocabularies-reference) for
/// `eonax-*` directories and splits them into publishable and skipped.
///
/// Publishability is read off the source itself rather than configured here:
/// a vocabulary is published exactly when its root resource — its
/// `owl:Ontology`, or `skos:ConceptScheme` for a code list or thesaurus — has
/// the IRI `{site_base}{asset-type}/{slug}/{version}#`, i.e. when upstream has
/// frozen its namespace on the site. `{asset-type}` is one of [`ASSET_TYPES`]
/// and, when the directory's `metadata.ttl` declares a `dcat:type` from the EU
/// asset-classification table, the one covering it.
/// Anything still minted elsewhere (`w3id.org/eonax/...`) is skipped, because
/// serving it here would publish documents whose terms don't dereference here.
///
/// Errors are reserved for sources that claim the site base but break its
/// convention — publishing those would put wrong IRIs on eona-x.eu.
pub fn discover(vocabularies_root: &Path, site_base: &str) -> Result<Discovery, String> {
  let dirs = version_dirs(vocabularies_root)?;

  let mut found = Discovery {
    published: Vec::new(),
    skipped: Vec::new(),
  };
  for dir_name in dirs {
    match classify(vocabularies_root, &dir_name, site_base)? {
      Classified::Published(v) => found.published.push(v),
      Classified::Skipped(reason) => found.skipped.push(Skipped { dir_name, reason }),
    }
  }
  Ok(found)
}

/// Every asset version directory, `<slug>/<version>`, that holds Turtle: in
/// slug order, then version order (numerically: v0.10.0 after v0.9.0).
pub fn version_dirs(root: &Path) -> Result<Vec<String>, String> {
  let mut out = Vec::new();
  for slug in subdirs(root)? {
    let mut versions: Vec<String> = subdirs(&root.join(&slug))?
      .into_iter()
      .filter(|v| {
        fs::read_dir(root.join(&slug).join(v))
          .map(|entries| entries.filter_map(Result::ok).any(|e| e.file_name().to_string_lossy().ends_with(".ttl")))
          .unwrap_or(false)
      })
      .collect();
    versions.sort_by_key(|v| version_key(v));
    out.extend(versions.into_iter().map(|v| format!("{slug}/{v}")));
  }
  Ok(out)
}

/// Sorted, non-hidden subdirectory names of `dir`.
pub(crate) fn subdirs(dir: &Path) -> Result<Vec<String>, String> {
  let mut names: Vec<String> = fs::read_dir(dir)
    .map_err(|e| format!("cannot read {}: {e}", dir.display()))?
    .filter_map(Result::ok)
    .filter(|e| e.path().is_dir())
    .filter_map(|e| e.file_name().into_string().ok())
    .filter(|n| !n.starts_with('.'))
    .collect();
  names.sort();
  Ok(names)
}

/// `v0.10.0` sorts after `v0.9.0`; non-numeric parts compare as text.
fn version_key(version: &str) -> Vec<(u64, String)> {
  version
    .trim_start_matches('v')
    .split(['.', '-'])
    .map(|part| (part.parse().unwrap_or(0), part.to_string()))
    .collect()
}

pub(crate) enum Classified {
  Published(Vocabulary),
  Skipped(String),
}

/// The eona-x.eu publication rules for one directory: published when its
/// root resource is minted under `site_base` and follows the convention,
/// skipped when it is minted elsewhere, an error when it claims `site_base`
/// but breaks the convention.
pub(crate) fn classify(vocabularies_root: &Path, dir_name: &str, site_base: &str) -> Result<Classified, String> {
  let graph = graph_file(&vocabularies_root.join(dir_name))?;
  let path = vocabularies_root.join(dir_name).join(&graph);
  if !path.is_file() {
    return Ok(Classified::Skipped(format!("no {graph}")));
  }
  let (triples, prefixes) = parse_turtle(&path)?;
  let namespace = ontology_iri(&triples).map_err(|e| format!("{}: {e}", path.display()))?;
  let Some((host_base, rest)) = [site_base, crate::VENDORED_BASE]
    .into_iter()
    .find_map(|base| namespace.strip_prefix(base).map(|rest| (base, rest)))
  else {
    return Ok(Classified::Skipped(format!(
      "namespace {namespace} is not under {site_base} or {}",
      crate::VENDORED_BASE
    )));
  };
  // Who authored it decides the host: an external dcterms:creator marks an
  // Eona-X representation of someone else's standard.
  let vendored = names_a_creator(&vocabularies_root.join(dir_name).join("metadata.ttl"))?;
  let expected_base = if vendored { crate::VENDORED_BASE } else { site_base };
  if host_base != expected_base {
    return Err(format!(
      "{}: namespace {namespace} is on {host_base}, but metadata.ttl names {} dcterms:creator, so it belongs on {expected_base}<asset-type>/<slug>/<version>#",
      path.display(),
      if vendored { "an external" } else { "no" }
    ));
  }
  let (asset_type, slug, version) = split_iri_path(rest).ok_or_else(|| {
    format!(
      "{}: namespace {namespace} is under {site_base} but is not {site_base}<asset-type>/<slug>/<version>#",
      path.display()
    )
  })?;
  let Some((_, covered)) = ASSET_TYPES.iter().find(|(name, _)| *name == asset_type) else {
    return Err(format!(
      "{}: namespace {namespace}: '{asset_type}' is not an asset type; expected one of {}",
      path.display(),
      asset_type_names().join(", ")
    ));
  };
  let declared = declared_asset_classes(&vocabularies_root.join(dir_name).join("metadata.ttl"))?;
  if let Some(code) = declared.iter().find(|c| !covered.contains(&c.as_str())) {
    let expected = ASSET_TYPES
      .iter()
      .find(|(_, codes)| codes.contains(&code.as_str()))
      .map_or("no asset type", |(name, _)| *name);
    return Err(format!(
      "{}: namespace {namespace} is a {asset_type}, but metadata.ttl declares dcat:type {code} <{ASSET_CLASSIFICATION}{code}>, which is published as {expected}",
      path.display()
    ));
  }
  let version_info = literal(&triples, &namespace, OWL_VERSION_INFO);
  if version_info.map(|v| format!("v{v}")).as_deref() != Some(version) {
    return Err(format!(
      "{}: namespace {namespace} says version {version} but owl:versionInfo is {}",
      path.display(),
      version_info.unwrap_or("missing")
    ));
  }
  Ok(Classified::Published(Vocabulary {
    base: host_base.to_string(),
    dir_name: dir_name.to_string(),
    kind: asset_type.into(),
    slug: slug.into(),
    version: version.into(),
    namespace,
    triples,
    prefixes,
  }))
}

type PrefixTable = Vec<(String, String)>;

fn parse_turtle(path: &Path) -> Result<(Vec<Triple>, PrefixTable), String> {
  parse_turtle_with(path, TurtleParser::new())
}

fn parse_turtle_with(path: &Path, parser: TurtleParser) -> Result<(Vec<Triple>, PrefixTable), String> {
  let data = fs::read(path).map_err(|e| format!("cannot read {}: {e}", path.display()))?;
  let mut parser = parser.for_reader(data.as_slice());
  let mut triples = Vec::new();
  for t in parser.by_ref() {
    triples.push(t.map_err(|e| format!("{} is not valid Turtle: {e}", path.display()))?);
  }
  let prefixes = parser.prefixes().map(|(p, iri)| (p.to_string(), iri.to_string())).collect();
  Ok((triples, prefixes))
}

/// The one root resource: an `owl:Ontology`, or a `skos:ConceptScheme` (code
/// lists, thesauri).
fn ontology_iri(triples: &[Triple]) -> Result<String, String> {
  let mut iris: Vec<&str> = triples
    .iter()
    .filter_map(|t| match (&t.subject, &t.object) {
      (NamedOrBlankNode::NamedNode(s), Term::NamedNode(o)) if t.predicate.as_str() == RDF_TYPE && [OWL_ONTOLOGY, SKOS_CONCEPT_SCHEME].contains(&o.as_str()) => {
        Some(s.as_str())
      }
      _ => None,
    })
    .collect();
  iris.sort_unstable();
  iris.dedup();
  // A code list embedded in the vocabulary (`…v0.1.0#StatusCodes` under
  // `…v0.1.0#`) is part of it, not a second root.
  let all = iris.clone();
  iris.retain(|iri| !all.iter().any(|other| other != iri && iri.starts_with(other)));
  match iris.as_slice() {
    [iri] => Ok(iri.to_string()),
    [] => Err("declares no owl:Ontology or skos:ConceptScheme".into()),
    [a, b, ..] => Err(format!("declares more than one owl:Ontology or skos:ConceptScheme ({a}, {b})")),
  }
}

/// `vocabulary/odrl-profile/v0.0.1#` -> `("vocabulary", "odrl-profile", "v0.0.1")`.
fn split_iri_path(rest: &str) -> Option<(&str, &str, &str)> {
  let mut segments = rest.strip_suffix('#')?.split('/');
  let (asset_type, slug, version) = (segments.next()?, segments.next()?, segments.next()?);
  let valid = |s: &str| !s.is_empty() && s.chars().all(|c| c.is_ascii_alphanumeric() || "-._".contains(c));
  (segments.next().is_none() && [asset_type, slug, version].into_iter().all(valid)).then_some((asset_type, slug, version))
}

/// The asset-classification codes `metadata.ttl` gives as `dcat:type`, if the
/// file exists (upstream ships one per vocabulary).
/// The asset's graph file, relative to its directory: the one its
/// `metadata.ttl` declares as a sibling `dcat:distribution`'s
/// `dcat:downloadURL`, else `alignment.ttl` for a crosswalk (dcat:type
/// Alignment) and `ontology.ttl` for anything else.
pub fn graph_file(dir: &Path) -> Result<String, String> {
  let metadata = dir.join("metadata.ttl");
  if !metadata.is_file() {
    return Ok("ontology.ttl".into());
  }
  let base = format!("file://{}/", dir.canonicalize().unwrap_or_else(|_| dir.to_path_buf()).display());
  let parser = TurtleParser::new()
    .with_base_iri(format!("{base}metadata.ttl"))
    .map_err(|e| format!("{}: {e}", metadata.display()))?;
  let (triples, _) = parse_turtle_with(&metadata, parser)?;
  let distributions: Vec<&Term> = triples
    .iter()
    .filter(|t| t.predicate.as_str() == DCAT_DISTRIBUTION)
    .map(|t| &t.object)
    .collect();
  for t in &triples {
    let subject_is_distribution = distributions.iter().any(|d| match (d, &t.subject) {
      (Term::NamedNode(d), NamedOrBlankNode::NamedNode(s)) => d == s,
      (Term::BlankNode(d), NamedOrBlankNode::BlankNode(s)) => d == s,
      _ => false,
    });
    if subject_is_distribution
      && t.predicate.as_str() == DCAT_DOWNLOAD_URL
      && let Term::NamedNode(url) = &t.object
      && let Some(file) = url.as_str().strip_prefix(&base).filter(|f| !f.contains('/'))
    {
      return Ok(file.to_string());
    }
  }
  let alignment = triples
    .iter()
    .any(|t| t.predicate.as_str() == DCAT_TYPE && matches!(&t.object, Term::NamedNode(o) if o.as_str() == format!("{ASSET_CLASSIFICATION}c_bba2bb35")));
  Ok(if alignment { "alignment.ttl" } else { "ontology.ttl" }.into())
}

/// Whether `metadata.ttl` names a `dcterms:creator` other than a person: the
/// upstream body of a standard Eona-X represents but did not author.
fn names_a_creator(metadata: &Path) -> Result<bool, String> {
  if !metadata.is_file() {
    return Ok(false);
  }
  let base = format!("file://{}", metadata.canonicalize().unwrap_or_else(|_| metadata.to_path_buf()).display());
  let parser = TurtleParser::new().with_base_iri(base).map_err(|e| format!("{}: {e}", metadata.display()))?;
  let (triples, _) = parse_turtle_with(metadata, parser)?;
  // A creator typed foaf:Person is an author credit; any other creator (a
  // foaf:Organization or foaf:Agent naming a standards body, or a plain name)
  // is the upstream body of a standard Eona-X represents.
  let is_person = |node: &Term| {
    triples.iter().any(|t| {
      let same = match (node, &t.subject) {
        (Term::NamedNode(n), NamedOrBlankNode::NamedNode(s)) => n == s,
        (Term::BlankNode(n), NamedOrBlankNode::BlankNode(s)) => n == s,
        _ => false,
      };
      same && t.predicate.as_str() == RDF_TYPE && matches!(&t.object, Term::NamedNode(o) if o.as_str() == FOAF_PERSON)
    })
  };
  Ok(
    triples
      .iter()
      .filter(|t| t.predicate.as_str() == DCTERMS_CREATOR)
      .any(|t| !is_person(&t.object)),
  )
}

fn declared_asset_classes(metadata: &Path) -> Result<Vec<String>, String> {
  if !metadata.is_file() {
    return Ok(Vec::new());
  }
  // metadata.ttl describes itself as `<>`, a relative IRI; only its dcat:type
  // objects are read, so the base is just something to resolve against.
  let base = format!("file://{}", metadata.canonicalize().unwrap_or_else(|_| metadata.to_path_buf()).display());
  let parser = TurtleParser::new().with_base_iri(base).map_err(|e| format!("{}: {e}", metadata.display()))?;
  let (triples, _) = parse_turtle_with(metadata, parser)?;
  Ok(
    triples
      .iter()
      .filter(|t| t.predicate.as_str() == DCAT_TYPE)
      .filter_map(|t| match &t.object {
        Term::NamedNode(o) => o.as_str().strip_prefix(ASSET_CLASSIFICATION).map(str::to_string),
        _ => None,
      })
      .collect(),
  )
}

fn literal<'a>(triples: &'a [Triple], subject: &str, predicate: &str) -> Option<&'a str> {
  triples.iter().find_map(|t| match (&t.subject, &t.object) {
    (NamedOrBlankNode::NamedNode(s), Term::Literal(l)) if s.as_str() == subject && t.predicate.as_str() == predicate => Some(l.value()),
    _ => None,
  })
}
