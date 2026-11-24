#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression re-verification of every processed MDACS output.

Pairs each download/ redline output with its upload/ source (base-stem
matching: the trailing edition suffix after the 4-digit year is
stripped from both sides, with a plain-prefix fallback for the early
no-bump pilots and a pre-year fallback for outputs renamed to their
new year-aligned code — TR003C-2026.docx pairs with TR003C-2025.docx),
reads the date the output's OWN revision-history row carries, and
runs mdacs_verify.py round-trip with --bump --today DATE — so engine
or table changes can never silently alter an earlier deliverable, and
re-verification stays date-faithful however old the output is.

Usage:  python3 scripts/regression_verify.py
"""
import os
import re
import subprocess
import sys
import zipfile
from datetime import date

from defusedxml import minidom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdacs_redline as mr  # noqa: E402

UP = "/home/z/my-project/upload"
DL = "/home/z/my-project/download"
VERIFY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "mdacs_verify.py")

# one-off pilots produced before the --bump workflow (no revision row,
# no header edition bump)
NO_BUMP = {"TR-007E_2026_clean_redline.docx", "TR007E_redline.docx"}

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def base_stem(stem):
    """Stem minus the edition suffix trailing the year ('-1.1', '.1',
    '-1.0', …). Unmatched stems (pilots) come back unchanged."""
    m = re.match(r"^(.*\d{4})(?:[-.]\d+(?:\.\d+)?)?$", stem)
    return m.group(1) if m else stem


def pre_year(stem):
    """Stem with the YEAR and everything after it stripped
    ('TR003C-2026' -> 'TR003C', 'GN-00-C-2026-2' -> 'GN-00-C'); stems
    whose tail does not fit the year pattern (the pilot names) come
    back None. Used only as a LAST resort, for outputs renamed to the
    year of their new year-aligned code."""
    m = re.match(r"^(.*?)[-_ ]?\d{4}(?:[-.]\d+(?:\.\d+)?)?$", stem)
    if m:
        return m.group(1).rstrip("-_ ")
    return None


def sources():
    out = []
    for fn in os.listdir(UP):
        if fn.endswith(".docx"):
            stem = fn[:-5]
            out.append((stem, base_stem(stem), fn))
    return out


def source_for(out_stem):
    """upload/ file matching the output: equal base stem, else a plain
    stem prefix (pilot naming), else equal pre-year stem (for outputs
    renamed to their new year-aligned code, whose year differs from the
    source's). Longest source stem wins."""
    ob = base_stem(out_stem)
    best = None
    for stem, base, fn in sources():
        if base == ob or stem == ob or out_stem.startswith(stem):
            if best is None or len(stem) > len(best[0]):
                best = (stem, fn)
    if best is None:
        op = pre_year(out_stem)
        if op:
            for stem, base, fn in sources():
                if pre_year(stem) == op:
                    if best is None or len(stem) > len(best[0]):
                        best = (stem, fn)
    return best[1] if best else None


def row_date(path):
    """The date on the output's LAST revision-history row — the date the
    redline was produced. None when there is no revision table."""
    with zipfile.ZipFile(path) as z:
        dom = minidom.parseString(z.read("word/document.xml"))
    t = mr.find_revision_table(dom)
    if t is None:
        return None
    rows = t.getElementsByTagName("w:tr")
    if not rows:
        return None
    cells = mr.row_cells(rows[-1])
    s = cells[1][0].strip() if len(cells) > 1 and cells[1] else ""
    m = re.match(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m and m.group(2).lower() in _MONTHS:
        return date(int(m.group(3)), _MONTHS[m.group(2).lower()],
                    int(m.group(1)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(*(int(g) for g in m.groups()))
    return None


def main():
    outputs = sorted(fn for fn in os.listdir(DL) if fn.endswith(".docx"))
    fails, checked = [], 0
    for fn in outputs:
        stem = fn[:-5]
        src = source_for(stem)
        if src is None:
            print(f"SKIP {fn} — no source in upload/")
            continue
        if fn in NO_BUMP:
            cmd = [sys.executable, VERIFY, os.path.join(UP, src),
                   os.path.join(DL, fn)]
        else:
            d = row_date(os.path.join(DL, fn))
            if d is None:
                print(f"SKIP {fn} — no parseable revision-row date")
                continue
            cmd = [sys.executable, VERIFY, os.path.join(UP, src),
                   os.path.join(DL, fn), "--bump", "--today",
                   d.isoformat()]
        r = subprocess.run(cmd, capture_output=True, text=True)
        checked += 1
        ok = "ALL CHECKS PASSED" in r.stdout
        print(f"{'OK  ' if ok else 'FAIL'} {fn}  <-  {src}"
              + ("" if fn in NO_BUMP else
                 f"  (row date {row_date(os.path.join(DL, fn)).isoformat()})"))
        if not ok:
            fails.append(fn)
            print(r.stdout[-1500:])
    print(f"\n{checked} output(s) checked, {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
