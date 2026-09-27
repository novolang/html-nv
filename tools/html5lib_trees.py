#!/usr/bin/env python3
"""Write tests/html5lib_tree_tests.nv from the tree-construction tests.

The tree-construction half of html5lib-tests is now kept by
web-platform-tests, under html/syntax/parsing/resources, as `.dat`
files: an input, an optional context element for a fragment, and the
tree a browser builds, one node per line.  This script takes the cases
this package's subset of tree construction answers the same way, and
writes each as a row: the input, the context, and the expected tree.

A browser's tree has `html`, `head` and `body` elements this package
does not add.  A document case is kept when its `head` is empty and
nothing but a doctype and comments sits beside its `html`; the tree
compared is the doctype and comments, then the children of `body`.

A case is left out, and counted in the file's header by reason, when
it needs a construct the subset does not implement:

- tables, which gain an implied `tbody` and foster-parent content;
- `template`, `svg`, `math`, `frameset`, `select`, `form` and
  `button`, whose insertion modes are not implemented;
- explicit `html`, `head` and `body` tags, and the elements a browser
  moves into `head`;
- misnested or reopened formatting elements, which the adoption agency
  algorithm and the list of active formatting elements repair, named
  one by one in MISNESTED below;
- a doctype with a public or system identifier, which is not kept;
- scripting enabled, `noscript` and the obsolete `image` and `isindex`;
- a context element whose insertion mode is not implemented;
- a processing instruction, which the version of the Standard these
  tests follow keeps as a node of its own.  html5lib-tests' tokenizer
  suite, which this package passes, reads one as a bogus comment.

Run from the package root:
    python3 tools/html5lib_trees.py [directory of .dat files]
With no argument the files are fetched at the pinned commit.
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

COMMIT = 'f085a1efc1f58fbe263d384b1e335d656fe58e66'
BASE = ('https://raw.githubusercontent.com/web-platform-tests/wpt/%s/'
        'html/syntax/parsing/resources/' % COMMIT)
FILES = ['tests1.dat', 'tests2.dat', 'tests3.dat', 'tests5.dat',
         'tests6.dat', 'tests7.dat', 'tests8.dat', 'tests9.dat',
         'tests_innerHTML_1.dat', 'entities01.dat', 'entities02.dat',
         'comments01.dat', 'doctype01.dat']

OUT_OF_SUBSET = ['table', 'caption', 'colgroup', 'col', 'tbody', 'thead',
                 'tfoot', 'tr', 'td', 'th', 'template', 'svg', 'math',
                 'frameset', 'frame', 'select', 'form', 'button', 'html',
                 'head', 'body', 'noscript', 'image', 'isindex', 'nobr',
                 'rb', 'rp', 'rt', 'rtc', 'ruby', 'keygen']
CONTEXTS = ['div', 'p', 'span', 'body', 'ul', 'ol', 'li', 'pre',
            'textarea', 'title', 'style', 'script', 'xmp', 'iframe',
            'noembed', 'noframes', 'plaintext', 'a', 'b', 'em']

# Inputs whose trees the adoption agency algorithm or the reopening of
# formatting elements decides.  Found by running the suite: in each a
# browser moves or clones a formatting element.  The test file asserts
# that each of them raises `IssueUnsupportedConstruct` instead.
MISNESTED = {
    '<a><p>X<a>Y</a>Z</p></a>',
    '<p><b><div><marquee></p></b></div>X',
    '<a X>0<b>1<a Y>2',
    '<b><p></b>TEST',
    '<b id=a><p><b id=b></p></b>TEST',
    '<font><p>hello<b>cruel</font>world',
    '<b>A<cite>B<div>C</b>D',
    '<DIV> abc <B> def <I> ghi <P> jkl </B>',
    '<DIV> abc <B> def <I> ghi <P> jkl </B> mno',
    '<DIV> abc <B> def <I> ghi <P> jkl </B> mno </I>',
    '<DIV> abc <B> def <I> ghi <P> jkl </B> mno </I> pqr',
    '<DIV> abc <B> def <I> ghi <P> jkl </B> mno </I> pqr </P>',
    '<DIV> abc <B> def <I> ghi <P> jkl </B> mno </I> pqr </P> stu',
    '<wbr><strike><code></strike><code><strike></code>',
    '<a><p><a></a></p></a>',
    '<p><b><div><marquee></p></b></div>',
    '<!DOCTYPE html><font><p><b>test</font>',
    '<b>a<div></div><div></b>y',
    '<a><div><p></a>',
}


def fetch(name):
    return urllib.request.urlopen(BASE + name).read().decode('utf-8')


def cases(text):
    for block in re.split(r'\n(?=#data\n)', '\n' + text):
        if not block.strip():
            continue
        sections, key = {}, None
        for line in block.strip('\n').split('\n'):
            if line.startswith('#'):
                key = line[1:]
                sections[key] = []
            elif key is not None:
                sections[key].append(line)
        yield sections


def depth(line):
    return (len(line) - len(line.lstrip(' '))) // 2


def body_tree(lines):
    """The doctype and comments beside `html`, then `body`'s children,
    or None when the tree has anything else."""
    out, i = [], 0
    while i < len(lines):
        line = lines[i][2:]
        if depth(line) != 0:
            return None
        if line == '<html>':
            j = i + 1
            if j >= len(lines) or lines[j][2:] != '  <head>':
                return None
            j += 1
            if j >= len(lines) or lines[j][2:] != '  <body>':
                return None
            j += 1
            while j < len(lines) and depth(lines[j][2:]) >= 2:
                out.append('| ' + lines[j][2:][4:])
                j += 1
            i = j
            continue
        if line.startswith('<!DOCTYPE') and '"' in line:
            return None
        out.append(lines[i])
        i += 1
    return out


def tags_in(data):
    return set(t.lower() for t in re.findall(r'</?([A-Za-z][A-Za-z0-9]*)', data))


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
        elif c == '\t':
            out.append('\\t')
        elif o < 0x20 or o == 0x7F or o > 0x7E:
            out.append('\\u{%x}' % o)
        else:
            out.append(c)
    return '"' + ''.join(out) + '"'


def main():
    rows, left, misnested = [], {}, []

    def leave(reason):
        left[reason] = left.get(reason, 0) + 1

    for name in FILES:
        if len(sys.argv) > 1:
            text = open(os.path.join(sys.argv[1], name), encoding='utf-8').read()
        else:
            text = fetch(name)
        for c in cases(text):
            data = '\n'.join(c.get('data', []))
            if 'script-on' in c:
                leave('scripting enabled')
                continue
            if '\x00' in data or '\r' in data:
                leave('U+0000 or a carriage return in the input')
                continue
            context = ''
            if 'document-fragment' in c:
                context = c['document-fragment'][0].strip()
                if context not in CONTEXTS:
                    leave('a context element outside the subset')
                    continue
            if '<?' in data:
                leave('a processing instruction, which the Standard now keeps as its own node')
                continue
            if tags_in(data) & set(OUT_OF_SUBSET):
                leave('an element outside the subset')
                continue
            if data in MISNESTED:
                leave('misnested formatting')
                misnested.append(data)
                continue
            tree = c.get('document', [])
            if not context:
                tree = body_tree(tree)
                if tree is None:
                    leave('a tree beside or inside head')
                    continue
            rows.append((name, data, context, '\n'.join(tree)))
    header = ', '.join('%d for %s' % (n, r) for r, n in sorted(left.items()))
    out = ['''// tests/html5lib_tree_tests.nv — tree construction against the
// html5lib tree-construction tests, as web-platform-tests keeps them at
// commit %s.
//
// Written by tools/html5lib_trees.py; do not edit by hand.  Each row
// is an input, a context element for a fragment or an empty string for
// a document, and the expected tree in the tests' own format: one node
// per line, `| ` and two spaces per level, attributes sorted by name.
// For a document the tree is the doctype and comments, then the
// children of `body`, because this package adds no `html`, `head` or
// `body`.  %d cases are here.  Left out: %s.

use std.test
use std.str
use htmlparse
use htmltree

// A document's tree in the tests' format.
fn dump(doc: HtmlDoc) -> Str
    var lines: [Str] = []
    lines = dump_children(doc, htmltree.root(doc), 0, lines)
    str.join(lines, "\\n")

// The lines of a node's children, adjacent text nodes joined.
fn dump_children(doc: HtmlDoc, index: Int, level: Int, start: [Str]) -> [Str]
    var lines = start[:]
    let pad = "| " + str.repeat("  ", level)
    var text = ""
    var in_text = false
    for c in htmltree.children(doc, index)
        match doc.nodes[c].kind
            HtmlText(_, _) =>
                text = text + htmltree.text_of(doc, c)
                in_text = true
            kind =>
                if in_text
                    lines = list.push(lines, pad + "\\"" + text + "\\"")
                    text = ""
                    in_text = false
                match kind
                    HtmlElement(_, _) =>
                        lines = list.push(lines, pad + "<" + htmltree.tag_name(doc, c) + ">")
                        lines = dump_attrs(doc, c, level + 1, lines)
                        lines = dump_children(doc, c, level + 1, lines)
                    HtmlComment(r) => lines = list.push(lines, pad + "<!-- " + str.slice(doc.source, r.start, r.end) + " -->")
                    HtmlDoctype(r) => lines = list.push(lines, pad + "<!DOCTYPE " + str.slice(doc.source, r.start, r.end) + ">")
                    _ => ()
    if in_text
        lines = list.push(lines, pad + "\\"" + text + "\\"")
    lines

// The lines of an element's attributes, sorted by name, the first of a
// repeated name kept.
fn dump_attrs(doc: HtmlDoc, index: Int, level: Int, start: [Str]) -> [Str]
    var lines = start[:]
    var names: [Str] = []
    match doc.nodes[index].kind
        HtmlElement(_, attrs) =>
            for a in attrs
                let name = str.slice(doc.source, a.name.start, a.name.end)
                if not list.contains(names, name)
                    names = list.push(names, name)
        _ => ()
    names = list.sort(names)
    let pad = "| " + str.repeat("  ", level)
    for name in names
        lines = list.push(lines, pad + name + "=\\"" + (htmltree.attr(doc, index, name) ?? "") + "\\"")
    lines

// The document an input parses to, in a context or as a whole.
fn parsed(input: Str, context: Str) -> HtmlDoc
    if context == ""
        return htmlparse.parse(input)
    htmlparse.parse_fragment(input, context)
''' % (COMMIT, len(rows), header)]
    chunk = 200
    for k in range(0, len(rows), chunk):
        part = rows[k:k + chunk]
        idx = k // chunk
        out.append('// Rows %d to %d.' % (k + 1, k + len(part)))
        out.append('fn rows_%d() -> [(Str, Str, Str)]' % idx)
        out.append('    [')
        out.append(',\n'.join('        (%s, %s, %s)' % (nv(d), nv(ctx), nv(t)) for (_, d, ctx, t) in part))
        out.append('    ]')
        out.append('')
        out.append('@test')
        out.append('fn test_html5lib_tree_rows_%d() [io]' % idx)
        out.append('    var n = %d' % k)
        out.append('    for row in rows_%d()' % idx)
        out.append('        let (input, context, want) = row')
        out.append('        n = n + 1')
        out.append('        test.case("row ${n}")')
        out.append('        test.assert_eq_str(dump(parsed(input, context)), want)')
        out.append('')
    out.append('// The inputs whose trees depend on the adoption agency algorithm.')
    out.append('fn misnested() -> [Str]')
    out.append('    [')
    out.append(',\n'.join('        %s' % nv(d) for d in misnested))
    out.append('    ]')
    out.append('')
    out.append('// Whether a document reports a construct outside the subset.')
    out.append('fn reports_unsupported(doc: HtmlDoc) -> Bool')
    out.append('    for issue in doc.issues')
    out.append('        match issue.kind')
    out.append('            IssueUnsupportedConstruct(_) => return true')
    out.append('            _                            => ()')
    out.append('    false')
    out.append('')
    out.append('@test')
    out.append('fn test_each_misnested_case_is_reported_rather_than_repaired() [io]')
    out.append('    for input in misnested()')
    out.append('        test.case(input)')
    out.append('        test.assert(reports_unsupported(htmlparse.parse(input)))')
    out.append('')
    path = 'tests/html5lib_tree_tests.nv'
    open(path, 'w').write('\n'.join(out))
    subprocess.run(['novo', 'fmt', path], check=False)
    print(len(rows), 'rows;', header)


if __name__ == '__main__':
    main()
