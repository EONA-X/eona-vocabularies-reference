use std::path::Path;

/// One problem, in one top-level directory of the repository.
#[derive(Debug, PartialEq)]
pub struct Finding {
  pub dir: String,
  pub message: String,
}

/// Every finding in the repository at `root`.
pub fn check(_root: &Path) -> Vec<Finding> {
  todo!()
}
