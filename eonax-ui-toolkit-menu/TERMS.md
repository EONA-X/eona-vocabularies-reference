# Eona-X UI Toolkit Menu Vocabulary

RDFS classes and properties that the `@eona-x/ui-toolkit-menu` package reads from JSON-LD to build the site menu. `v0.1.0/ontology.ttl` holds the terms.

Namespace `https://eona-x.eu/ontology/ui-toolkit-menu#` (stable; release IRI `https://eona-x.eu/ontology/ui-toolkit-menu/v0.1.0#`). Prefix `menu:`.

## Classes

| Term | Meaning |
| --- | --- |
| `menu:Menu` | A site menu. Exactly one per graph unless a menu IRI is given. |
| `menu:Item` | A menu entry. The type is optional and inferred from position. |
| `menu:Logo` | The site logo. |
| `menu:LinkAction` | A button-style link shown in the actions area. |
| `menu:LanguageSwitcher` | An action offering the alternate language versions. |
| `menu:Alternate` | One language version of the current page. |

## Properties

| Term | On | Value |
| --- | --- | --- |
| `menu:lang` | `menu:Menu`, `menu:Alternate` | `xsd:string` (BCP 47) |
| `menu:ariaLabel` | `menu:Menu` | `rdf:langString` |
| `menu:breakpoint` | `menu:Menu` | `xsd:integer`, px, default 1024 |
| `menu:collapseOffset` | `menu:Menu` | `xsd:integer`, px, default 200 |
| `menu:logo` | `menu:Menu` | `menu:Logo` |
| `menu:src`, `menu:srcCompact` | `menu:Logo` | `xsd:string` (image URL) |
| `menu:width`, `menu:height` | `menu:Logo` | `xsd:integer`, px |
| `menu:label` | any | `rdf:langString`; `rdfs:label` is the fallback |
| `menu:href` | any | `xsd:string` or IRI |
| `menu:current`, `menu:external` | any | `xsd:boolean` |
| `menu:variant` | `menu:LinkAction` | `xsd:string`: `glass` (default) or `solid` |
| `menu:items`, `menu:children`, `menu:actions`, `menu:alternates` | `menu:Menu`, `menu:Item`, `menu:Menu`, `menu:LanguageSwitcher` | `rdf:List`, preferred |
| `menu:item`, `menu:child`, `menu:action`, `menu:alternate` | as above | unordered form, sorted by `menu:order` |
| `menu:order` | any | `xsd:integer`; missing sorts last |

## Context

`v0.1.0/context.jsonld` is the JSON-LD context of the menu vocabulary, the same file as `packages/menu/vocab/context.jsonld` in eona-ui-toolkit. Producers put `https://eona-x.eu/ontology/ui-toolkit-menu/context.jsonld` in `@context`; the Vocabulary Hub serves the latest version's context there and each version's at `https://eona-x.eu/ontology/ui-toolkit-menu/v0.1.0.context.jsonld`. The menu package never fetches it: the context is built in.

## Legacy

These terms were first published as `https://eona-x.eu/ns/menu#` by `@eona-x/ui-toolkit-menu` 0.10.x and earlier. That namespace is off the IRI convention and is not part of this asset. The local names, labels and comments are unchanged; only the namespace differs. Documents that still use the old namespace must switch to the new one.
