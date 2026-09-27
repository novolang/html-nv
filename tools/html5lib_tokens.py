#!/usr/bin/env python3
"""Write tests/html5lib_tokenizer_tests.nv from html5lib-tests.

html5lib-tests' `tokenizer/*.test` files are the suite HTML tokenizers
are measured against: an input, the state the tokenizer starts in, and
the exact tokens it must produce.  This script turns every case this
package can take into a row of the test file: the input, the state,
the last start tag, and the expected tokens written as one string.

Cases are left out, and counted in the file's header, for three
reasons:

- the input or the output holds U+0000 or a lone surrogate, which a
  novo-lang `Str` cannot hold;
- the case starts in the CDATA section state, which exists only in
  foreign content, which this package does not implement;
- the output names a doctype's public or system identifier, which this
  package reads and does not keep.  The doctype's name is compared.

Parse errors are not compared: this package's tokenizer does not report
them.

Run from the package root:
    python3 tools/html5lib_tokens.py [path/to/html5lib-tests]
With no argument the suite is cloned at the pinned commit.
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = 'https://github.com/html5lib/html5lib-tests.git'
COMMIT = '224991ec10db04f056a89eed8b0bd8695fd2950e'
STATES = {'Data state': 0, 'RCDATA state': 1, 'RAWTEXT state': 2,
          'Script data state': 3, 'PLAINTEXT state': 4}
SEP = '\x01'
CHUNK = 400


def fetch():
    work = tempfile.mkdtemp()
    subprocess.run(['git', 'clone', '-q', REPO, work], check=True)
    subprocess.run(['git', '-C', work, 'checkout', '-q', COMMIT], check=True)
    return work


def unescape(s):
    return re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)


def deep_unescape(x):
    if isinstance(x, str):
        return unescape(x)
    if isinstance(x, list):
        return [deep_unescape(v) for v in x]
    if isinstance(x, dict):
        return {deep_unescape(k): deep_unescape(v) for k, v in x.items()}
    return x


def storable(s):
    return '\x00' not in s and not any(0xD800 <= ord(c) <= 0xDFFF for c in s)


def expected(tokens):
    out = []
    chars = None
    for t in tokens:
        if t[0] == 'Character':
            chars = (chars or '') + t[1]
            continue
        if chars is not None:
            out.append('C' + chars)
            chars = None
        if t[0] == 'DOCTYPE':
            if t[2] is not None or t[3] is not None:
                return None
            out.append('D' + (t[1] or ''))
        elif t[0] == 'StartTag':
            attrs = ''.join('|%s=%s' % (k, v) for k, v in t[2].items())
            closing = '/' if len(t) > 3 and t[3] else ''
            out.append('S' + t[1] + attrs + closing)
        elif t[0] == 'EndTag':
            out.append('E' + t[1])
        elif t[0] == 'Comment':
            out.append('M' + t[1])
    if chars is not None:
        out.append('C' + chars)
    return SEP.join(out)


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
        elif c == '\r':
            out.append('\\r')
        elif o < 0x20 or o == 0x7F or o > 0x7E:
            out.append('\\u{%x}' % o)
        else:
            out.append(c)
    return '"' + ''.join(out) + '"'


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else fetch()
    rows, skipped = [], {'unstorable': 0, 'cdata': 0, 'doctype ids': 0}
    for path in sorted(glob.glob(os.path.join(root, 'tokenizer', '*.test'))):
        data = json.load(open(path))
        for case in data.get('tests', []):
            inp, tokens = case['input'], case['output']
            if case.get('doubleEscaped'):
                inp = unescape(inp)
                tokens = deep_unescape(tokens)
            flat = json.dumps(tokens, ensure_ascii=False)
            if not storable(inp) or not storable(flat):
                skipped['unstorable'] += 1
                continue
            want = expected(tokens)
            if want is None:
                skipped['doctype ids'] += 1
                continue
            for state in case.get('initialStates', ['Data state']):
                if state not in STATES:
                    skipped['cdata'] += 1
                    continue
                rows.append((os.path.basename(path), inp, STATES[state],
                             case.get('lastStartTag') or '', want))
    out = ['''// tests/html5lib_tokenizer_tests.nv — the tokenizer against
// html5lib-tests' tokenizer suite, at commit %s.
//
// Written by tools/html5lib_tokens.py; do not edit by hand.  Each row
// is an input, the state the tokenizer starts in, the last start tag,
// and the expected tokens: `D` a doctype's name, `S` a start tag with
// `|name=value` for each attribute and `/` when it closes itself, `E`
// an end tag, `M` a comment and `C` characters, separated by U+0001.
// %d cases are here.  %d were left out because a `Str` cannot hold
// their U+0000 or lone surrogate, %d because they start in the CDATA
// section state, which only foreign content has, and %d because they
// name a doctype's public or system identifier, which this package
// does not keep.

use std.test
use std.str
use htmlparse
use htmlentity

// The expected-token string of a tokenizer's tokens.
fn tokens_text(start: HtmlTokenizer) -> Str
    var t = start
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
                            TokenDoctype(name)            => items = list.push(items, "D" + slice(src, name))
                            TokenStartTag(name, attrs, closing) => items = list.push(items, start_text(src, name, attrs, closing))
                            TokenEndTag(name)             => items = list.push(items, "E" + slice(src, name))
                            TokenComment(r)               => items = list.push(items, "M" + slice(src, r))
                            _                             => ()
    if in_chars
        items = list.push(items, "C" + chars)
    str.join(items, "\\u{1}")

// A start tag's expected text, the first of a repeated attribute kept.
fn start_text(src: Str, name: HtmlRange, attrs: [HtmlAttr], closing: Bool) -> Str
    var out = "S" + slice(src, name)
    var seen: [Str] = []
    for a in attrs
        let key = slice(src, a.name)
        if not list.contains(seen, key)
            seen = list.push(seen, key)
            out = out + "|" + key + "=" + decoded(src, a.value, a.needs_decoding, true)
    if closing
        out = out + "/"
    out

// The text of a range.
fn slice(src: Str, r: HtmlRange) -> Str
    str.slice(src, r.start, r.end)

// The decoded text of a range.
fn decoded(src: Str, r: HtmlRange, refs: Bool, in_attr: Bool) -> Str
    if refs
        return htmlentity.decode_scan(src, r.start, r.end, in_attr).text
    slice(src, r)
''' % (COMMIT, len(rows), skipped['unstorable'], skipped['cdata'], skipped['doctype ids'])]
    chunks = [rows[i:i + CHUNK] for i in range(0, len(rows), CHUNK)]
    for k, chunk in enumerate(chunks):
        out.append('// Rows %d to %d.' % (k * CHUNK + 1, k * CHUNK + len(chunk)))
        out.append('fn rows_%d() -> [(Str, Int, Str, Str)]' % k)
        out.append('    [')
        body = []
        for (_, inp, state, last, want) in chunk:
            body.append('        (%s, %d, %s, %s)' % (nv(inp), state, nv(last), nv(want)))
        out.append(',\n'.join(body))
        out.append('    ]')
        out.append('')
        out.append('@test')
        out.append('fn test_html5lib_tokenizer_rows_%d() [io]' % k)
        out.append('    var n = %d' % (k * CHUNK))
        out.append('    for row in rows_%d()' % k)
        out.append('        let (input, state, last, want) = row')
        out.append('        n = n + 1')
        out.append('        test.case("row ${n}")')
        out.append('        test.assert_eq_str(tokens_text(htmlparse.tokenizer_state(input, state, last, false)), want)')
        out.append('')
    path = 'tests/html5lib_tokenizer_tests.nv'
    open(path, 'w').write('\n'.join(out))
    subprocess.run(['novo', 'fmt', path], check=False)
    print('%d rows, skipped %s' % (len(rows), skipped))


if __name__ == '__main__':
    main()
