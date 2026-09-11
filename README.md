# html-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`. Installing this package works;
calling it panics with `not implemented`.

## What this is

Tolerant HTML: read a document that was never valid, find things in it,
write it back out, and — separately — decide what a publisher is
allowed to have written.

- `htmlparse` — the HTML5 tokenizer, and a **named subset** of tree
  construction;
- `htmltree` — the document as a flat arena over the caller's source;
- `htmlquery` — by tag, by attribute, and a named subset of CSS;
- `htmlwrite` — a tree back out, into a buffer the caller owns;
- `htmlsafe` — escaping, and sanitising, and why they are two jobs.

```
novo pkg add html-nv
novo pkg build
novo test
```

## The one example that will work — the registry's own job

```novo ignore
use htmlparse
use htmlsafe
use htmlwrite

// A published README, rendered, arriving on a page this origin serves.
fn safe_readme(rendered: Str) -> Str
    let doc = htmlparse.parse_fragment(rendered, "div")
    let clean = htmlsafe.sanitize(doc, htmlsafe.allow_readme())
    htmlwrite.serialize_str(clean, htmlwrite.default_options())
```

## The load-bearing interfaces — there are two

**Reading: the tokenizer, which is the whole spec and is testable.**

```novo ignore
pub fn next_token(t: HtmlTokenizer) -> ?HtmlTokenStep []
```

Bytes in, tokens out, the state as a value, no tree. All eighty states,
the character-reference machine, the raw-text and script-data escapes,
the bogus-comment path — there is no honest way to implement a subset
of it, and html5lib-tests checks exactly this shape.

**Safety: the allow-list, which is a value.**

```novo ignore
pub struct HtmlAllowList
    tags: [Str]
    attrs: [HtmlAttrRule]
    url_schemes: [Str]
    strip_contents_of: [Str]
    ...

pub fn sanitize(doc: HtmlDoc, allow: HtmlAllowList) -> HtmlDoc []
```

A documentation site, a registry rendering READMEs, a comment box and a
mail client want four different policies, and the difference between
them is **data**, not flags. `allow_none()`, `allow_basic()` and
`allow_readme()` are named lists to start from; `with_tag` and
`without_tag` modify one in a line.

## Escaping and sanitising are not the same job

A package that offered one function called `clean` would be offering
the wrong one to half its callers.

| | escaping | sanitising |
| --- | --- | --- |
| input | text that was never meant to be markup | a document that **is** markup |
| output | text that renders as itself | a document with what a publisher may not write removed |
| totality | total — every input has an escaped form | necessarily lossy |
| what it needs | five characters | a tree |

**Sanitising cannot be done on text**, and that is the argument this
package exists to make. An allow-list over a substring search is not an
allow-list.

## The dogfood: what the registry does today, and why it is safe by accident

`orbit/website/src/packages.nv` renders a published README into the
registry's own origin, with two functions:

- `safe_href(url)` — trims, lowercases, and accepts `https://`,
  `http://`, `mailto:`, a `#` fragment or a `/` path; everything else
  becomes `#`. The allow-list is right.
- `sanitize_hrefs(html)` — finds every `href="` in the **rendered
  HTML** by substring search and rewrites the value to the closing
  quote.

That is safe today. It is safe **by accident of composition**: it works
only because `markdown.to_html` escapes the whole document before it
substitutes inline markup — so no tag a README wrote can survive — and
because that renderer emits an `href` from exactly one place. The
comment above `sanitize_hrefs` says as much, and is correct.

Change either fact and the search is wrong in three ways at once:

- it rewrites an `href="` **inside a code sample**, where the text is
  content;
- it rewrites one **inside a text node**, where the same is true;
- it does not touch `src`, `srcset`, `formaction`, `xlink:href`,
  `onclick`, `onerror` or `style` — none of which is an `href` and
  every one of which is a way to run script or load a tracker.

And `safe_href`'s own check is a `starts_with` on a lowercased string.
A browser strips leading whitespace and C0 controls from a URL and
decodes character references **before** it looks at the scheme, so
`  javascript:`, `java\tscript:` and `java&#09;script:` are all
`javascript:` to a browser and none of them is to a `starts_with`.
`htmlsafe.safe_url` makes that check; `tests/htmlsafe_tests.nv` has all
four spellings.

