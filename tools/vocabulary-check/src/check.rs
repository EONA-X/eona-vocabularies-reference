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

use crate::convention::{ASSET_CLASSIFICATION, ASSET_TYPES, Classified, classify, graph_file, subdirs};
use crate::{SITE_BASE, VENDORED_BASE};

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const OWL_ONTOLOGY: &str = "http://www.w3.org/2002/07/owl#Ontology";
const SKOS_CONCEPT_SCHEME: &str = "http://www.w3.org/2004/02/skos/core#ConceptScheme";
const DCTERMS_TITLE: &str = "http://purl.org/dc/terms/title";
const DCAT_TYPE: &str = "http://www.w3.org/ns/dcat#type";
const DCAT_VERSION: &str = "http://www.w3.org/ns/dcat#version";
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
  /// The asset's graph file: declared in metadata.ttl, or the default.
  graph: String,
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
    self.graphs.get(&self.graph)?.iter().find_map(|t| typed(t, OWL_ONTOLOGY))
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

  /// The lexical forms of `<> predicate "…"` in metadata.ttl.
  fn metadata_literals(&self, predicate: &str) -> Vec<&str> {
    self
      .metadata_objects(predicate)
      .into_iter()
      .filter_map(|o| match o {
        Term::Literal(l) => Some(l.value()),
        _ => None,
      })
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

  // <asset-type>/<slug> -> (host, directory), to catch one path on two hosts.
  let mut paths: Vec<(String, String, String)> = Vec::new();
  // Stable term namespaces the published assets mint: the only
  // `<asset-type>/<slug>#…` IRIs that are not off-convention.
  let mut stable: Vec<String> = Vec::new();
  for dir in dirs.iter().filter(|d| d.published()) {
    let name = dir.name.as_str();
    if dir.metadata_objects(DCTERMS_TITLE).is_empty() {
      report(name, "metadata.ttl: no dcterms:title on <>".into());
    }
    // The version: exactly one dcat:version, which names the directory.
    let versions = dir.metadata_literals(DCAT_VERSION);
    let version = match versions.as_slice() {
      [v] => Some(*v),
      _ => {
        report(name, format!("metadata.ttl: needs exactly one dcat:version on <> (found {})", versions.len()));
        None
      }
    };
    if let (Some(version), Some((slug, version_dir))) = (version, name.split_once('/'))
      && version_dir != format!("v{version}")
    {
      report(
        name,
        format!("version directory {version_dir} but dcat:version is {version}: expected {slug}/v{version}/"),
      );
    }
    let classes = dir.asset_classes();

    if classes.contains(&ALIGNMENT) {
      match dir.graphs.get(&dir.graph) {
        None if !root.join(name).join(&dir.graph).is_file() => {
          report(name, format!("dcat:type is Alignment but its graph file {} does not exist", dir.graph));
        }
        None => {} // present but unparsable: already reported
        Some(alignment) => match alignment.iter().find_map(|t| typed(t, VOID_LINKSET)) {
          None => report(name, format!("{}: no void:Linkset root", dir.graph)),
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
                  "{}: the void:Linkset's rdfs:seeAlso reach {} published vocabularies ({}); a crosswalk needs at least 2",
                  dir.graph,
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

    let Some(ontology) = dir.graphs.get(&dir.graph) else {
      if !root.join(name).join(&dir.graph).is_file() {
        report(name, format!("metadata.ttl but its graph file {} does not exist", dir.graph));
      }
      continue;
    };
    if dir.first_ontology().is_none() && (classes.is_empty() || classes.contains(&FORMAL_ONTOLOGY)) {
      report(name, format!("{} declares no owl:Ontology (required for a Formal ontology)", dir.graph));
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
        .is_some_and(|s| s.starts_with(SITE_BASE) || s.starts_with(VENDORED_BASE))
    });
    if minted_here {
      match classify(root, name, SITE_BASE) {
        Ok(Classified::Published(v)) => {
          paths.push((format!("{}/{}", v.kind, v.slug), v.base.clone(), name.to_string()));
          if v.is_stable() && !stable.contains(&v.namespace) {
            stable.push(v.namespace.clone());
          }
          if let Some(version) = version
            && v.version != format!("v{version}")
          {
            report(
              name,
              format!("namespace {} is version {} but dcat:version is {version}", v.namespace, v.version),
            );
          }
        }
        Ok(Classified::Skipped(_)) => {}
        Err(e) => report(name, relative(&e, root)),
      }
    }
  }
  for (i, (path, base, dir)) in paths.iter().enumerate() {
    if let Some((_, other_base, other_dir)) = paths[..i].iter().find(|(p, b, _)| p == path && b != base) {
      report(
        dir,
        format!("{path} is published on both {other_base} ({other_dir}) and {base}: one asset, one host"),
      );
    }
  }

  // IRIs on Eona-X-owned hosts must be publication-convention IRIs, in every
  // file of a published asset (graphs, metadata, anything else).
  for dir in dirs.iter().filter(|d| d.published()) {
    for (file, triples) in &dir.graphs {
      let mut off: Vec<(String, String, usize)> = Vec::new(); // (namespace, example, count)
      for t in triples {
        let terms = [
          match &t.subject {
            NamedOrBlankNode::NamedNode(n) => Some(n.as_str()),
            _ => None,
          },
          Some(t.predicate.as_str()),
          match &t.object {
            Term::NamedNode(n) => Some(n.as_str()),
            _ => None,
          },
        ];
        for iri in terms.into_iter().flatten() {
          if let Some(ns) = off_convention(iri, &stable) {
            match off.iter_mut().find(|(n, _, _)| *n == ns) {
              Some(entry) => entry.2 += 1,
              None => off.push((ns, iri.to_string(), 1)),
            }
          }
        }
      }
      for (ns, example, count) in off {
        report(
          &dir.name,
          format!(
            "{file}: {count} IRI(s) under <{ns}>, e.g. <{example}>, are on an Eona-X host but not {SITE_BASE} or {VENDORED_BASE}<asset-type>/<slug>/<version>#…, nor a stable term namespace <asset-type>/<slug>#… that a published asset mints ({}) (asset types: {})",
            if stable.is_empty() {
              "none".to_string()
            } else {
              stable.iter().map(|n| format!("<{n}>")).collect::<Vec<_>>().join(", ")
            },
            ASSET_TYPES.iter().map(|(t, _)| *t).collect::<Vec<_>>().join(", ")
          ),
        );
      }
    }
  }
  // Last line of defence: what passes here is what vocabulary-hub-build gets,
  // and it builds with `discover`. Anything it still refuses is a finding.
  if findings.is_empty()
    && let Err(e) = crate::discover(root, SITE_BASE)
  {
    findings.push(Finding {
      dir: ".".into(),
      message: format!("vocabulary-hub-build would fail: {e}"),
    });
  }
  findings
}

/// For an IRI on an Eona-X-owned host or path that is neither a
/// publication-convention IRI nor a bare site root: the namespace to report it
/// under (scheme, host and first path segment). `None` when the IRI is fine.
///
/// `stable` holds the stable term namespaces (`<asset-type>/<slug>#`,
/// eona-x/backlog#677 as amended by eona-x/backlog#994) that published assets
/// mint, each with its release as `owl:versionIRI` (which `classify` enforces).
/// An IRI of that form under any other namespace — e.g. one that drops the
/// version of a versioned-only asset — is off-convention.
fn off_convention(iri: &str, stable: &[String]) -> Option<String> {
  let (scheme, rest) = iri.split_once("://")?;
  let (host, path) = rest.split_once('/').unwrap_or((rest, ""));
  let host = host.to_ascii_lowercase();
  let eona_host = host == "eona-x.eu" || host.ends_with(".eona-x.eu");
  let eonax_w3id = host == "w3id.org" && (path == "eonax" || path.starts_with("eonax/"));
  if !eona_host && !eonax_w3id {
    return None;
  }
  if path.is_empty() && !eonax_w3id {
    return None; // the site itself, e.g. https://eona-x.eu/
  }
  if scheme == "https" && (host == "eona-x.eu" || host == "vocabulary.eona-x.eu") {
    // The fragment is the term, and may itself contain '/' (a code list
    // member, `…#StatusCodes/active`): only the part before '#' is the path.
    let (head, fragment) = match path.split_once('#') {
      Some((head, fragment)) => (head, Some(fragment)),
      None => (path, None),
    };
    let segments: Vec<&str> = head.split('/').collect();
    let asset_type_ok = |t: &str| ASSET_TYPES.iter().any(|(name, _)| *name == t);
    match (segments.as_slice(), fragment) {
      // <asset-type>/<slug>/<version>#<term>
      ([asset_type, slug, version], Some(_)) if asset_type_ok(asset_type) && !slug.is_empty() && version.starts_with('v') && version.len() > 1 => {
        return None;
      }
      // <asset-type>/<slug>#<term>, under a stable namespace an asset mints
      ([asset_type, slug], Some(_)) if asset_type_ok(asset_type) && !slug.is_empty() && stable.iter().any(|ns| iri.starts_with(ns.as_str())) => {
        return None;
      }
      _ => {}
    }
  }
  let first = if eonax_w3id {
    path.splitn(3, '/').take(2).collect::<Vec<_>>().join("/")
  } else {
    path.split(['/', '#']).next().unwrap_or("").to_string()
  };
  Some(format!("{scheme}://{host}/{first}"))
}

/// Every top-level directory's own Turtle files (graphs that are part of the
/// hub without being published assets, e.g. a dependency closure — or an
/// asset still in the pre-version layout) and every `<slug>/<version>/`
/// directory (an asset version).
fn load(root: &Path, findings: &mut Vec<Finding>) -> Vec<Dir> {
  let slugs = match subdirs(root) {
    Ok(s) => s,
    Err(message) => {
      findings.push(Finding { dir: ".".into(), message });
      return Vec::new();
    }
  };
  let mut dirs = Vec::new();
  for slug in slugs {
    let top = load_dir(root, &slug, findings);
    if top.published() {
      let version = top
        .metadata_literals(DCAT_VERSION)
        .first()
        .map_or_else(|| "<version>".to_string(), |v| (*v).to_string());
      findings.push(Finding {
        dir: slug.clone(),
        message: format!("metadata.ttl directly under {slug}/: an asset version belongs in {slug}/v{version}/"),
      });
      dirs.push(Dir { metadata_base: None, ..top });
    } else if !top.graphs.is_empty() {
      dirs.push(top);
    }
    for version in subdirs(&root.join(&slug)).unwrap_or_default() {
      let dir = load_dir(root, &format!("{slug}/{version}"), findings);
      if !dir.graphs.is_empty() || dir.metadata_base.is_some() {
        dirs.push(dir);
      }
    }
  }
  dirs
}

/// Parses every Turtle file directly in `root/name`.
fn load_dir(root: &Path, name: &str, findings: &mut Vec<Finding>) -> Dir {
  let dir_path = root.join(name);
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
          dir: name.to_string(),
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
        dir: name.to_string(),
        message: format!("{file}: not valid Turtle: {e}"),
      }),
    }
  }
  let graph = graph_file(&dir_path).unwrap_or_else(|_| "ontology.ttl".into());
  Dir {
    name: name.to_string(),
    graph,
    graphs,
    metadata_base,
  }
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
