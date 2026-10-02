//! `eona-vocabulary-check [REPOSITORY]` — every finding, one per line; exit
//! status 1 when there is any. Defaults to the current directory.

use std::path::PathBuf;
use std::process::ExitCode;

fn main() -> ExitCode {
  let root = std::env::args_os().nth(1).map_or_else(|| PathBuf::from("."), PathBuf::from);
  let findings = eona_vocabulary_check::check(&root);
  for f in &findings {
    println!("{}: {}", f.dir, f.message);
  }
  if findings.is_empty() {
    println!("ok: {} passes the vocabulary checks", root.display());
    ExitCode::SUCCESS
  } else {
    eprintln!("{} finding(s)", findings.len());
    ExitCode::FAILURE
  }
}