On a tree, *every `a` element's `href` attribute* is a thing you can
say. That is the whole difference, and it is why this package's
sanitiser takes an `HtmlDoc` and not a `Str`.

## The named subset, and its four refusals

The HTML5 tree-construction algorithm is twenty-three insertion modes,
a stack of open elements, a list of active formatting elements, foster
parenting and the adoption agency algorithm. It exists to make every
browser agree about documents nobody meant to write. This package
implements the part a scraper, a sanitiser and a linter need, and
**names what it refuses** rather than approximating it.

**Implemented:** the void elements; the raw-text elements
(`script`, `style`, `textarea`, `title`); implied end tags for `p`,
`li`, `dd`, `dt`, `option`, `td`, `th`, `tr`, `thead`, `tbody`,
`tfoot`; an end tag matching an ancestor closing everything up to it; a
stray end tag dropped and reported; anything still open closed at the
end and reported; the fragment case.

**Refused — each raising `IssueUnsupportedConstruct`, never silently
approximated:**

| refused | what happens instead |
| --- | --- |
| the adoption agency algorithm — `<b>a<i>b</b>c</i>` | the `</b>` closes the `<i>` as well; both are reported |
| foster parenting — content in a table but outside a cell | it stays where it was written, as a child of the table |
| `<template>` contents as their own fragment | a template's children are ordinary children |
| foreign content — SVG and MathML integration points | `<svg>` is an ordinary element, its names lowercased |

A reader who needs any of those four needs a browser engine, and should
learn that from a named issue rather than from a rendering that is
subtly wrong.

**There is no error type**, and that is the specification's decision
rather than this package's: the parsing algorithm has no fatal errors.
`doc.issues` carries every recovery, named and positioned, so a linter
can fail on what it chooses to.

## The selector subset

Compiled once, matched many times. In: `*`, type, `#id`, `.class`, the
seven attribute operators (`[a]`, `=`, `~=`, `^=`, `$=`, `*=`, `|=`),
descendant, `>`, `+`, `~`, groups, and
`:first-child :last-child :only-child :empty :root`.

Refused, as a named `HtmlSelectorError` with a position:
`:nth-child()` and its family (a counting pass plus the `an+b`
micro-syntax), `:not() :has() :is() :where()` (a selector list nested
inside a selector), the pseudo-*elements*, the state pseudo-classes
(`:hover`, `:checked`), and namespaces.

A refusal is an error because the alternative is worse: a selector
engine that accepted `:nth-child(2n)` and matched nothing would leave a
caller debugging their document instead of their selector.

`by_tag`, `by_id`, `by_class` and `by_attr` are beside the selector
surface, not under it. They cost no parsing and cannot be misspelled
into something that silently matches nothing — and `by_class` matches a
**word**, so `navbar` does not match `class="navbar-brand"`, which is
the bug a `str.contains` on the attribute always has.

## The round trip is not an identity, and the promise is narrower

`serialize(parse(s))` is not `s`, and cannot be: the parser closed what
the document left open, dropped what it could not place, lowercased the
names and resolved the character references.

What **is** promised is that `parse(serialize(parse(s)))` has the same
tree as `parse(s)`. That is the property a sanitiser depends on — a
sanitiser whose output re-parsed to something else would be one that
could be talked out of its own policy — and it is what the suite
checks.

## The layer, and the absent dependency

`core` — no effects. A tokenizer over a string the caller already
holds, a tree of indices, a serialiser that appends to the caller's
buffer. **Nothing is fetched**: a document's `<img src>` and
`<script src>` are reported as what they are and never followed, which
is a security property as much as a layer one.

**unicode-nv is not a dependency, and that is a finding rather than an
oversight.** HTML5 defines tag and attribute name matching as **ASCII**
case-insensitive, deliberately and explicitly, so `DIV` and `div` are
the same element with no Unicode table anywhere. The one big table this
package needs — the 2231 named character references, about 40 KB — is
HTML's own, not Unicode's, and lives here. The two places a Unicode
question could have appeared: a numeric character reference naming a
surrogate becomes U+FFFD, which is a range check rather than a table;
and a URL scheme is ASCII by RFC 3986.

