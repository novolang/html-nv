#!/usr/bin/env python3
"""Write tests/differential_tests.nv from Python's html.parser.

`html.parser.HTMLParser` is an independent HTML tokenizer.  This script
builds documents from a seeded generator, has Python read each one, and
records the tokens it reports: start tags with their attributes, end
tags, comments, doctypes and text, with character references resolved.
The test file reads the same documents with this package's tokenizer
and asserts the same tokens.

The generator keeps to what both read the same way.  Python reads
`textarea` and `title` as markup, and in an attribute value it resolves
a reference without its semicolon where HTML leaves it, so the
documents use neither; every other reference ends in `;`.  Tag and
attribute names come in mixed case, values are quoted three ways,
`script` and `style` hold markup-like text, and comments, void
elements written with and without `/>`, and a doctype appear.

Run from the package root:  python3 tools/differential.py
The output is passed through `novo fmt`.
"""
import html.parser
import random
import subprocess

COUNT = 150
SEED = 13
SEP = '\x01'

TAGS = ['div', 'P', 'span', 'Em', 'a', 'ul', 'li', 'section', 'b']
VOIDS = ['br', 'img', 'HR', 'input']
ATTRS = ['id', 'class', 'HREF', 'data-x', 'title', 'alt']
REFS = ['&amp;', '&lt;', '&gt;', '&quot;', '&#65;', '&#x263A;', '&copy;', '&hellip;', '&eacute;']
WORDS = ['alpha', 'beta', 'x < y', 'a > b', 'café', '  spaced  ', '\n', 'q"uote', "it's"]


