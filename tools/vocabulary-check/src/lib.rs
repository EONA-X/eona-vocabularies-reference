//! Quality gate for eona-vocabularies-reference.
//!
//! [`convention`] holds the rules for vocabularies published under
//! `https://eona-x.eu/<asset-type>/<slug>/<version>#`; the same crate is the
//! dependency the publishing pipeline (vocabulary-hub.eona-x.eu) builds with,
//! so a contribution that passes here is one the build accepts.

pub mod check;
pub mod convention;

pub use check::{Finding, check};
pub use convention::{ASSET_TYPES, Discovery, Skipped, Vocabulary, asset_type_alternation, discover};

/// Where Eona-X vocabularies are published.
pub const SITE_BASE: &str = "https://eona-x.eu/";