**No `@tier(embedded)` claim, and none is intended.** The entity table
alone is 40 KB, the tree is a growable list, and nothing on a device
parses HTML. The audit's `core-embedded` row passes as *makes no device
claim*.

## Where the names come from, and the ones that were taken

Public type names are unique across the whole assembly, dependencies
included.

| here | the obvious name | why not |
| --- | --- | --- |
| `HtmlNode` | `Node` | certain to collide — markdown-nv wants it in this same lane, and `NodeError` is already published |
| `HtmlDoc` | `Document` | `TomlDoc`, `YamlDoc`, `JsonDoc` and `XmlDoc` are the standard library's precedent for exactly this |
| `HtmlKind` | `Element`, `NodeKind` | `Element` is the name three other packages will want |
| `HtmlAttr` | `Attr`, `Attribute` | generic |
| `HtmlToken`, `HtmlTokenKind` | `Token`, `TokenKind` | sql-engine-nv publishes `Token` and `TokKind` |
| `HtmlRange` | `Range`, `Span` | `ElfRange` and `ZipRange` are the precedent; `Span` is a module name in use |
| `HtmlSelector` | `Selector` | generic, and `Selection` and `SelItem` are already published by sql-engine-nv |
| `HtmlAllowList` | `AllowList`, `Policy`, `Sanitizer` | all three generic enough to collide with a future security package |
| `HtmlIssue`, `HtmlIssueKind` | `Issue`, `Diagnostic` | generic |
| module `htmlparse`, `htmltree`, … | `html`, `parse`, `tree`, `query`, `write`, `safe` | every one of the six is a name another package will want, and `dom` is a **standard-library module** |

Nothing here collided with markdown-nv or tera-nv, in the same lane, by
construction: the three packages prefix their types with `Md`, `Html`
and `Tera` and their modules with the same.

## The reference implementation

**html5ever** for the tokenizer's shape and for the decision to make it
public rather than internal. **BeautifulSoup** for the query
vocabulary, and for the observation that most callers want `find_all`
by tag rather than a selector. **lol-html** for the streaming rewrite
model that `HtmlToken.span` makes possible. **ammonia** and
**DOMPurify** for the sanitiser's allow-list shape, the unwrap-versus-
strip distinction, and the URL-scheme check. **`orbit/website`'s
`safe_href`** for the list of schemes a published document may link to,
which is where `web_schemes()` comes from.

The oracles are:

- **html5lib-tests** — `tokenizer/*.test` for the tokenizer, which is
  the suite every parser is measured against, and `tree-construction/`
  for the part of the tree algorithm this package implements;
- the **named character reference table** from the HTML specification
  itself, all 2231 of them;
- the sanitiser's own attack corpus, which is the one thing not taken
  from a spec: the four spellings of `javascript:`, the event-handler
  attributes, and the raw-text elements that cannot be unwrapped.

Deliberately left out, and where it goes instead:

- **Rendering, layout and CSS cascade.** A browser engine.
- **Fetching anything.** This package is `core`; a document's `src` is
  reported and never followed.
- **Mutating a tree in place.** The tree is a value; `sanitize` returns
  a new one. A builder API is a different package, and a caller
  assembling HTML has `htmlwrite.write_start_tag`.
- **XML and XHTML strictness.** xml-nv's row on the plan. `htmlwrite`'s
  `xhtml` option is about the output syntax, not about parsing.
- **Content Security Policy, or anything about headers.** A sanitiser
  decides what a document may contain; a header decides what a browser
  may do with it, and that is the `web` package's.

## Status

Every function is `todo()`. Three suites, all red, all for the same
reason — every assertion reaches `not implemented: html-nv.<fn>`, which
is the expected result until the bodies land.

```
novo test --isolate tests/htmlparse_tests.nv   # html5lib-tests' tokenizer cases, and the four refusals
novo test --isolate tests/htmlquery_tests.nv   # the selector subset, and the round-trip property
novo test --isolate tests/htmlsafe_tests.nv    # escaping, and the sanitiser's attack corpus
```

`novo doc` renders and its examples compile.
