# assets/

Illustrations and upstream-standards-body logos referenced by each
ontology's `<slug>/metadata.toml` (`upstream.logo`) — shared here rather
than duplicated per-directory since several ontologies share the same
upstream (`dpp` and `battery-pass` both cite BatteryPass). Consumed by
[eona-vocabulary-services](https://github.com/Eona-X/eona-vocabulary-services)'
publish pipeline, which copies these into its own published site and
references them from the generated `catalog.jsonld`/`.ttl` via
`foaf:thumbnail` — rendered as each catalog card's hero image.

Each upstream org below has two files: the logo as originally sourced, and
a composed `*-hero.png` (logo centered on a 700x504 canvas — 25:18, the
aspect ratio the consuming UI's `object-fit: cover` thumbnail box needs so
nothing gets cropped — with a white rounded chip behind logos designed for
a light background, or none behind the two logos that are already a
white/reversed variant). Each ontology's `metadata.toml` references the
`*-hero.png` file; the original is kept alongside purely as the documented
source.

- `owl-illustration.svg` — original artwork (EONA-X), the default hero image
  for every catalog card (used as-is, no `-hero.png` composed variant).
- `w3c.svg` — [World Wide Web Consortium](https://www.w3.org/), from
  [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:W3C%C2%AE_Icon_2025.svg).
  Public domain per Commons (simple geometric shapes/text), used here to
  identify the W3C ODRL 2.2 Recommendation the `odrl22` vocabulary bundles.
  W3C® and the W3C icon are registered trademarks of W3C; this is nominative
  use (identifying the referenced standard), not an endorsement claim.
  Also used by the `dpv-pd` vocabulary.
- `datex-ii.png` — [DATEX II](https://datex2.eu/), from datex2.eu's own
  media library. No published brand/reuse policy found — nominative use,
  identifying the DATEX II standard the `datex-ii` vocabulary is derived
  from.
- `cen.svg` — [CEN](https://www.cencenelec.eu/) (Comité Européen de
  Normalisation), from
  [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Comit%C3%A9_Europ%C3%A9en_de_Normalisation_(logo).svg).
  Public domain per Commons + trademark notice (same basis as w3c.svg above).
  Used as a stand-in for NeTEx/Transmodel (CEN/TS 16614), the standard the
  `netex` vocabulary is derived from — NeTEx itself has no comparably
  clearly-licensed logo.
- `datatourisme.png` — [DATAtourisme](https://www.datatourisme.fr/),
  published by ADN Tourisme, from datatourisme.fr's own media library. No
  published brand/reuse policy found — nominative use.
- `batterypass.svg` — the [BatteryPass](https://thebatterypass.eu/)
  consortium (white/reversed variant, for dark backgrounds), from
  thebatterypass.eu's own media library. No published brand/reuse policy
  found — nominative use, identifying the BatteryPass Data Attribute
  Longlist / data model the `dpp` and `battery-pass` vocabularies are
  derived from.

All logos above are the property of their respective organisations and are
used solely to indicate which upstream standard each vocabulary implements
or derives from — not to imply endorsement or affiliation. If any
organisation objects to this usage, replace or remove the file and the
`[upstream]` table in the referencing ontology's `metadata.toml`.
