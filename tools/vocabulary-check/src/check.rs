//! The repository-wide gate. Every top-level directory with a `metadata.ttl`
//! is a published asset; the rules are the ones the publishing pipelines
//! enforce when they build from this repository, collected here so that a
//! contribution meets them before it is merged — and reported all at once,
//! not stopping at the first.

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use oxrdf::{NamedOrBlankNode, Term, Triple};
use oxttl::TurtleParser;

use crate::SITE_BASE;
use crate::convention::{ASSET_CLASSIFICATION, Classified, classify};

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const OWL_ONTOLOGY: &str = "http://www.w3.org/2002/07/owl#Ontology";
const SKOS_CONCEPT_SCHEME: &str = "http://www.w3.org/2004/02/skos/core#ConceptScheme";
const DCTERMS_TITLE: &str = "http://purl.org/dc/terms/title";
const DCAT_TYPE: &str = "http://www.w3.org/ns/dcat#type";
const VOID_LINKSET: &str = "http://rdfs.org/ns/void#Linkset";
const RDFS_SEE_ALSO: &str = "http://www.w3.org/2000/01/rdf-schema#seeAlso";
const FORMAL_ONTOLOGY: &str = "c_89b4bdb7";
const ALIGNMENT: &str = "c_bba2bb35";

/// One problem, in one top-level directory of the repository.
#[derive(Debug, PartialEq)]
pub struct Finding {
  pub dir: String,
  pub message: String,
}

/// One top-level directory: its parsed Turtle files, by file name.
struct Dir {
  name: String,
  graphs: BTreeMap<String, Vec<Triple>>,
  /// The `<>` subject `metadata.ttl` was parsed against, when it has one.
  metadata_base: Option<String>,
}

impl Dir {
  fn published(&self) -> bool {
    self.metadata_base.is_some()
  }

  /// The first `owl:Ontology` of `ontology.ttl`, in authored order — what the
  /// publishing pipeline takes as the vocabulary's namespace.
  fn first_ontology(&self) -> Option<&str> {
    self.graphs.get("ontology.ttl")?.iter().find_map(|t| typed(t, OWL_ONTOLOGY))
  }

  fn metadata_objects(&self, predicate: &str) -> Vec<&Term> {
    let (Some(base), Some(metadata)) = (&self.metadata_base, self.graphs.get("metadata.ttl")) else {
      return Vec::new();
    };
    metadata
      .iter()
      .filter(|t| matches!(&t.subject, NamedOrBlankNode::NamedNode(s) if s.as_str() == base) && t.predicate.as_str() == predicate)
      .map(|t| &t.object)
      .collect()
  }

  /// Asset-classification codes `metadata.ttl` gives as `dcat:type`.
  fn asset_classes(&self) -> Vec<&str> {
    self
      .metadata_objects(DCAT_TYPE)
      .into_iter()
      .filter_map(|o| match o {
        Term::NamedNode(n) => n.as_str().strip_prefix(ASSET_CLASSIFICATION),
        _ => None,
      })
      .collect()
  }
}

/// Every finding in the repository at `root`, in directory order.
pub fn check(root: &Path) -> Vec<Finding> {
  let mut findings = Vec::new();
  let dirs = load(root, &mut findings);
  let mut report = |dir: &str, message: String| findings.push(Finding { dir: dir.to_string(), message });

  // Namespaces of the published vocabularies, and of every ontology in the
  // repository (the hub), published or not.
  let published: Vec<(&str, &str)> = dirs
    .iter()
    .filter(|d| d.published())
    .filter_map(|d| Some((d.name.as_str(), d.first_ontology()?)))
    .collect();
  let hub: Vec<(&str, &str)> = dirs.iter().filter_map(|d| Some((d.name.as_str(), d.first_ontology()?))).collect();

  for dir in dirs.iter().filter(|d| d.published()) {
    let name = dir.name.as_str();
    if dir.metadata_objects(DCTERMS_TITLE).is_empty() {
      report(name, "metadata.ttl: no dcterms:title on <>".into());
    }
    let classes = dir.asset_classes();

    if classes.contains(&ALIGNMENT) {
      match dir.graphs.get("alignment.ttl") {
        None if !root.join(name).join("alignment.ttl").is_file() => {
          report(name, "dcat:type is Alignment but there is no alignment.ttl".into());
        }
        None => {} // present but unparsable: already reported
        Some(alignment) => match alignment.iter().find_map(|t| typed(t, VOID_LINKSET)) {
          None => report(name, "alignment.ttl: no void:Linkset root".into()),
          Some(linkset) => {
            let mut sides: Vec<&str> = Vec::new();
            for target in objects(alignment, linkset, RDFS_SEE_ALSO) {
              for (side, ns) in &published {
                if !ns.is_empty() && target.starts_with(ns) && !sides.contains(side) {
                  sides.push(side);
                }
              }
            }
            if sides.len() < 2 {
              report(
                name,
                format!(
                  "alignment.ttl: the void:Linkset's rdfs:seeAlso reach {} published vocabularies ({}); a crosswalk needs at least 2",
                  sides.len(),
                  sides.join(", ")
                ),
              );
            }
          }
        },
      }
      continue;
    }

    let Some(ontology) = dir.graphs.get("ontology.ttl") else {
      if !root.join(name).join("ontology.ttl").is_file() {
        report(name, "metadata.ttl but no ontology.ttl".into());
      }
      continue;
    };
    if dir.first_ontology().is_none() && (classes.is_empty() || classes.contains(&FORMAL_ONTOLOGY)) {
      report(name, "ontology.ttl declares no owl:Ontology (required for a Formal ontology)".into());
    }

    // References into an ontology of the repository that is not published.
    let referenced: Vec<&str> = ontology
      .iter()
      .filter_map(|t| match &t.object {
        Term::NamedNode(o) => Some(o.as_str()),
        _ => None,
      })
      .collect();
    for (hub_dir, hub_iri) in &hub {
      if published.iter().any(|(_, ns)| ns == hub_iri) {
        continue;
      }
      if referenced.iter().any(|o| o.starts_with(hub_iri)) {
        report(
          name,
          format!("references hub ontology <{hub_iri}> ({hub_dir}/ontology.ttl), which has no metadata.ttl"),
        );
      }
    }

    // The eona-x.eu publication rules, wherever a root is minted there.
    let minted_here = ontology.iter().any(|t| {
      typed(t, OWL_ONTOLOGY)
        .or_else(|| typed(t, SKOS_CONCEPT_SCHEME))
        .is_some_and(|s| s.starts_with(SITE_BASE))
    });
    if minted_here {
      match classify(root, name, SITE_BASE) {
        Ok(Classified::Published(_) | Classified::Skipped(_)) => {}
        Err(e) => report(name, relative(&e, root)),
      }
    }
  }
  findings
}

