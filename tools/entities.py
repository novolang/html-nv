#!/usr/bin/env python3
"""Write src/htmlentity.nv's table from the HTML Standard's list of
named character references.

Python's `html.entities.html5` is that list: all 2231 names, the
legacy ones without a semicolon included, each mapped to one or two
code points.  The table is written as one string per first letter, a
row of 44 bytes per name, sorted by the name padded with spaces:

    bytes 0-31   the name without its `&`, padded with spaces
    bytes 32-37  the first code point, six hexadecimal digits
    bytes 38-43  the second code point, or 000000

A lookup is a binary search on those rows.  No name holds a space and
no name is longer than 32 bytes, which is what the padding needs.

Run from the package root:  python3 tools/entities.py
Everything between the two marker lines of src/htmlentity.nv is
replaced; the rest of the file is kept.
"""
import html.entities

BEGIN = '// BEGIN GENERATED TABLE'
END = '// END GENERATED TABLE'


def rows():
    by_letter = {}
    for name, text in html.entities.html5.items():
        assert ' ' not in name and len(name) <= 32
        cps = [ord(c) for c in text]
        assert 1 <= len(cps) <= 2
        cps = cps + [0] * (2 - len(cps))
        row = '%-32s%06x%06x' % (name, cps[0], cps[1])
        by_letter.setdefault(name[0], []).append(row)
    return {k: sorted(v) for k, v in by_letter.items()}


def main():
    table = rows()
    total = sum(len(v) for v in table.values())
    assert total == 2231, total
    out = [BEGIN,
           '// Written by tools/entities.py from the HTML Standard\'s list of',
           '// %d named character references; do not edit by hand.' % total,
           '']
    arms = []
    for letter in sorted(table):
        const = 'ROWS_%s_%s' % ('UPPER' if letter.isupper() else 'LOWER', letter.upper())
        out.append('const %s = "%s"' % (const, ''.join(table[letter])))
        arms.append((letter, const))
    out.append('')
    out.append('// The rows of the names that begin with a byte, or an empty string.')
    out.append('fn rows_for(first: Int) -> Str')
    out.append('    match first')
    for letter, const in arms:
        out.append("        %d => %s" % (ord(letter), const))
    out.append('        _ => ""')
    out.append(END)
    path = 'src/htmlentity.nv'
    src = open(path).read()
    i, j = src.index(BEGIN), src.index(END) + len(END)
    open(path, 'w').write(src[:i] + '\n'.join(out) + src[j:])


if __name__ == '__main__':
    main()
