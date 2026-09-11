# Changelog

All notable changes to html-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.0.1 — 2026-09-11

The **interface**: every signature and every effect row, and no bodies.
`stability = "draft"`, and the release is recorded `implemented = false`.

### Added

- `htmlparse` — the HTML5 tokenizer, published rather than hidden
  because html5lib-tests tests exactly that shape, plus a **named
  subset** of tree construction whose four refusals each raise
  `IssueUnsupportedConstruct`.
- `htmltree` — the flat-arena tree over the caller's source, with
  `is_void` and `is_raw_text` published so a serialiser, a sanitiser
  and a caller building a document read one list rather than three.
- `htmlquery` — `by_tag`/`by_id`/`by_class`/`by_attr` beside a compiled
  CSS subset. `by_class` matches a word, not a substring.
- `htmlwrite` — serialisation into a caller's buffer. The round trip is
  documented as *parses to the same tree*, not as an identity.
- `htmlsafe` — escaping and sanitising as separate named functions,
  with `HtmlAllowList` as a value and `allow_readme()` as the policy
  the novo-lang registry's package pages need.

### Known

- **There is no error type**, because the HTML5 parsing algorithm has
  no fatal errors. `doc.issues` carries every recovery, named and
  positioned.
- **Four constructs are refused rather than approximated**: the
  adoption agency algorithm, foster parenting, `<template>` contents,
  and foreign content. The README says what happens instead for each.
- **A selector outside the subset is a compile error**, not an empty
  match — the alternative leaves a caller debugging their document
  instead of their selector.
- **No dependency on unicode-nv, and the absence is a finding.** HTML5
  defines name matching as ASCII case-insensitive, deliberately. The
  entity table is HTML's own.
- **No `@tier(embedded)` claim.** The entity table alone is 40 KB.