/// Parses every Turtle file directly in each top-level directory.
fn load(root: &Path, findings: &mut Vec<Finding>) -> Vec<Dir> {
  let Ok(entries) = fs::read_dir(root) else {
    findings.push(Finding {
      dir: ".".into(),
      message: format!("cannot read {}", root.display()),
    });
    return Vec::new();
  };
  let mut names: Vec<String> = entries
    .filter_map(Result::ok)
    .filter(|e| e.path().is_dir())
    .filter_map(|e| e.file_name().into_string().ok())
    .filter(|n| !n.starts_with('.'))
    .collect();
  names.sort();

  names
    .into_iter()
    .map(|name| {
      let dir_path = root.join(&name);
      let mut files: Vec<String> = fs::read_dir(&dir_path)
        .into_iter()
        .flatten()
        .filter_map(Result::ok)
        .filter(|e| e.path().is_file())
        .filter_map(|e| e.file_name().into_string().ok())
        .filter(|f| f.ends_with(".ttl"))
        .collect();
      files.sort();
      let metadata_base = files.iter().any(|f| f == "metadata.ttl").then(|| format!("file:///{name}/metadata.ttl"));
      let mut graphs = BTreeMap::new();
      for file in files {
        let mut parser = TurtleParser::new();
        if file == "metadata.ttl" {
          // `<>` is the asset itself: resolve it against a stable base.
          parser = parser.with_base_iri(format!("file:///{name}/metadata.ttl")).expect("a valid base IRI");
        }
        let data = match fs::read(dir_path.join(&file)) {
          Ok(d) => d,
          Err(e) => {
            findings.push(Finding {
              dir: name.clone(),
              message: format!("{file}: cannot read: {e}"),
            });
            continue;
          }
        };
        match parser.for_reader(data.as_slice()).collect::<Result<Vec<_>, _>>() {
          Ok(triples) => {
            graphs.insert(file, triples);
          }
          Err(e) => findings.push(Finding {
            dir: name.clone(),
            message: format!("{file}: not valid Turtle: {e}"),
          }),
        }
      }
      Dir { name, graphs, metadata_base }
    })
    .collect()
}

/// The subject IRI of `t` when `t` is `<subject> a <class>`.
fn typed<'a>(t: &'a Triple, class: &str) -> Option<&'a str> {
  match (&t.subject, &t.object) {
    (NamedOrBlankNode::NamedNode(s), Term::NamedNode(o)) if t.predicate.as_str() == RDF_TYPE && o.as_str() == class => Some(s.as_str()),
    _ => None,
  }
}

fn objects<'a>(triples: &'a [Triple], subject: &'a str, predicate: &'a str) -> impl Iterator<Item = &'a str> + 'a {
  triples.iter().filter_map(move |t| match (&t.subject, &t.object) {
    (NamedOrBlankNode::NamedNode(s), Term::NamedNode(o)) if s.as_str() == subject && t.predicate.as_str() == predicate => Some(o.as_str()),
    _ => None,
  })
}

/// Paths in convention errors, relative to the repository.
fn relative(message: &str, root: &Path) -> String {
  message.replace(&format!("{}/", root.display()), "")
}
