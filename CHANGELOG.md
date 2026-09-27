# Changelog

All notable changes to html-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.1.0 — 2026-09-27

The first implementation of the interface published as 0.0.1: the
tokenizer, a named subset of tree construction, queries, the
serialiser, escaping and the sanitiser.

### Added

- The tokenizer is the whole of WHATWG HTML section 13.2.5, and it
  produces the tokens of every case of html5lib-tests' tokenizer suite
  that a `Str` can hold: 6499 of them, in
  `tests/html5lib_tokenizer_tests.nv`.
- Tree construction follows the subset the README lists, and 219
  tree-construction cases of web-platform-tests' copy of the html5lib
  tests, in `tests/html5lib_tree_tests.nv`, build the trees a browser
  builds.  The cases the adoption agency algorithm decides are asserted
  to raise `IssueUnsupportedConstruct`.
- `htmlentity`, a module with no public functions, holds the 2231 named
  character references, written by `tools/entities.py`, and the
  decoding the other modules call.
- `tests/differential_tests.nv`, written by `tools/differential.py`,
  compares the tokenizer with Python's `html.parser` over 150
  documents.  Every line under `src/` is run by the suites;
  `bash tests/coverage.sh` prints the number.

### Changed

These break code written against 0.0.x.

- `HtmlIssueKind` has a sixth variant, `IssueSelfClosingNonVoid`, for
  the `/>` on a non-void element that the parser reports and ignores.
- `HtmlDoc.source` and `HtmlTokenizer.source` are the caller's text
  after the preprocessing of section 13.2.3.5: CR LF and CR are LF,
  and tag and attribute names are lowered.  Every range points into
  them.
- `HtmlTokenizer` has three more fields: `last`, `switching` and
  `ended`.  A tokenizer is made with `tokenizer` or `tokenizer_in`.
- The tree holds what the document wrote: no `html`, `head` or `body`
  element is added.
- `is_void` answers the thirteen void elements of the Standard, not
  fourteen, and `is_raw_text` answers all nine raw-text elements, not
  four.
- `escape_text` escapes three characters, `&`, `<` and `>`.
  `escape_attr` escapes five.
- A function that takes a byte list answers a new list with the
  output after the one passed in, and leaves that one as it was.
- The toolchain floor is 0.13.0.

## 0.0.2 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

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

### Design notes

Public type names are unique across a whole assembly, dependencies
included, so every type here is prefixed. `HtmlNode` because
markdown-nv wants `Node`; `HtmlDoc` on the precedent of `TomlDoc`,
`YamlDoc` and `XmlDoc`; `HtmlToken` and `HtmlTokenKind` because
sql-engine-nv publishes `Token` and `TokKind`; `HtmlRange` on the
precedent of `ElfRange` and `ZipRange`; `HtmlSelector`, `HtmlAllowList`
and `HtmlIssue` because `Selector`, `Policy` and `Issue` are names
other packages will want. The modules are prefixed for the same
reason, and because `dom` is a standard library module.

The package was written against the novo-lang registry's own README
rendering, `orbit/website/src/packages.nv`. That code is safe today by
accident of composition: `sanitize_hrefs` finds every `href="` in the
rendered HTML by substring search, which works only because
`markdown.to_html` escapes the whole document before substituting
inline markup, and because that renderer emits an `href` from exactly
one place. The search rewrites an `href="` inside a code sample or a
text node, and it does not touch `src`, `srcset`, `formaction`,
`xlink:href`, `onclick`, `onerror` or `style`. Its companion
`safe_href` checks the scheme with `starts_with` on a lowercased
string, which the four spellings of `javascript:` in the sanitiser's
test corpus each defeat. `htmlsafe.safe_url` and `htmlsafe.sanitize`
over a tree are the replacements.