class Reader(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.text = None

    def flush(self):
        if self.text is not None:
            self.items.append('C' + self.text)
            self.text = None

    def handle_starttag(self, tag, attrs):
        self.flush()
        seen, parts = set(), []
        for k, v in attrs:
            if k in seen:
                continue
            seen.add(k)
            parts.append('|%s=%s' % (k, v if v is not None else ''))
        self.items.append('S' + tag + ''.join(parts))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.flush()
        self.items.append('E' + tag)

    def handle_data(self, data):
        self.text = (self.text or '') + data

    def handle_comment(self, data):
        self.flush()
        self.items.append('M' + data)

    def handle_decl(self, decl):
        self.flush()
        self.items.append('D' + decl.split()[1].lower())


def text(rng):
    out = []
    for _ in range(rng.randrange(1, 4)):
        if rng.random() < 0.4:
            out.append(rng.choice(REFS))
        else:
            out.append(rng.choice(WORDS).replace('<', '&lt;').replace('>', '&gt;'))
    return ''.join(out)


def value(rng):
    v = text(rng).replace('\n', ' ')
    quote = rng.choice(['"', "'", ''])
    if quote == '"':
        return '"' + v.replace('"', '&quot;') + '"'
    if quote == "'":
        return "'" + v.replace("'", '&#39;') + "'"
    return rng.choice(['plain', 'x-1', '42', 'a&amp;b'])


def attrs(rng):
    out = ''
    for _ in range(rng.randrange(0, 3)):
        out += ' ' + rng.choice(ATTRS) + '=' + value(rng)
    if rng.random() < 0.1:
        out += ' disabled'
    return out


def element(rng, depth):
    roll = rng.random()
    if roll < 0.15:
        return '<%s%s%s>' % (rng.choice(VOIDS), attrs(rng), rng.choice(['', '/', ' /']))
    if roll < 0.22:
        return '<!-- %s -->' % rng.choice(['note', 'a -- b', '<p>'])
    if roll < 0.27:
        return '<script>if (a < b && c > d) { x = "</p>"; }</script>'
    if roll < 0.30:
        return '<style>p > a { color: red }</style>'
    if roll < 0.55 or depth > 3:
        return text(rng)
    tag = rng.choice(TAGS)
    inner = ''.join(element(rng, depth + 1) for _ in range(rng.randrange(0, 4)))
    return '<%s%s>%s</%s>' % (tag, attrs(rng), inner, tag)


def document(rng):
    head = '<!DOCTYPE html>' if rng.random() < 0.3 else ''
    return head + ''.join(element(rng, 0) for _ in range(rng.randrange(1, 5)))


def nv(s):
    out = []
    for c in s:
        o = ord(c)
        if c == '\\':
            out.append('\\\\')
        elif c == '"':
            out.append('\\"')
        elif c == '$':
            out.append('\\$')
        elif c == '\n':
            out.append('\\n')
        elif o < 0x20 or o > 0x7E:
            out.append('\\u{%x}' % o)
        else:
            out.append(c)
    return '"' + ''.join(out) + '"'


def main():
    rng = random.Random(SEED)
    rows = []
    for _ in range(COUNT):
        doc = document(rng)
        r = Reader()
        r.feed(doc)
        r.close()
        r.flush()
        rows.append((doc, SEP.join(r.items)))
    out = ['''// tests/differential_tests.nv — this package's tokenizer against
// Python's `html.parser`, over %d generated documents.
//
// Written by tools/differential.py; do not edit by hand.  Each row is a
// document and the tokens Python reads from it: `D` a doctype's name,
// `S` a start tag with `|name=value` for each attribute, `E` an end
// tag, `M` a comment and `C` text, references resolved, separated by
// U+0001.  The documents keep to what both tokenizers read the same
// way; the script's docstring says what that leaves out.

use std.test
use std.str
use htmlparse
use htmltree
use htmlentity

// The tokens of a document, in the form Python's are written.
fn tokens_text(source: Str) -> Str
    var t = htmlparse.tokenizer(source)
    var items: [Str] = []
    var chars = ""
    var in_chars = false
    var more = true
    while more
        match htmlparse.next_token(t)
            None => more = false
            Some(step) =>
                t = step.tokenizer
                let src = t.source
                match step.token.kind
                    TokenCharacters(r, refs) =>
                        chars = chars + decoded(src, r, refs, false)
                        in_chars = true
                    kind =>
                        if in_chars
                            items = list.push(items, "C" + chars)
                            chars = ""
                            in_chars = false
                        match kind
                            TokenDoctype(name) => items = list.push(items, "D" + slice(src, name))
                            TokenStartTag(name, attrs, _) => items = list.push(items, start_text(src, name, attrs))
                            TokenEndTag(name) => items = list.push(items, "E" + slice(src, name))
                            TokenComment(r) => items = list.push(items, "M" + slice(src, r))
                            _ => ()
    if in_chars
        items = list.push(items, "C" + chars)
    str.join(items, "\\u{1}")

// A start tag's text, the first of a repeated attribute kept.
fn start_text(src: Str, name: HtmlRange, attrs: [HtmlAttr]) -> Str
    var out = "S" + slice(src, name)
    var seen: [Str] = []
    for a in attrs
        let key = slice(src, a.name)
        if not list.contains(seen, key)
            seen = list.push(seen, key)
            out = out + "|" + key + "=" + decoded(src, a.value, a.needs_decoding, true)
    out

// The text of a range.
fn slice(src: Str, r: HtmlRange) -> Str
    str.slice(src, r.start, r.end)

// The decoded text of a range.
fn decoded(src: Str, r: HtmlRange, refs: Bool, in_attr: Bool) -> Str
    if refs
        return htmlentity.decode_scan(src, r.start, r.end, in_attr).text
    slice(src, r)

// The documents and Python's tokens.
fn rows() -> [(Str, Str)]
    [''' % COUNT]
    out.append(',\n'.join('        (%s,\n        %s)' % (nv(d), nv(w)) for d, w in rows))
    out.append('''    ]

@test
fn test_every_document_reads_as_python_reads_it() [io]
    var n = 0
    for row in rows()
        let (source, want) = row
        n = n + 1
        test.case("row ${n}")
        test.assert_eq_str(tokens_text(source), want)
''')
    path = 'tests/differential_tests.nv'
    open(path, 'w').write('\n'.join(out))
    subprocess.run(['novo', 'fmt', path], check=False)


if __name__ == '__main__':
    main()
