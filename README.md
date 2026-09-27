# html-nv

HTML is the markup language of the web, and its parsing is specified by
the [WHATWG HTML Standard section 13](https://html.spec.whatwg.org/multipage/parsing.html).
That specification is written to be tolerant: it says what every
browser must do with a document nobody meant to write, and it has no
fatal errors. This package brings a tolerant HTML reader, a tree, a
finder, a writer and a sanitiser to novo-lang.
[tera-nv](https://novo-lang.org/packages/tera-nv) uses its escaping.

## What the pieces are

Reading HTML happens in two stages. The **tokenizer** (section 13.2.5)
turns bytes into a flat sequence of **tokens**: a doctype, a start tag,
an end tag, a comment, a run of characters, and the end of the file.
**Tree construction** (section 13.2.6) turns that sequence into a tree
of elements, inserting what the document left implied and closing what
it left open.

A **character reference** is `&` followed by a name or a number, such
as `&amp;` or `&#169;`. The specification names 2231 of them. The
tokenizer resolves references in text and in attribute values.

A **void element** is one that cannot have children, such as `br` and
`img`. A **raw-text element** is one whose contents are not markup,
such as `script`, `style`, `textarea` and `title`. Both are lists the
specification fixes.

A **fragment** is a document parsed as if it were the contents of some
element, which is what a template or a rendered comment is. Section
13.4 is the fragment parsing algorithm, and the context element decides
what is allowed inside.

**Escaping** turns text into markup that renders as that text: `<`
becomes `&lt;` and so on. It is total, and it needs no tree.
**Sanitising** takes a document that is markup and removes what the
publisher is not allowed to write. It is lossy, and it needs a tree,
because "every `a` element's `href` attribute" is not a thing one can
say about a string. They are two jobs and this package keeps them in
two sets of functions.

The tree here is a **flat arena**: one list of nodes, each holding
indices to its parent and children, over the document's source. A
node's names and text are byte ranges into that source, so nothing is
copied until a caller asks for a string. The source a document holds is
the caller's text after the preprocessing of section 13.2.3.5: each CR
LF pair and each lone CR is a LF, and every tag and attribute name is
lowered, which moves no byte.

The tree holds what the document wrote. The `html`, `head` and `body`
elements a browser adds are not added, so the tree of `<p>hi` is one
`p` element under the document node.

Every function in this package performs no input and no output. A
document's `src` and `href` are reported and never followed.

## Install

```
novo pkg add html-nv
```

## Example

```novo
use htmlparse
use htmlquery
use htmlsafe
use htmltree
use htmlwrite

fn main() [io]
    // A document that was never valid: the paragraph is left open.
    let doc = htmlparse.parse("<p>hello <a href='https://example.org'>there")

    // Every link in the tree, by tag name rather than by selector.
    for i in htmlquery.by_tag(doc, htmltree.root(doc), "a")
        match htmltree.attr(doc, i, "href")
            Some(url) => println("link to ${url}")
            None      => println("a link with no href")

    // Remove everything a README is not allowed to write, then write
    // the tree back out as a string.
    let clean = htmlsafe.sanitize(doc, htmlsafe.allow_readme())
    println(htmlwrite.serialize_str(clean, htmlwrite.default_options()))
```

## What the package contains

| Module | Contents |
| --- | --- |
| `htmltree` | The document as a flat arena of nodes over the caller's source, the recovery issues a parse reports, and the lookups on a node. |
| `htmlparse` | The tokenizer as a value, the whole-document and fragment parsers, and the parse limits. |
| `htmlquery` | Finding nodes: by tag, by identifier, by class, by attribute, and by a compiled subset of CSS. |
| `htmlwrite` | A tree back out into a buffer the caller owns, and the three calls for writing a tag by hand. |
| `htmlsafe` | Escaping, unescaping, looking up a named character reference, and sanitising against an allow-list. |
| `htmlentity` | The table of the 2231 named character references, and the decoding the other modules call. It has no public functions. |

## How to choose an entry point

**`htmlparse.parse` reads a whole document.** `parse_fragment` reads
one as the contents of a named element, which is what a rendered
comment or a template is. `parse_with` is `parse` with limits the
caller chose.

**`htmlparse.tokenizer` and `next_token` are the tokenizer on its
own.** Use them when a scraper wants one tag and no tree, or when a
rewriter edits the source in place: every token carries the byte range
it occupied.

**`htmlquery.by_tag`, `by_id`, `by_class` and `by_attr` cost no
parsing.** Use them for a single condition. `by_class` matches a whole
word, so `navbar` does not match `class="navbar-brand"`.

**`htmlquery.compile` and `select_all` are for a selector.** A selector
is compiled once and matched many times, and a selector this package
does not support is refused with a position rather than matching
nothing.

**`htmlsafe.escape_text` and `escape_attr` take text that was never
markup.** `sanitize` takes a document that is.

## The rules a user needs

1. **Escaping and sanitising are different jobs.** Escaping is total:
   every input has an escaped form, and it needs five characters.
   Sanitising is lossy and needs a tree. An allow-list applied by
   searching a string is not an allow-list.
2. **`htmlsafe.safe_url` is the URL check, and `starts_with` is not.**
   A browser strips leading whitespace and C0 control characters from a
   URL, and decodes character references, before it looks at the
   scheme. `  javascript:`, `java<tab>script:` and `java&#09;script:`
   all reach a browser as `javascript:`.
3. **An allow-list is data, not flags.** `allow_none()`,
   `allow_basic()` and `allow_readme()` are lists to start from, and
   `with_tag`, `without_tag` and `with_attr_rule` each change one in a
   line.
4. **A tag that is not allowed is unwrapped, and its children stay.**
   An element in `strip_contents_of` is removed with its contents
   instead. `script` and `style` must be in that list, because their
   contents are raw text and unwrapping one leaves its code on the page
   as prose.
5. **A URL attribute must be named as one.** `HtmlAttrRule.url_attrs`
   is the subset of `attrs` whose value is checked against
   `url_schemes`. A URL attribute that is merely allowed is the hole
   the module exists to close. `href` is not the only one: `src`,
   `srcset`, `formaction`, `xlink:href` and the event-handler
   attributes each load or run something.
6. **`web_schemes()` is `http`, `https`, `mailto` and `tel`.** It does
   not include `data:`, which is a script vector in an `href`.
7. **A refused URL becomes `HtmlAllowList.refused_url`, not nothing.**
   The default is `#`, so the link is visibly inert and a reader can
   see that something was there.
8. **The parser has no error type**, because the specification's
   algorithm has no fatal errors. `HtmlDoc.issues` carries every
   recovery, named and positioned, and a linter decides which ones
   matter.
9. **Four tree-construction constructs are refused, not approximated.**
   Each raises `IssueUnsupportedConstruct` where it appears. A reader
   who needs one of them needs a browser engine.

   | Refused | What happens instead |
   | --- | --- |
   | The adoption agency algorithm and the reopening of formatting elements, as in `<b>a<i>b</b>c</i>` | The `</b>` closes the `<i>` as well, and a formatting element closed by something else stays closed |
   | Foster parenting: content in a table but outside a cell | It stays where it was written, as a child of the table |
   | A `<template>`'s contents as their own fragment | A template's children are ordinary children |
   | Foreign content: SVG and MathML integration points | `<svg>` is an ordinary element and its names are lowercased |

   The rest of section 13.2.6 that this package implements: void
   elements, raw-text elements, the implied end tags of `p`, `li`,
   `dd`, `dt`, `option`, `td`, `th`, `tr` and the table sections, an
   end tag that closes what was opened after its element, `</p>` with
   no open `p` as an empty `p`, `</br>` as a `br`, a line feed right
   after `<pre>` dropped, and in a document the whitespace before the
   first element dropped. Tables get no implied `tbody`.

10. **`serialize(parse(s))` is not `s`.** The parser closed what the
    document left open, dropped what it could not place, lowercased the
    names and resolved the character references. What is promised is
    that `parse(serialize(parse(s)))` has the same tree as `parse(s)`.
    A sanitiser depends on that property.
11. **A self-closing slash is honoured only on a void element.** On
    anything else it is reported as `IssueSelfClosingNonVoid` and
    ignored, as section 13.2.6.1 says, so `<div/>` opens a `div`.
12. **Tag and attribute names are matched ASCII case-insensitively**
    and stored lowercased. That is the specification's own rule, not an
    approximation of Unicode case folding.
13. **`htmlwrite.pretty_options()` is for reading, not for
    publishing.** Indentation changes what a document means wherever
    whitespace is significant, inside a `pre` and between two inline
    elements. `default_options()` indents by zero.
14. **The serialiser keeps comments even when the sanitiser drops
    them.** Serialising is not sanitising, and a writer that silently
    dropped part of its input would make rule 10 untrue.
15. **A selector this package does not support is an error, not an
    empty match.** A selector engine that accepted `:nth-child(2n)` and
    matched nothing would leave a caller debugging the document instead
    of the selector. `HtmlSelectorError` carries the position.
16. **A byte list passed to a writer is not changed.** `serialize`,
    `escape_text` and the other functions that take one answer a new
    list: the one passed in, with the output after it.

## What the selector subset covers

| Supported | |
| --- | --- |
| Simple | `*`, a type name, `#id`, `.class` |
| Attribute | `[a]`, `[a=v]`, `[a~=v]`, `[a^=v]`, `[a$=v]`, `[a*=v]`, `[a\|=v]` |
| Combinators | descendant, `>`, `+`, `~`, and comma-separated groups |
| Pseudo-class | `:first-child`, `:last-child`, `:only-child`, `:empty`, `:root` |

Refused, each as an `HtmlSelectorError` with a position:
`:nth-child()` and its family, `:not()`, `:has()`, `:is()`, `:where()`,
the pseudo-elements, the state pseudo-classes such as `:hover` and
`:checked`, and namespaces.

## Sizes and limits

| `HtmlLimits` field | What it bounds | `default_limits()` |
| --- | --- | --- |
| `max_depth` | How deeply elements may nest | 512 |
| `max_nodes` | How many nodes the tree may hold | 1,000,000 |
| `max_attributes` | How many attributes one element may carry | 4,096 |

A document past `max_depth` is truncated rather than recursed into. The
pathological input is a file of 100,000 `<div>` tags.

| Other quantity | Value |
| --- | --- |
| Named character references | 2,231 |
| Characters escaped by `escape_text` | 3 |
| Characters escaped by `escape_attr` | 5 |

## What is not included

- **Rendering, layout and the CSS cascade.** That is a browser engine.
- **Fetching anything.** This package declares no effects. A
  document's `src` is reported and never followed.
- **Mutating a tree in place.** The tree is a value, and `sanitize`
  answers a new one. A caller assembling HTML uses
  `htmlwrite.write_start_tag` and its neighbours.
- **The four tree-construction constructs in rule 9.**
- **The selector features listed above.**
- **XML and XHTML parsing.** `htmlwrite`'s `xhtml` option changes the
  output syntax only. [xml-nv](https://novo-lang.org/packages/xml-nv)
  is the XML package.
- **Content Security Policy and anything else about headers.** A
  sanitiser decides what a document may contain. A header decides what
  a browser may do with it.
- **A build for a microcontroller.** The character reference table
  alone is about 100 KB and the tree is a growable list, so this package
  does not build for a microcontroller with no heap allocator.
- **Processing instructions as nodes.** `<?php ?>` is a bogus comment,
  as html5lib-tests' tokenizer suite expects.
- **A Unicode dependency.** HTML matches names ASCII
  case-insensitively by design, the character reference table is
  HTML's own rather than Unicode's, a numeric reference naming a
  surrogate becomes U+FFFD by a range check, and a URL scheme is ASCII
  under RFC 3986.

## Related packages

- [tera-nv](https://novo-lang.org/packages/tera-nv) renders templates
  and autoescapes through this package's `escape_text`. Take it to
  produce HTML. Take this one to read HTML or to clean it.
- [markdown-nv](https://novo-lang.org/packages/markdown-nv) turns
  Markdown into HTML. Its output is a document this package's
  sanitiser takes.
- [xml-nv](https://novo-lang.org/packages/xml-nv) is XML, which is
  strict where this is tolerant.
- [mime-nv](https://novo-lang.org/packages/mime-nv) decides whether a
  response body is HTML at all before it is parsed.
- [url-nv](https://novo-lang.org/packages/url-nv) parses and resolves
  the URLs found in a document's attributes. This package checks a
  URL's scheme and does not parse the rest.
- `std.json` and the standard library's other document types are the
  precedent for the `HtmlDoc` name.

## Tests

```bash
novo test tests/htmlparse_tests.nv            # the tokenizer and the tree through the public calls
novo test tests/htmlbuild_tests.nv            # each rule of tree construction, and the element lists
novo test tests/htmlquery_tests.nv            # finding nodes, and the serialiser's round trip
novo test tests/htmlsafe_tests.nv             # escaping and the sanitiser's attack cases
novo test tests/htmledge_tests.nv             # the edges of every module
novo test tests/html5lib_tokenizer_tests.nv   # 6499 cases of html5lib-tests' tokenizer suite
novo test tests/html5lib_tree_tests.nv        # 219 tree-construction cases
novo test tests/differential_tests.nv         # 150 documents, compared with Python's html.parser
bash tests/coverage.sh                        # line coverage over src/, merged across the suites
```

`html5lib_tokenizer_tests.nv` is written by `tools/html5lib_tokens.py`
from html5lib-tests, the suite HTML tokenizers are measured against,
at a pinned commit. It holds every case a novo-lang `Str` can hold,
from every file of the suite, in every start state but the CDATA
section state, which only foreign content has. Each is an input and
the exact tokens it must produce. Parse errors are not compared.

`html5lib_tree_tests.nv` is written by `tools/html5lib_trees.py` from
the tree-construction tests, which web-platform-tests now keeps. It
holds the cases this package's subset answers the same way, with the
children of `body` compared for a document. The script counts what it
leaves out and why: tables, `template`, foreign content and the other
insertion modes the subset does not implement, the elements a browser
moves into `head`, and processing instructions. The nineteen cases
whose trees the adoption agency algorithm decides are asserted to
raise `IssueUnsupportedConstruct` instead.

`differential_tests.nv` is written by `tools/differential.py`. It
builds documents from a seeded generator, keeping to what Python's
`html.parser` reads as HTML does, and compares the tokens.

The named character reference table is written by
`tools/entities.py` from Python's `html.entities.html5`, which is the
HTML Standard's list. The sanitiser's corpus is the one set of cases
not taken from a specification: the spellings of `javascript:` named
in rule 2, the event-handler attributes, and the raw-text elements
that cannot be unwrapped.

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
