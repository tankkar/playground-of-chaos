#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MDACS typo-table redliner — batch tracked-changes generator (EN + TC).

Applies the verified typo tables as Word tracked changes:

  scripts/typo_data.py      English table          (72 rows)
  scripts/typo_data_cn.py   Traditional Chinese    (60 rows)

Each table row is (reference, incorrect_text, correct_text, remark); the
reference starts with the document id (COP-01 … RS-01). A table may also
define GLOBAL_RULES = [(incorrect, correct, remark)] — corpus-wide
terminology directives with no document id; NONE is active (the
品質管理 -> 質量管理 directive of 9 Nov 2026 was retracted the same day:
the senior team decides that substitution case by case).

scripts/rule_data.py RULES = [(incorrect, correct, remark)] — the
terminology rules of the +1.0 edition (user directive, 24 Nov 2026):
corpus-wide wording replacements applied on top of the typo tables in
the same tracked-changes pass, so one redline carries both. Rules fire
wherever their incorrect text appears (body, tables, headers, footers,
notes) EXCEPT inside the revision-history table, whose historical rows
record old terminology on purpose. After packing, every rule is
re-checked against the accepted final text: occurrences remaining
outside the revision table must be ZERO.

The typo tables and the rules are the ONLY source of changes — no re-
verification, no new discoveries, no comments, and no stylistic
refinements beyond them: only errors that are flat-out wrong
(misspellings, duplicated/stray words, wrong official titles, wrong
numbers) and the stated terminology rules. Every change is a single
w:del + single w:ins authored 'denis', so the reviewer Accepts/Rejects
each item in Word (Review tab) as usual.

Usage
-----
  python mdacs_redline.py INPUT.docx [-o OUTPUT.docx] [--doc DOC-ID]
                                     [--all] [--dry-run] [--bump]
                                     [--data-dir DIR] [--skill-dir DIR]

  INPUT           a .docx from the MDACS set (any name)
  -o/--output     output path (default: <stem>_redline.docx next to the
                  input; files taken from upload/ land in download/)
  --doc DOC-ID    pin the document, e.g. --doc TR-007 (default: detected
                  from the file name, e.g. 'COP-05_2026(C).docx' -> COP-05)
  --all           try every document's rows instead (rows whose incorrect
                  text is legitimate in some OTHER document are excluded)
  --bump          edition bump (the standing workflow): output named +1.0
                  (24 Nov 2026 directive), a tracked revision-history row
                  appended, and the headers' current reference code bumped
                  to the new YEAR-ALIGNED code (12 Nov 2026 nomenclature —
                  see year_aligned_ref)
  --dry-run       report the planned changes only, write nothing

Per-file behaviour
------------------
  * rows whose incorrect text is not in the file are reported and skipped
    (e.g. an English row in a Chinese file, or a typo MDD already fixed in
    this Word version);
  * PRE-EXISTING tracked changes (any author — e.g. the drafter's own
    pending edits) are ACCEPTED into the base text before the table's
    corrections are applied, so the only revisions left pending in the
    output are the table's own (--keep-existing disables this);
  * corpus-wide terminology RULES (scripts/rule_data.py) apply in
    addition to the document's own rows — everywhere EXCEPT inside the
    revision-history table — and are re-checked after packing (zero
    occurrences of the incorrect text may remain outside it);
  * a paragraph that already shows the table's correct text is left alone;
  * every occurrence is redlined — body text, tables, headers, footers,
    footnotes and endnotes;
  * nothing else is touched: settings.xml keeps the source's
    w:trackRevisions state, and w:updateFields is stripped so Word never
    shows the update-fields dialog on open. No comments are added;
  * PRE-EXISTING COMMENTS (any author's margin comments — comments are
    not tracked changes, so they cannot be 'accepted') are REMOVED
    outright: anchors out of the story XML, comments.xml & its
    commentsExtended/Ids/Extensible payload parts, relationships and
    content-type overrides out of the package (12 Nov 2026 — the user
    requires the redline output to carry ONLY the typo tracked changes,
    not the reviewers' earlier comment threads).

Chinese-specific logic
----------------------
  * paragraph text is matched at four levels, first level with a hit wins:
        0 exact
        1 NFC-normalised
        2 whitespace-insensitive   (PDF-extraction spaces, U+3000)
        3 + full-width folded      （，） -> (,)
  * the tracked change is the minimal diff between the file's ACTUAL
    matched text and the table's correct text, so spacing / width
    variants inside the file still land on the correction the table
    specifies;
  * CJK spans may cross run boundaries — runs are split per text node
    (w:t / w:br / w:tab) so line breaks inside runs survive;
  * rows noted in the tables as having several occurrences get one
    tracked change per occurrence.

Exit code 0 = ran fine (changes or not), 1 = hard error.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import sys
import unicodedata
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation

from defusedxml import minidom

AUTHOR = "denis"
INITIALS = "D"

DEFAULT_SKILL_DIR = "/home/z/my-project/skills/docx"
DEFAULT_DATA_DIR = "/home/z/my-project/scripts"
DEFAULT_WORK_ROOT = "/home/z/my-project/work_redline"

LEVELS = (0, 1, 2, 3)
LEVEL_NAMES = ("exact", "NFC", "ws-flex", "width-flex")

STORY_RE = re.compile(
    r"^word/(document\.xml|header\d*\.xml|footer\d*\.xml|"
    r"footnotes\.xml|endnotes\.xml)$"
)
HEADER_RE = re.compile(r"^word/(header|footer)\d*\.xml$")
DOC_REF_RE = re.compile(r"[A-Z]{2,3}-\d{2,3}:\d{4}(?:-\d+)?")

# Rows whose incorrect text is CORRECT in some other document of the
# corpus: only ever applied when the document id is known (--doc or the
# file name), never in --all scan mode.
CONTEXT_DEPENDENT = {
    ("COP-03", "the List of Distributors"),        # correct in COP-05 / GN-09
    ("COP-03", "the three-year validity period"),  # correct in GN-09
    ("COP-03", "COP-03:2026(E) (Ed. 1.0)"),        # correct in the EN edition
    ("GN-09", "complaints related to any of the imported medical devices"),
    ("GN-00", "如對本概覽及醫療器械行政管理制度有任何查詢"),  # GN-01's own wording
    ("COP-04", "就有關決定提出上訴"),               # mid-sentence use elsewhere
}


# ---------------------------------------------------------------- table rows

def load_rows(data_dir=DEFAULT_DATA_DIR):
    """Rows of both tables as dicts, deduped, with pre-normalised forms.

    Per-document rows come from TYPOS; GLOBAL_RULES entries (corpus-wide
    directives, no document id — none currently active) are appended with
    doc='*' so they would be selected for every file.

    Edition flags (12 Nov 2026): a reference may carry '(TC only)' /
    '(EN only)' — the row is then excluded from the OTHER language's
    files. Only text that is CORRECT in the other edition needs it
    (COP-03C's page-header '(E) -> (C)' row: '(E)' is the right code in
    the English edition, so text presence alone cannot keep it off the
    English file). Everything else relies on presence: rows shared by
    both editions (same incorrect text in both — GN-07 / TR-006's
    English-term rows) are deduped to ONE row with src='BOTH' that fires
    on either file whose text carries it, and a TC-table row with ASCII
    text (GN-09 5.1.5 'Recognized -> Recognised') fires on the English
    edition too — that is the 9 Nov 2026 blanket-guard bug this replaces:
    the blanket filter wrongly dropped all such rows from the other
    language's selection.
    """
    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)
    import typo_data
    import typo_data_cn

    rows, seen, cor_by_inc = [], set(), {}
    for src, mod in (("EN", typo_data), ("TC", typo_data_cn)):
        for entry in mod.TYPOS:
            ref, inc, cor = entry[0], entry[1], entry[2]
            remark = entry[3] if len(entry) > 3 else ""
            m = re.match(r"\s*([A-Z]{2,3}-\d{2,3})", ref)
            if not m:
                raise SystemExit(f"ABORT: no doc id in reference {ref!r}")
            doc_id = m.group(1)
            om = re.search(r"\(\s*(EN|TC)\s*[- ]?only\s*\)", ref,
                           re.IGNORECASE)
            only = om.group(1).upper() if om else None
            key = (doc_id, inc, cor)
            if key in seen:              # same row in both tables —
                for r in rows:           # applies to BOTH editions
                    if (r["doc"], r["inc"], r["cor"]) == key:
                        r["src"] = "BOTH"
                        r["only"] = r["only"] or only
                        break
                continue
            seen.add(key)
            prev = cor_by_inc.get((doc_id, inc))
            if prev is not None and prev != cor:
                raise SystemExit(f"ABORT: conflicting corrections for "
                                 f"{doc_id} {inc!r}")
            cor_by_inc[(doc_id, inc)] = cor
            rows.append({
                "src": src, "doc": doc_id, "ref": ref, "inc": inc,
                "cor": cor, "remark": remark, "only": only,
                "kind": "typo",
                "_norms": [build_norm(inc, lv)[0] for lv in LEVELS],
            })

    for src, mod in (("EN", typo_data), ("TC", typo_data_cn)):
        for entry in getattr(mod, "GLOBAL_RULES", ()):
            inc, cor = entry[0], entry[1]
            remark = entry[2] if len(entry) > 2 else ""
            if ("*", inc, cor) in seen:
                continue
            seen.add(("*", inc, cor))
            rows.append({
                "src": src, "doc": "*", "ref": "(global)", "inc": inc,
                "cor": cor, "remark": remark, "only": None,
                "kind": "rule",
                "_norms": [build_norm(inc, lv)[0] for lv in LEVELS],
            })

    # terminology rules of the +1.0 edition (rule_data.RULES, 24 Nov
    # 2026) — corpus-wide, language-agnostic (presence-based: an
    # English edition simply never carries the CJK incorrect text), and
    # EXCLUDED from the revision-history table (see process_parts)
    import rule_data
    for entry in getattr(rule_data, "RULES", ()):
        inc, cor = entry[0], entry[1]
        remark = entry[2] if len(entry) > 2 else ""
        if ("*", inc, cor) in seen:
            continue
        seen.add(("*", inc, cor))
        rows.append({
            "src": "BOTH", "doc": "*", "ref": "(rule)", "inc": inc,
            "cor": cor, "remark": remark, "only": None,
            "kind": "rule",
            "_norms": [build_norm(inc, lv)[0] for lv in LEVELS],
        })
    return rows


def detect_language(src):
    """'TC' when the document body is predominantly Chinese, else 'EN'.

    CJK vs Latin letter counts over word/document.xml — the MDD editions
    are unambiguous (a Chinese edition is >80% CJK, an English one has
    none). Returns None when the part cannot be read."""
    try:
        with zipfile.ZipFile(src) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    text = re.sub(r"<[^>]+>", "", xml)
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff"
              or "\u3400" <= ch <= "\u4dbf"
              or "\uf900" <= ch <= "\ufaff")
    latin = sum(1 for ch in text if "a" <= ch <= "z" or "A" <= ch <= "Z")
    if cjk + latin < 50:
        return None
    return "TC" if cjk > latin else "EN"


def detect_doc_id(path, doc_ids):
    """Document id from the file name, longest token wins (TR-010 > TR-001)."""
    stem = os.path.splitext(os.path.basename(path))[0]
    norm = re.sub(r"[^A-Za-z0-9]", "", stem).upper()
    if not norm:
        return None
    for did in sorted(doc_ids, key=lambda d: (-len(d), d)):
        token = re.sub(r"[^A-Za-z0-9]", "", did).upper()
        if token and token in norm:
            return did
    return None


def canonical_doc_id(arg, doc_ids):
    token = re.sub(r"[^A-Za-z0-9]", "", arg).upper()
    for did in doc_ids:
        if re.sub(r"[^A-Za-z0-9]", "", did).upper() == token:
            return did
    raise SystemExit(f"ABORT: --doc {arg!r} matches no document in the "
                     f"tables. Known: {', '.join(sorted(doc_ids))}")


def select_rows(rows, doc_id, scan, lang=None):
    """lang ('EN' / 'TC') keeps a row unless its reference carries the
    OTHER language's '(EN only)' / '(TC only)' flag. The blanket
    same-table-only filter of 9 Nov 2026 wrongly dropped cross-edition
    ASCII rows (GN-09 5.1.5, GN-07 / TR-006's shared English-term rows)
    from the other edition's selection — flagged rows (12 Nov 2026 fix)
    are the only ones excluded, because only their text is CORRECT in
    the other edition (COP-03C's page-header '(E) -> (C)': '(E)' is the
    right code in the English edition). Rows of the other language
    whose text is simply absent report 'not present' and are skipped.
    """
    if lang:
        rows = [r for r in rows if not r.get("only") or r["only"] == lang]
    glob = [r for r in rows if r["doc"] == "*"]
    if scan:
        sel, seen_inc = [], set()
        for r in rows:
            if r["doc"] == "*":
                continue
            if (r["doc"], r["inc"]) in CONTEXT_DEPENDENT:
                continue
            if r["inc"] in seen_inc:     # same typo listed under 2+ docs: once
                continue
            seen_inc.add(r["inc"])
            sel.append(r)
        return sel + glob
    return [r for r in rows if r["doc"] == doc_id] + glob


# ------------------------------------------------------------- text matching

def _norm_char(ch, level):
    if level >= 1:
        ch = unicodedata.normalize("NFC", ch)
    if level >= 3 and len(ch) == 1:
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:            # full-width ASCII -> half-width
            ch = chr(o - 0xFEE0)
    return ch


def build_norm(text, level):
    """(normalised, back_map). back_map[i] = index in `text` of normalised
    char i; None means identity. Levels: 1 NFC, 2 + drop whitespace,
    3 + fold full-width ASCII."""
    if level == 0:
        return text, None
    if level == 1 and unicodedata.is_normalized("NFC", text):
        return text, None
    out, idx = [], []
    for i, ch in enumerate(text):
        if level >= 2 and ch.isspace():
            continue
        for c in _norm_char(ch, level):
            out.append(c)
            idx.append(i)
    return "".join(out), idx


class ParaView:
    """One paragraph's joined text + lazily cached normalisations."""
    __slots__ = ("p", "text", "_norm")

    def __init__(self, p):
        self.p = p
        self.text = joined_text(p)
        self._norm = {}

    def norm(self, lv):
        if lv not in self._norm:
            self._norm[lv] = build_norm(self.text, lv)
        return self._norm[lv]


def _all_spans(hay, needle):
    """Non-overlapping (start, end) spans of needle in hay."""
    out, k = [], hay.find(needle)
    while k >= 0:
        out.append((k, k + len(needle)))
        k = hay.find(needle, k + len(needle))
    return out


def minimal_diff(inc, cor):
    """Minimal tracked change taking `inc` (the file's actual text) to `cor`.

    The diff is computed in NFC space so that Big5 compatibility-ideograph
    variants in the file (e.g. U+F9C1 療 vs U+7642 療) do not inflate the
    change span; the deletion span is mapped back to the file's own
    characters. Returns (offset, span, repl) — delete
    inc[offset:offset+len(span)], insert `repl` in its place ('' span =
    pure insertion, '' repl = pure deletion) — or None when the two are
    NFC-equivalent (no visible change).
    """
    ninc, idx = build_norm(inc, 1)
    ncor, _ = build_norm(cor, 1)
    if ninc == ncor:
        return None
    if idx is None:
        idx = list(range(len(inc)))
    i = 0
    while i < min(len(ninc), len(ncor)) and ninc[i] == ncor[i]:
        i += 1
    j = 0
    while j < min(len(ninc), len(ncor)) - i and ninc[-1 - j] == ncor[-1 - j]:
        j += 1
    L = len(ninc) - j - i
    if L > 0:
        off = idx[i]
        span = inc[off:idx[i + L - 1] + 1]
        if unicodedata.normalize("NFC", span) != ninc[i:i + L]:
            raise SystemExit(f"ABORT: NFC back-map failed for {inc!r} -> "
                             f"{cor!r}")
    else:
        off = idx[i] if i < len(idx) else len(inc)
        span = ""
    repl = ncor[i:len(ncor) - j]
    assert span or repl, "no change"
    return off, span, repl


def plan_specs(row, view):
    """Planned changes for one row in one paragraph.

    Returns (level, specs, n_already); specs = (s, e, span, repl) in
    CURRENT-text coordinates, meant to be applied right-to-left; level None
    means the row's incorrect text is not in this paragraph at all.
    """
    text = view.text
    for lv in LEVELS:
        ninc = row["_norms"][lv]
        if not ninc:
            continue
        if lv == 0:
            hits = _all_spans(text, ninc)
        else:
            N, idx = view.norm(lv)
            hits = [(idx[a], idx[b - 1] + 1)
                    if idx is not None else (a, b)
                    for a, b in _all_spans(N, ninc)]
        if not hits:
            continue
        specs, already = [], 0
        for rs, re_ in hits:
            actual = text[rs:re_]
            d = minimal_diff(actual, row["cor"])
            if d is None:                # NFC-equivalent — already correct
                already += 1
                continue
            off, span, repl = d
            specs.append((rs + off, rs + off + len(span), span, repl))
        return lv, specs, already
    return None, [], 0


def resolve_jobs(jobs):
    """Non-overlapping subset of planned jobs, longest span first.

    Guards against two rows matching the same characters (only possible in
    --all scan mode, e.g. 「…情况」 and 「…情况。」). Returns (kept,
    dropped) with kept ordered right-to-left for application.
    """
    order = sorted(jobs, key=lambda j: (-(j[1] - j[0]), j[0]))
    kept, dropped = [], []
    for j in order:
        s, e = j[0], j[1]
        if any(e > k[0] and s < k[1] for k in kept):
            dropped.append(j)
            continue
        kept.append(j)
    kept.sort(key=lambda j: (-j[0], -j[1]))
    return kept, dropped


# --------------------------------------------------------------- XML engine

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wt(s):
    return f'<w:t xml:space="preserve">{esc(s)}</w:t>'


def wdt(s):
    return f'<w:delText xml:space="preserve">{esc(s)}</w:delText>'


def node_text(t):
    return "".join(c.nodeValue or "" for c in t.childNodes
                   if c.nodeType == c.TEXT_NODE)


def joined_text(p):
    return "".join(node_text(t) for t in p.getElementsByTagName("w:t"))


def runs_of(p):
    """(run_element, text) for runs with non-empty w:t text, doc order.

    Runs inside w:del carry w:delText (not w:t) so they contribute
    nothing; runs inside w:ins contribute their text — i.e. the 'current'
    text."""
    out = []
    for r in p.getElementsByTagName("w:r"):
        txt = "".join(node_text(t) for t in r.getElementsByTagName("w:t"))
        if txt:
            out.append((r, txt))
    return out


def _inside_ins(elem):
    anc = elem.parentNode
    while anc is not None and anc.nodeType == anc.ELEMENT_NODE:
        if anc.tagName == "w:ins":
            return True
        anc = anc.parentNode
    return False


def foreign_conflict(p, s, e):
    """True when the change [s, e) touches runs inside a PRE-EXISTING
    tracked insertion (e.g. an earlier editor's w:ins). Editing such runs
    would nest revisions — the change must be skipped instead."""
    lo = s - 1 if (s == e and s > 0) else s      # insertion: chars around s
    hi = s if s == e else e - 1
    pos = 0
    for r, txt in runs_of(p):
        rs_, re_ = pos, pos + len(txt)
        pos = re_
        if re_ > lo and rs_ <= hi and _inside_ins(r):
            return True
    return False


def rpr_xml(r):
    tags = r.getElementsByTagName("w:rPr")
    return tags[0].toxml() if tags else ""


def bucket_split(r, s_rel, e_rel):
    """Split run r's children around the text span [s_rel, e_rel).

    Returns (pre_parts, del_parts, suf_parts) as XML strings. Non-text
    children (w:br, w:tab, ...) are preserved verbatim in the bucket their
    text position falls into. s_rel == e_rel marks a pure insertion point.
    """
    pre, dele, suf = [], [], []
    pos = 0
    for child in r.childNodes:
        if child.nodeType != child.ELEMENT_NODE:
            continue
        tag = child.tagName
        if tag == "w:rPr":
            continue
        if tag == "w:t":
            txt = node_text(child)
            a, b = pos, pos + len(txt)
            pre_slice = txt[:max(0, min(len(txt), s_rel - a))]
            del_slice = txt[max(0, s_rel - a):max(0, min(len(txt), e_rel - a))]
            suf_slice = txt[min(len(txt), max(0, e_rel - a)):]
            if pre_slice:
                pre.append(wt(pre_slice))
            if del_slice:
                dele.append(wdt(del_slice))
            if suf_slice:
                suf.append(wt(suf_slice))
            pos = b
        else:
            raw = child.toxml()
            if pos <= s_rel:
                pre.append(raw)
            elif pos >= e_rel:
                suf.append(raw)
            else:
                dele.append(raw)
    return pre, dele, suf


def apply_change(editor, p, s, e, repl, ctx=""):
    """One consolidated tracked change at [s, e) of the paragraph's current
    joined run text: single w:del (if e > s) + single w:ins (if repl)."""
    joined = joined_text(p)
    if not (0 <= s <= e <= len(joined)):
        raise SystemExit(f"ABORT: change range [{s},{e}) outside paragraph "
                         f"(len {len(joined)}) {ctx}")
    span = joined[s:e]

    if not span:                                   # ---- pure insertion ----
        runs = runs_of(p)
        target, pos = None, 0
        for r, txt in runs:
            if pos <= s <= pos + len(txt):
                target = (r, txt, pos)
                break
            pos += len(txt)
        if target is None:
            raise SystemExit(f"ABORT: insertion point {s} maps to no run {ctx}")
        r, txt, rstart = target
        rpr = rpr_xml(r)
        pre, _, suf = bucket_split(r, s - rstart, s - rstart)
        ins = (f'<w:ins><w:r>{rpr}<w:t xml:space="preserve">'
               f'{esc(repl)}</w:t></w:r></w:ins>')
        parts = []
        if pre:
            parts.append(f'<w:r>{rpr}{"".join(pre)}</w:r>')
        parts.append(ins)
        if suf:
            parts.append(f'<w:r>{rpr}{"".join(suf)}</w:r>')
        editor.replace_node(r, "".join(parts))
        return

    # ---- replacement / deletion ----
    runs = runs_of(p)
    covering, pos = [], 0
    for r, txt in runs:
        rs_, re_ = pos, pos + len(txt)
        if re_ > s and rs_ < e:
            covering.append((r, txt, rs_, re_))
        pos = re_
    if not covering:
        raise SystemExit(f"ABORT: span {span!r} maps to no runs {ctx}")
    first_r, _, first_rs, _ = covering[0]
    last_r = covering[-1][0]
    rpr = rpr_xml(first_r)
    rpr_last = rpr_xml(last_r)

    pre, dele, suf = bucket_split(first_r, s - first_rs, e - first_rs)
    if len(covering) > 1:
        if suf:
            raise SystemExit(f"ABORT: unexpected suffix on first covering "
                             f"run {ctx}")
        for r, txt, _, _ in covering[1:-1]:        # fully covered middle runs
            pre2, dele2, suf2 = bucket_split(r, -1, len(txt))
            if pre2 or suf2:
                raise SystemExit(f"ABORT: middle covering run not fully "
                                 f"covered {ctx}")
            dele += dele2
        pre2, dele2, suf2 = bucket_split(
            last_r, s - covering[-1][2], e - covering[-1][2])
        if pre2:
            raise SystemExit(f"ABORT: unexpected prefix on last covering "
                             f"run {ctx}")
        dele += dele2
        suf = suf2

    parts = []
    if pre:
        parts.append(f'<w:r>{rpr}{"".join(pre)}</w:r>')
    parts.append(f'<w:del><w:r>{rpr}{"".join(dele)}</w:r></w:del>')
    if repl:
        parts.append(f'<w:ins><w:r>{rpr}<w:t xml:space="preserve">'
                     f'{esc(repl)}</w:t></w:r></w:ins>')
    if suf:
        parts.append(f'<w:r>{rpr_last}{"".join(suf)}</w:r>')
    editor.replace_node(first_r, "".join(parts))
    for r, _, _, _ in covering[1:]:
        r.parentNode.removeChild(r)


def describe(span, repl):
    if span and repl:
        return f"{span!r} -> {repl!r}"
    if span:
        return f"delete {span!r}"
    return f"insert {repl!r}"


# ------------------------------------------- accepting pre-existing edits

def _first_child(el, tag):
    for c in el.childNodes:
        if c.nodeType == c.ELEMENT_NODE and c.tagName == tag:
            return c
    return None


_SKIP_BETWEEN_PARAS = {
    "w:bookmarkStart", "w:bookmarkEnd", "w:proofErr",
    "w:commentRangeStart", "w:commentRangeEnd",
    "w:moveFromRangeStart", "w:moveFromRangeEnd",
    "w:moveToRangeStart", "w:moveToRangeEnd",
}


def _next_para(p):
    """The following sibling paragraph, or None when the next significant
    block element is not a paragraph (a table etc. — no merge possible)."""
    nxt = p.nextSibling
    while nxt is not None:
        if nxt.nodeType == nxt.ELEMENT_NODE:
            if nxt.tagName == "w:p":
                return nxt
            if nxt.tagName not in _SKIP_BETWEEN_PARAS:
                return None
        nxt = nxt.nextSibling
    return None


def _merge_para_forward(p):
    """Paragraph p carries an accepted paragraph-mark deletion: its content
    joins the FOLLOWING paragraph, which keeps its own properties (the
    surviving paragraph mark is the next paragraph's)."""
    nxt = _next_para(p)
    if nxt is None:                       # last in cell/body: keep as-is
        return
    anchor = None
    ppr = _first_child(nxt, "w:pPr")
    if ppr is not None:
        anchor = ppr.nextSibling
    if anchor is None:
        anchor = nxt.firstChild
    for child in list(p.childNodes):
        if child.nodeType == child.ELEMENT_NODE and child.tagName == "w:pPr":
            continue
        nxt.insertBefore(child, anchor)
    p.parentNode.removeChild(p)


def revision_authors(dom):
    """{author: number of tracked-change marks} in a story DOM."""
    out = {}
    for tag in ("w:ins", "w:del", "w:moveFrom", "w:moveTo"):
        for el in dom.getElementsByTagName(tag):
            a = el.getAttribute("w:author")
            if a:
                out[a] = out.get(a, 0) + 1
    return out


_PROP_CHANGES = ("w:pPrChange", "w:rPrChange", "w:tblPrChange",
                 "w:trPrChange", "w:tcPrChange", "w:sectPrChange",
                 "w:tblGridChange")

_RANGE_MARKS = ("w:moveFromRangeStart", "w:moveFromRangeEnd",
                "w:moveToRangeStart", "w:moveToRangeEnd",
                "w:customXmlInsRangeStart", "w:customXmlInsRangeEnd",
                "w:customXmlDelRangeStart", "w:customXmlDelRangeEnd",
                "w:customXmlMoveFromRangeStart", "w:customXmlMoveFromRangeEnd",
                "w:customXmlMoveToRangeStart", "w:customXmlMoveToRangeEnd")


def accept_all_revisions(dom):
    """Accept every tracked change in a story DOM (any author).

    Run-level deletions are dropped, run-level insertions unwrapped into
    plain runs, paragraph-mark insertions kept (mark removed),
    paragraph-mark deletions merge the paragraph into the following one,
    deleted table rows/cells dropped, inserted rows/cells kept (mark
    removed), moves applied (source dropped, target kept), and
    property-change records (w:pPrChange & co.) removed — the current
    properties ARE the accepted state. Returns the number of accepted
    marks. Loop runs to a fixpoint so nested/adjacent cases settle.
    """
    accepted = 0
    while True:
        n = 0
        # run-level deletions (marks inside w:rPr / w:trPr are the
        # paragraph-mark / row cases handled further down)
        for el in list(dom.getElementsByTagName("w:del")):
            par = el.parentNode
            if par is None or par.tagName in ("w:rPr", "w:trPr"):
                continue
            par.removeChild(el)
            n += 1
        # run-level insertions -> plain runs
        for el in list(dom.getElementsByTagName("w:ins")):
            par = el.parentNode
            if par is None or par.tagName in ("w:rPr", "w:trPr"):
                continue
            for child in list(el.childNodes):
                par.insertBefore(child, el)
            par.removeChild(el)
            n += 1
        # moves: source dropped, target kept
        for tag in ("w:moveFrom", "w:moveTo"):
            for el in list(dom.getElementsByTagName(tag)):
                par = el.parentNode
                if par is None:
                    continue
                if tag == "w:moveFrom":
                    par.removeChild(el)
                else:
                    for child in list(el.childNodes):
                        par.insertBefore(child, el)
                    par.removeChild(el)
                n += 1
        # range markers + property-change records: current state wins
        for tag in _RANGE_MARKS + _PROP_CHANGES:
            for el in list(dom.getElementsByTagName(tag)):
                if el.parentNode is not None:
                    el.parentNode.removeChild(el)
                    n += 1
        # paragraph-mark insertions: keep the paragraph, drop the mark
        for el in list(dom.getElementsByTagName("w:ins")):
            par = el.parentNode
            if par is not None and par.tagName == "w:rPr":
                par.removeChild(el)
                n += 1
        # paragraph-mark deletions: merge into the following paragraph
        for p in list(dom.getElementsByTagName("w:p")):
            if p.parentNode is None:
                continue
            ppr = _first_child(p, "w:pPr")
            rpr = _first_child(ppr, "w:rPr") if ppr is not None else None
            mark = _first_child(rpr, "w:del") if rpr is not None else None
            if mark is None:
                continue
            rpr.removeChild(mark)
            _merge_para_forward(p)
            n += 1
        # table rows: deleted rows out, inserted rows unmarked
        for tr in list(dom.getElementsByTagName("w:tr")):
            trpr = _first_child(tr, "w:trPr")
            if trpr is None:
                continue
            if _first_child(trpr, "w:del") is not None:
                if tr.parentNode is not None:
                    tr.parentNode.removeChild(tr)
                    n += 1
            else:
                for mark in [c for c in list(trpr.childNodes)
                             if c.nodeType == c.ELEMENT_NODE
                             and c.tagName == "w:ins"]:
                    trpr.removeChild(mark)
                    n += 1
        # table cells: deleted cells out, inserted cells unmarked
        for tc in list(dom.getElementsByTagName("w:tc")):
            tcpr = _first_child(tc, "w:tcPr")
            if tcpr is None:
                continue
            if _first_child(tcpr, "w:tcDel") is not None:
                if tc.parentNode is not None:
                    tc.parentNode.removeChild(tc)
                    n += 1
            else:
                for mark in [c for c in list(tcpr.childNodes)
                             if c.nodeType == c.ELEMENT_NODE
                             and c.tagName == "w:tcIns"]:
                    tcpr.removeChild(mark)
                    n += 1
        if n == 0:
            return accepted
        accepted += n


# --------------------------------------- removing pre-existing comments

_COMMENT_PARTS = ("word/comments.xml", "word/commentsExtended.xml",
                  "word/commentsIds.xml", "word/commentsExtensible.xml")

_RUN_CONTENT = ("w:t", "w:tab", "w:br", "w:cr", "w:sym", "w:drawing",
                "w:object", "w:delText", "w:fldChar", "w:instrText")


def _by_local(dom, local):
    """Elements whose tag is `local` or namespaced `<prefix:local>`."""
    out = []
    for el in dom.getElementsByTagName("*"):
        if el.tagName == local or el.tagName.endswith(":" + local):
            out.append(el)
    return out


def strip_comments(dom):
    """Drop every comment ANCHOR from a story DOM: w:commentRangeStart /
    w:commentRangeEnd markers and the text-less run carrying
    w:commentReference (Word puts the reference in its own anchor run;
    if a run ever mixes text and reference, only the reference goes).
    Returns the number of anchors removed."""
    removed = 0
    for tag in ("w:commentRangeStart", "w:commentRangeEnd"):
        for el in list(dom.getElementsByTagName(tag)):
            if el.parentNode is not None:
                el.parentNode.removeChild(el)
                removed += 1
    for ref in list(dom.getElementsByTagName("w:commentReference")):
        run = ref.parentNode
        if run is not None and run.nodeType == run.ELEMENT_NODE \
                and run.tagName == "w:r" \
                and not any(run.getElementsByTagName(g)
                            for g in _RUN_CONTENT) \
                and run.parentNode is not None:
            run.parentNode.removeChild(run)      # the whole anchor run
        elif ref.parentNode is not None:
            ref.parentNode.removeChild(ref)      # defensive fallback
        removed += 1
    return removed


def drop_comment_parts(work_dir):
    """Delete the comments payload from an unpacked docx and purge its
    relationships (every word/_rels/*.rels) and content-type overrides,
    leaving a package that opens with no previous reviewers' comments.
    Returns the list of part names removed (empty when it had none)."""
    removed = [p for p in _COMMENT_PARTS
               if os.path.exists(os.path.join(work_dir, p))]
    for part in removed:
        os.remove(os.path.join(work_dir, part))
    if not removed:
        return removed
    # relationships: comments*, wherever they are declared
    for rels in sorted(glob.glob(os.path.join(work_dir,
                                              "word/_rels/*.rels"))):
        dom = minidom.parse(rels)
        n = 0
        for rel in list(_by_local(dom, "Relationship")):
            if "/comments" in rel.getAttribute("Type"):
                rel.parentNode.removeChild(rel)
                n += 1
        if n:
            with open(rels, "wb") as f:
                f.write(dom.toxml(encoding="UTF-8"))
    # content types: drop the comments* overrides
    ct = os.path.join(work_dir, "[Content_Types].xml")
    dom = minidom.parse(ct)
    n = 0
    for ov in list(_by_local(dom, "Override")):
        if ov.getAttribute("PartName").lstrip("/") in _COMMENT_PARTS:
            ov.parentNode.removeChild(ov)
            n += 1
    if n:
        with open(ct, "wb") as f:
            f.write(dom.toxml(encoding="UTF-8"))
    return removed


# ---------------------------------------------------------------- front matter

def _direct_children(el, tag):
    return [c for c in el.childNodes
            if c.nodeType == c.ELEMENT_NODE and c.tagName == tag]


def find_revision_table(dom):
    """The revision-history w:tbl: first table whose header row mentions
    版本, Edition or Version (TR-004/5/6 E editions head theirs 'Version
    Number'; TR-001E's own header drops the space — 'VersionNumber', 12
    Nov 2026). None when the file has no such table."""
    for t in dom.getElementsByTagName("w:tbl"):
        rows = t.getElementsByTagName("w:tr")
        if not rows:
            continue
        head = " ".join(node_text(tt) for tt in rows[0].getElementsByTagName("w:t"))
        if ("版本" in head or "Edition" in head
                or re.search(r"\bVersion\b", head) or "VersionNumber" in head):
            return t
    return None


def row_cells(tr):
    """[[para text, ...], ...] — the text of each cell's paragraphs."""
    out = []
    for tc in tr.getElementsByTagName("w:tc"):
        out.append([joined_text(p) for p in tc.getElementsByTagName("w:p")])
    return out


def bump_decimal(s):
    """'7' -> '8', '1.0' -> '2.0', '1.2' -> '2.2' — an increment of 1.0.

    User directive, 24 Nov 2026: the combined typo + terminology-rule
    edition is a MAJOR step, not the +0.1 typo-only step of 9-12 Nov
    2026. Integer versions stay integers so the column keeps each
    table's own grammar ('0' -> '1', '15' -> '16'); decimals add a
    whole 1.0 and keep their minor digit ('(Ed. 1.2)' -> '(Ed. 2.2)')."""
    t = s.strip()
    d = Decimal(t) + Decimal("1.0")
    return str(int(d)) if "." not in t else str(d)


def bump_ref(ref):
    """LEGACY edition bump — only the '(Ed. X.Y)' branch is live
    (year_aligned_ref delegates to it); the counter/bare-year branches
    survive for context-free callers and are superseded by the 12 Nov
    2026 year-aligned nomenclature (year_aligned_ref).

    '(Ed. X.Y)' codes (2026 documents): 'GN-01:2026(C) (Ed. 3.0)' ->
    'GN-01:2026(C) (Ed. 4.0)' — the +1.0 directive of 24 Nov 2026.
    Older '-N' counters: 'GN-00:2026-1(C)' -> 'GN-00:2026-2(C)'. A bare
    year gets '-1' appended ('GN-00:2026(C)' -> 'GN-00:2026-1(C)')."""
    m = re.search(r"\(Ed\.?\s*(\d+(?:\.\d+)?)(?!\d)", ref)
    if m:
        return ref[:m.start(1)] + bump_decimal(m.group(1)) + ref[m.end(1):]
    m = re.search(r"(\d{4}-)(\d+)(?!\d)", ref)
    if m:
        return ref[:m.start(2)] + bump_decimal(m.group(2)) + ref[m.end(2):]
    m = re.search(r"\d{4}(?!\d)(?!-)", ref)
    if m:
        return ref[:m.end()] + "-1" + ref[m.end():]
    return ref


def _date_year(s):
    """The year of a revision-row date cell — CJK ('2026年9月1日'),
    English ('12 November 2026') or ISO ('2026-11-12') alike; None when
    the cell carries no year at all ('NIL', '不適用')."""
    m = re.search(r"(?:19|20)\d{2}", s or "")
    return int(m.group(0)) if m else None


def _ref_year(ref):
    """The year inside a reference code ('TR-003:2025-1(C)' -> 2025);
    None when the code carries none."""
    m = re.search(r":\s*((?:19|20)\d{2})", ref or "")
    return int(m.group(1)) if m else None


def year_aligned_ref(ref, year, n_prior):
    """The NEXT update's reference code under the MDACS year-aligned
    nomenclature (user directive, 12 Nov 2026): the code's year is the
    year of the update itself, and the counter counts that year's
    updates — the first update of a year carries the bare year
    ('TR-003:2026(C)'), the second '-1' ('TR-007:2026-1(C)'), the third
    '-2' ('GN-00:2026-2(C)'); the counter restarts each year.
    n_prior = how many revision rows the table already dates to `year`.

    Codes carrying an '(Ed. X.Y)' part keep the documents' OWN
    convention instead (the MDD's 2026 COP/GN sequence): the (Ed.)
    number bumps +1.0 (24 Nov 2026 directive — the combined typo + rule
    edition is a major step) and the year part stays the year that
    sequence began — 'GN-01:2026(C) (Ed. 3.0)' -> 'GN-01:2026(C)
    (Ed. 4.0)'. Everything but the year/counter (prefix, spacing, the
    '(C)'/'(E)' language code) is preserved from the code being bumped."""
    if re.search(r"\(Ed\.?\s*\d+(?:\.\d+)?", ref):
        return bump_ref(ref)                # the documents' own sequence
    m = re.search(r":\s*((?:19|20)\d{2})(\s*-\s*\d+(?:\.\d+)?)?", ref)
    if m is None:
        return ref
    end = m.end(2) if m.group(2) else m.end(1)
    counter = f"-{n_prior}" if n_prior else ""
    return ref[:m.start(1)] + f"{year}" + counter + ref[end:]


def _base_year_ref(ref):
    """`ref` minus the in-year counter and the '(Ed. …)' part — the
    year-edition form a header often carries while the table's own
    current code has a counter ('TR-003:2025-1(C)' -> 'TR-003:2025(C)').
    None when the code already IS that form (nothing stripped)."""
    r = (ref or "").strip()
    r2 = re.sub(r"\s*\(Ed\.?\s*\d+(?:\.\d+)?\)\s*$", "", r)
    r2 = re.sub(r"\s*-\s*\d+(?:\.\d+)?\s*(?=[(（])", "", r2)
    r2 = re.sub(r"\s*-\s*\d+(?:\.\d+)?\s*$", "", r2)
    return r2 if r2 != r else None


def _year_refresh(ref, year):
    """Year-only refresh of a year-edition code — 'TR-003:2025(C)' ->
    'TR-003:2026(C)'; the counter-less form is kept."""
    m = re.search(r":\s*((?:19|20)\d{2})", ref)
    if m is None:
        return ref
    return ref[:m.start(1)] + f"{year}" + ref[m.end(1):]


def format_date_like(sample, today):
    """Today's date in the same shape as the file's own revision dates.

    The CJK branch tolerates drafter-inserted spaces around 年/月/日
    (TR-009C's only row reads '2025 年 10月 2 日' — 12 Nov 2026 fix: the
    strict '\\d{4}年' anchor missed that form and fell through to the ISO
    fallback). The emitted date is the corpus-standard compact form."""
    if re.search(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日", sample):
        return f"{today.year}年{today.month}月{today.day}日"
    if re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", sample):
        return f"{today.day} {today.strftime('%B')} {today.year}"
    return f"{today.year}-{today.month:02d}-{today.day:02d}"


def _clause_numbers(ref):
    """Clause numbers a table row's reference points at, in order, deduped —
    e.g. 'GN-01 sections 4.4.9 and 5.13 (2 occurrences)' -> ['4.4.9',
    '5.13']; 'TR-010 sections 5.1.5/5.1.6 and Appendix I/II titles …' ->
    ['5.1.5', '5.1.6']. Parenthesised qualifiers are ignored."""
    out = []
    for m in re.finditer(r"sections?\s+", ref):
        seg = ref[m.end():].split("(", 1)[0]
        for tok in re.findall(r"\d+(?:\.\d+)*", seg):
            if tok not in out:
                out.append(tok)
    return out


_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
          "VII": 7, "VIII": 8, "IX": 9, "X": 10}


def _appendix_tokens(ref):
    """Appendix labels a table row's reference points at, in order,
    deduped — e.g. 'GN-07 Appendix II (Annex I address)' -> ['II'].
    Annex/附件 qualifiers are ignored: they live INSIDE the appendix.
    Slash lists are expanded (12 Nov 2026 fix — TR-010C's row reads
    'Appendix I/II titles', which the single-token pattern truncated to
    ['I'], dropping 附錄II from the merged summary): 'Appendix I/II' ->
    ['I', 'II']."""
    out = []
    for m in re.finditer(
            r"Appendix\s+((?:[IVX]+|\d+)(?:\s*/\s*(?:[IVX]+|\d+))*)", ref):
        for tok in re.split(r"\s*/\s*", m.group(1)):
            if tok and tok not in out:
                out.append(tok)
    return out


def _clause_key(tok):
    return tuple(int(x) for x in tok.split("."))


def _appendix_key(tok):
    return _ROMAN.get(tok) or (int(tok) if tok.isdigit() else 99)


def summary_lines(applied_rows, tc):
    """Revision-summary lines for the corrections that actually fired.

    Merged into ONE line (user directive, 9 Nov 2026): all clause numbers
    in a single list, in document order — TC 「更正了第2.10、2.16及2.20節
    的拼寫錯誤」, EN 'Typos in clauses 2.2, 2.25 and 3.1 are fixed'.
    Appendix targets join the same line (clause list joined with 、, 及
    before the appendix — the documents' own style, cf. GN-07's 「修改了
    第6.1.1、6.2.1、8.2.1節及附錄II中的附件1」): TC 「更正了第8.5.1節
    及附錄II的拼寫錯誤」, EN 'Typos in clauses 4.1.3, 5.2.6, 5.3.1, 10.1
    and Appendix II are fixed'. Grammar (12 Nov 2026 fix): the EN
    singular is kept iff exactly ONE clause/appendix-bearing correction
    fired — rows may carry a 'fires' occurrence count; several typos in
    ONE clause now read 'Typos in clause 7.1 are fixed' (TR-003E), two
    in clause 8.4 'Typos in clause 8.4 are fixed' (GN-02). TC has no
    grammatical number and is unaffected. Rows whose reference carries
    neither a clause number nor an appendix label contribute one extra
    「更正了其他拼寫錯誤」 / 'Other typos are fixed' line (rare), and each
    terminology rule (rule_data.RULES) gets its own line — TC
    「質量體系」取代「品質體系」， EN '"X" replaces "Y"'.
    """
    clauses, appendices, generic, glob = [], [], 0, []
    n_fires = 0                    # clause/appendix-bearing corrections
    for r in applied_rows:
        if r["doc"] == "*":
            glob.append(r)
            continue
        nums = _clause_numbers(r["ref"])
        apps = _appendix_tokens(r["ref"])
        for c in nums:
            if c not in clauses:
                clauses.append(c)
        for a in apps:
            if a not in appendices:
                appendices.append(a)
        if nums or apps:
            n_fires += r.get("fires", 1)
        if not nums and not apps:
            generic += 1
    clauses.sort(key=_clause_key)
    appendices.sort(key=_appendix_key)

    def join_and(items):        # A、B及C  /  A, B and C
        if len(items) > 1:
            sep = "、" if tc else ", "
            return sep.join(items[:-1]) + ("及" if tc else " and ") \
                + items[-1]
        return items[0]

    lines = []
    if tc:
        if clauses and appendices:      # …、Z節及附錄II
            apps = ("及".join(f"附錄{a}" for a in appendices)
                    if len(appendices) > 1 else f"附錄{appendices[0]}")
            lines.append("更正了第" + "、".join(clauses)
                         + f"節及{apps}的拼寫錯誤")
        elif clauses:
            lines.append(f"更正了第{join_and(clauses)}節的拼寫錯誤")
        elif appendices:
            lines.append("更正了"
                         + join_and([f"附錄{a}" for a in appendices])
                         + "的拼寫錯誤")
    else:
        one = n_fires == 1
        apps = [f"Appendix {a}" for a in appendices]
        if clauses and apps:
            head = "clause " if len(clauses) == 1 else "clauses "
            items = [head + clauses[0]] + clauses[1:] + apps
            lines.append(("Typo in " if one else "Typos in ")
                         + join_and(items)
                         + (" is" if one else " are") + " fixed")
        elif clauses:
            clause_word = "clause " if len(clauses) == 1 else "clauses "
            lines.append(("Typo in " if one else "Typos in ")
                         + clause_word + join_and(clauses)
                         + (" is" if one else " are") + " fixed")
        elif apps:
            lines.append(("Typo in " if one else "Typos in ")
                         + join_and(apps)
                         + (" is" if one else " are") + " fixed")
    if generic:
        lines.append("更正了其他拼寫錯誤" if tc else "Other typos are fixed")
    for g in glob:
        if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", g["inc"] + g["cor"]):
            lines.append(f"「{g['cor']}」取代「{g['inc']}」")
        else:
            lines.append(f"“{g['cor']}” replaces “{g['inc']}”")
    return lines


def revision_row_plan(dom, applied_rows, today=None):
    """Derive the new revision-history row from the file's own last row.

    Returns None when there is no 4-column revision table, the version cell
    is not numeric, or no corrections fired. The row's texts mirror the
    document's own conventions: the version cell bumped +1.0 (24 Nov 2026
    directive — the combined typo + rule edition is a major step), today's
    date in the
    file's format, all fired corrections' clause numbers merged into ONE
    summary line, and the YEAR-ALIGNED reference code (12 Nov 2026): the
    code's year is THIS update's year and its counter counts that year's
    updates — first 'TR-003:2026(C)', second 'TR-007:2026-1(C)', third
    'GN-00:2026-2(C)' — read off the rows the table already carries
    (dates parsed per file, CJK included). Codes with an '(Ed. X.Y)'
    part keep their own convention: '(Ed. 3.0)' -> '(Ed. 3.1)', year
    part untouched. base_ref (the code's year-edition form) is exposed
    so the header pass can refresh year-form header codes when the year
    changes.
    """
    t = find_revision_table(dom)
    if t is None:
        return None
    trs = t.getElementsByTagName("w:tr")
    cells = row_cells(trs[-1])
    if len(cells) != 4 or not cells[0] or not cells[3]:
        return None
    try:
        version = bump_decimal(cells[0][0])
    except (InvalidOperation, ValueError):
        return None
    date_s = cells[1][0].strip() if cells[1] else ""
    today = today or date.today()
    ref = cells[3][0].strip()
    lines = summary_lines(applied_rows, tc=bool(re.search(r"\d{4}\s*年", date_s)))
    if not lines:
        return None

    def row_year(tr):
        cs = row_cells(tr)
        if len(cs) > 1 and cs[1]:
            return _date_year(cs[1][0])
        return None

    n_prior = sum(1 for tr in trs[1:] if row_year(tr) == today.year)
    new_ref = year_aligned_ref(ref, today.year, n_prior)
    base_ref = (_base_year_ref(ref) if _ref_year(ref) != today.year
                else None)
    return {
        "version": version, "date": format_date_like(date_s, today),
        "ref": new_ref, "old_ref": ref,
        "ref_year": today.year, "ref_prior": n_prior, "base_ref": base_ref,
        "cells": [[version], [format_date_like(date_s, today)], lines,
                  [new_ref]],
        "n_lines": len(lines),
        "doc_prefix": ref.split(":")[0] if ":" in ref else None,
    }


def _with_ins_mark(ppr_xml):
    """Add the paragraph-insertion mark (<w:ins/>) to a w:pPr XML string."""
    if "</w:pPr>" not in ppr_xml:
        return ppr_xml                       # self-closing / no children
    if "<w:rPr" in ppr_xml:
        return re.sub(r"<w:rPr[^>]*>", lambda m: m.group(0) + "<w:ins/>",
                      ppr_xml, count=1)
    return ppr_xml.replace("</w:pPr>", "<w:rPr><w:ins/></w:rPr></w:pPr>", 1)


def build_revision_row(last_tr, cells):
    """XML for a tracked-insertion table row mirroring last_tr's formatting.

    Copies the last row's w:trPr (with a w:ins row mark), each cell's
    w:tcPr and first paragraph's w:pPr/w:rPr; every new paragraph's runs
    are wrapped in w:ins and its paragraph mark carries w:rPr/w:ins.
    cells: [[para text, ...], ...] — one list per column.
    """
    trprs = _direct_children(last_tr, "w:trPr")
    if trprs:
        x = trprs[0].toxml()
        m = re.match(r"<w:trPr[^>]*>", x)
        trpr = x[:m.end()] + "<w:ins/>" + x[m.end():] if m else "<w:trPr><w:ins/></w:trPr>"
    else:
        trpr = "<w:trPr><w:ins/></w:trPr>"
    tcs = _direct_children(last_tr, "w:tc")
    if len(tcs) != len(cells):
        raise SystemExit(f"ABORT: revision row has {len(tcs)} cell(s), "
                         f"planned {len(cells)}")
    parts = ["<w:tr>", trpr]
    for tc, texts in zip(tcs, cells):
        tcprs = _direct_children(tc, "w:tcPr")
        tcpr = tcprs[0].toxml() if tcprs else ""
        pps = _direct_children(tc, "w:p")
        ppr, rpr = "", ""
        if pps:
            pprs = _direct_children(pps[0], "w:pPr")
            if pprs:
                ppr = _with_ins_mark(pprs[0].toxml())
            for r in pps[0].getElementsByTagName("w:r"):
                if r.getElementsByTagName("w:t"):
                    rprs = _direct_children(r, "w:rPr")
                    rpr = rprs[0].toxml() if rprs else ""
                    break
        ps = [f"<w:p>{ppr}<w:ins><w:r>{rpr}"
              f'<w:t xml:space="preserve">{esc(tx)}</w:t>'
              f"</w:r></w:ins></w:p>" for tx in texts]
        parts.append(f"<w:tc>{tcpr}{''.join(ps)}</w:tc>")
    parts.append("</w:tr>")
    return "".join(parts)


def _flex_ref_pattern(ref):
    """Whitespace-flexible regex matching one exact reference code.

    'GN-06:2026(C) (Ed. 1.2)' also matches 'GN-06:2026 (C) (Ed. 1.2)' or
    'GN-06:2026(C)(Ed.1.2)' — header textboxes space the code either way
    — by allowing optional whitespace between every pair of characters."""
    chars = [re.escape(c) for c in ref.strip() if not c.isspace()]
    return re.compile(r"\s*".join(chars)) if chars else None


def ref_bump_edits_in_text(text, doc_prefix, only_ref=None, bump_year=None,
                           bump_prior=None, base_ref=None):
    """[(start, end, span, repl)] for every edition reference of
    doc_prefix found in `text`, bumped to its new code.

    only_ref — the revision table's current reference code: when given,
    ONLY occurrences equal to it (whitespace apart) are bumped — to the
    year-aligned code when bump_year/bump_prior carry the nomenclature
    context (12 Nov 2026), else with the legacy +0.1 bump. base_ref —
    the same code's year-edition form (counter stripped): its
    occurrences get their YEAR refreshed to bump_year
    ('TR-003:2025(C)' -> 'TR-003:2026(C)'), so a header that carries
    the year form while the table's current code has a counter still
    rides along when the year changes. A header may also carry stale
    codes — an older edition ('GN-09:2024-1(E)'), a code missing its
    '(Ed. …)' part, or a wrong edition; those stay untouched rather
    than being bumped into codes that never existed."""
    out = []
    if only_ref:
        def bump_to(found):
            if bump_year is None:
                return bump_ref(found)          # legacy, no context
            return year_aligned_ref(found, bump_year, bump_prior or 0)

        for pat_src, transform in (
                (only_ref, bump_to),
                (base_ref, lambda f: _year_refresh(f, bump_year))):
            if pat_src is None:
                continue
            pat = _flex_ref_pattern(pat_src)
            if pat is None:
                continue
            for m in pat.finditer(text):
                found = m.group(0)
                bumped = transform(found)
                if bumped == found:
                    continue
                d = minimal_diff(found, bumped)
                if d is None:
                    continue
                off, span, repl = d
                s = m.start() + off
                out.append((s, s + len(span), span, repl))
        return out
    if not doc_prefix:
        return out
    for m in DOC_REF_RE.finditer(text):
        found = m.group(0)
        if not found.startswith(doc_prefix + ":"):
            continue
        bumped = bump_ref(found)
        if bumped == found:
            continue
        d = minimal_diff(found, bumped)
        if d is None:
            continue
        off, span, repl = d
        s = m.start() + off
        out.append((s, s + len(span), span, repl))
    return out


def header_ref_edits(dom, doc_prefix, only_ref=None, bump_year=None,
                     bump_prior=None, base_ref=None):
    """[(para_idx, start, end, span, repl)] — edition-reference bumps for
    every paragraph of a header/footer part (current text). Paragraphs
    whose text is aggregated from a nested textbox are skipped: their
    nested paragraphs are visited on their own."""
    out = []
    for pi, p in enumerate(dom.getElementsByTagName("w:p")):
        if p.getElementsByTagName("w:txbxContent"):
            continue
        for s, e, span, repl in ref_bump_edits_in_text(
                joined_text(p), doc_prefix, only_ref=only_ref,
                bump_year=bump_year, bump_prior=bump_prior,
                base_ref=base_ref):
            out.append((pi, s, e, span, repl))
    return out


EMU_PER_PT = 12700
WIDEN_PT = 15.0
GLYPH_PT = 7.5          # per-inserted-glyph width estimate (10pt bold headers)


def widen_ref_textboxes(dom, doc_prefix, only_ref=None, new_ref=None,
                        base_ref=None, delta_pt=WIDEN_PT,
                        markup_fit=False):
    """Widen every textbox whose content carries this document's edition
    reference.

    Flat mode (default): every matching textbox grows by delta_pt — used
    when a LONGER bumped code ('-1' -> '-1.1') must still fit on one
    line.

    markup_fit mode: each textbox grows by ITS OWN markup-view growth
    instead — GLYPH_PT per character of text inserted inside it
    (tracked deletions stay visible, struck through, keeping their
    original width; insertions add width on top). Even a same-length
    bump ('(Ed. 1.0)' -> '(Ed. 1.1)') or a same-length language-code
    fix ('(E)' -> '(C)') renders 1-2 glyphs wider in Word's markup view
    and wraps + clips inside a tight one-line box (observed on the
    COP-03C / COP-04E / COP-05E running headers). Matching in this mode
    is by doc prefix only (looser than only_ref): after the edits land,
    a box's accept-view text can read 'COP-03:2026(C) (Ed. 11)' — the
    deleted '0' gone from w:t, the inserted '1' in — which the exact
    patterns would not match. Boxes with no insertions (growth 0) are
    left untouched.

    Shape geometry is not trackable in OOXML, so this is a direct
    formatting adjustment accompanying the tracked text edits: the
    DrawingML size (wp:extent + wps a:ext) and the VML fallback width
    all grow; right-anchored boxes extend inwards, so the visible
    position does not move. only_ref/new_ref/base_ref limit flat-mode
    widening to textboxes carrying one of those references. Returns the
    number of textboxes widened."""
    if not doc_prefix and not only_ref:
        return 0
    pats = ([p for p in map(_flex_ref_pattern,
                            [r for r in (only_ref, new_ref, base_ref) if r])
            if p]
            if only_ref else [])
    n = 0
    for tb in dom.getElementsByTagName("w:txbxContent"):
        text = "".join(node_text(t) for t in tb.getElementsByTagName("w:t"))
        if markup_fit:
            if not any(f.startswith(doc_prefix + ":")
                       for f in DOC_REF_RE.findall(text)):
                continue
            growth = sum(len(node_text(t))
                         for ins in tb.getElementsByTagName("w:ins")
                         for t in ins.getElementsByTagName("w:t"))
            if growth <= 0:
                continue                       # no insertions -> no growth
            box_pt = growth * GLYPH_PT
        else:
            if pats:
                if not any(p.search(text) for p in pats):
                    continue
            elif not any(f.startswith(doc_prefix + ":")
                         for f in DOC_REF_RE.findall(text)):
                continue
            box_pt = delta_pt
        anchor = spPr = vshape = None
        anc = tb.parentNode
        while anc is not None and anc.nodeType == anc.ELEMENT_NODE:
            if anc.tagName == "wp:anchor" and anchor is None:
                anchor = anc
            elif anc.tagName == "wps:spPr" and spPr is None:
                spPr = anc
            elif anc.tagName == "v:shape" and vshape is None:
                vshape = anc
            anc = anc.parentNode
        delta = int(round(box_pt * EMU_PER_PT))
        touched = False
        if anchor is not None:
            for ext in anchor.getElementsByTagName("wp:extent"):
                cx = int(ext.getAttribute("cx")) + delta
                ext.setAttribute("cx", str(cx))
                touched = True
        if spPr is not None:
            for xfrm in spPr.getElementsByTagName("a:xfrm"):
                for ext in xfrm.getElementsByTagName("a:ext"):
                    cx = int(ext.getAttribute("cx")) + delta
                    ext.setAttribute("cx", str(cx))
                    touched = True
        if vshape is not None and vshape.hasAttribute("style"):
            style = vshape.getAttribute("style")
            style = re.sub(
                r"width:([\d.]+)pt",
                lambda m: f"width:{float(m.group(1)) + box_pt:g}pt",
                style, count=1)
            vshape.setAttribute("style", style)
            touched = True
        if touched:
            n += 1
    return n


def apply_frontmatter(parts, doc_id, applied_rows, dry_run=False):
    """Edition-bump front matter: append the tracked revision-history row
    and bump every header/footer edition reference to the new
    year-aligned code (12 Nov 2026 nomenclature).

    parts: [(part_name, editor)] — word/document.xml must come first (the
    revision table supplies the doc prefix for the header bump). Returns
    (row_plan_or_None, n_header_edits).
    """
    plan, n_edits = None, 0
    for name, ed in parts:
        dom = ed.dom
        if name == "word/document.xml":
            plan = revision_row_plan(dom, applied_rows)
            if plan is None:
                print("  front matter: no usable revision-history table — "
                      "summary row not added")
                continue
            print(f"  front matter: revision row appended — {plan['version']}"
                  f" | {plan['date']} | {plan['n_lines']} summary line(s) | "
                  f"{plan['ref']}")
            if not dry_run:
                last_tr = find_revision_table(dom).getElementsByTagName(
                    "w:tr")[-1]
                ed.insert_after(last_tr, build_revision_row(last_tr,
                                                            plan["cells"]))
        elif HEADER_RE.match(name):
            if plan is None:
                # no revision row — no new code exists, so there is
                # nothing to point the headers at
                continue
            prefix = plan["doc_prefix"] or doc_id
            only_ref = plan["old_ref"]
            bypara = {}
            for pi, s, e, span, repl in header_ref_edits(
                    dom, prefix, only_ref=only_ref,
                    bump_year=plan["ref_year"],
                    bump_prior=plan["ref_prior"],
                    base_ref=plan["base_ref"]):
                bypara.setdefault(pi, []).append((s, e, span, repl))
            n_applied = 0
            grew = False
            for pi, jobs in bypara.items():
                jobs.sort(key=lambda j: (-j[0], -j[1]))
                p = dom.getElementsByTagName("w:p")[pi]
                for s, e, span, repl in jobs:
                    if foreign_conflict(p, s, e):
                        print(f"  [foreign-revision-skip] [edition bump] "
                              f"{name} para {pi} — inside a pre-existing "
                              f"tracked insertion; left untouched")
                        continue
                    ctx = f"[edition bump] {name} para {pi}"
                    print(f"  {ctx}  {describe(span, repl)}")
                    if not dry_run:
                        apply_change(ed, p, s, e, repl, ctx)
                    n_edits += 1
                    n_applied += 1
                    grew = grew or len(repl) > len(span)
            widened = 0
            if n_applied and grew:
                widened += widen_ref_textboxes(dom, prefix,
                                               only_ref=only_ref,
                                               new_ref=plan["ref"],
                                               base_ref=plan["base_ref"])
            # markup-view fit: even same-length bumps / language-code
            # fixes render wider with the tracked marks shown
            widened += widen_ref_textboxes(dom, prefix,
                                           only_ref=only_ref,
                                           new_ref=plan["ref"],
                                           base_ref=plan["base_ref"],
                                           markup_fit=True)
            if widened:
                print(f"  [edition bump] {name}: {widened} textbox(es) "
                      f"widened so the bumped reference (and its markup "
                      f"view) still fits on one line")
    return plan, n_edits


# ------------------------------------------------------------------- parts

def story_parts(work_dir):
    """Story parts present in an unpacked docx directory (document first)."""
    word = os.path.join(work_dir, "word")
    parts = ["word/document.xml"]
    for pat in ("header*.xml", "footer*.xml", "footnotes.xml", "endnotes.xml"):
        parts += sorted("word/" + os.path.basename(f)
                        for f in glob.glob(os.path.join(word, pat)))
    return [p for p in parts
            if os.path.exists(os.path.join(work_dir, p))]


def story_parts_in_zip(zf):
    names = [n for n in zf.namelist() if STORY_RE.match(n)]
    doc = [n for n in names if n == "word/document.xml"]
    return doc + sorted(n for n in names if n != "word/document.xml")


def settings_of(zf):
    try:
        return zf.read("word/settings.xml").decode("utf-8")
    except KeyError:
        return ""


# ------------------------------------------------------------------ driver

class _DomOnly:
    """Read-only stand-in for the skill's editor (dry-run mode)."""
    def __init__(self, dom):
        self.dom = dom


def revision_table_para_ids(dom):
    """id()s of the paragraphs inside the revision-history table.

    Rule rows skip these: the historical rows record the old
    terminology on purpose (e.g. GN-00's 2025 row quotes
    「醫療儀器行政管理制」 as the term being REPLACED), so rewriting
    them would falsify the record. Typo rows are unaffected — they are
    clause-targeted and never matched there in practice."""
    t = find_revision_table(dom)
    if t is None:
        return frozenset()
    return frozenset(id(p) for p in t.getElementsByTagName("w:p"))


def process_parts(parts, rows, apply_fn=None):
    """Paragraph-major pass over all story parts.

    parts: list of (part_name, editor) where editor has .dom (and
    .replace_node when apply_fn is used). Returns (total_changes, stats)
    with one stats dict per row: applied / already / hit / rev_skipped
    (rule occurrences found inside the revision-history table and kept
    as-is on purpose).
    """
    stats = [{"applied": 0, "already": 0, "hit": False, "rev_skipped": 0}
             for _ in rows]
    total = 0
    has_rules = any(r.get("kind") == "rule" for r in rows)
    for name, ed in parts:
        rev_ids = (revision_table_para_ids(ed.dom) if has_rules
                   else frozenset())
        for pi, p in enumerate(ed.dom.getElementsByTagName("w:p")):
            if p.getElementsByTagName("w:txbxContent"):
                continue    # text lives in nested textbox paragraphs,
                            # which are iterated on their own — editing
                            # the outer aggregation would double-apply
            view = ParaView(p)
            if not view.text:
                continue
            in_rev = id(p) in rev_ids
            jobs = []
            for ri, row in enumerate(rows):
                if in_rev and row.get("kind") == "rule":
                    _, specs, _ = plan_specs(row, view)
                    stats[ri]["rev_skipped"] += len(specs)
                    continue
                lv, specs, already = plan_specs(row, view)
                if lv is None:
                    continue
                stats[ri]["hit"] = True
                stats[ri]["already"] += already
                for s, e, span, repl in specs:
                    jobs.append((s, e, span, repl, ri, lv))
            if not jobs:
                continue
            kept, dropped = resolve_jobs(jobs)
            for j in dropped:
                row = rows[j[4]]
                print(f"  [overlap-skip] {row['ref']} — overlaps another "
                      f"change at the same spot")
            for s, e, span, repl, ri, lv in kept:
                row = rows[ri]
                ctx = f"[{row['ref']}] {name} para {pi}"
                if foreign_conflict(p, s, e):
                    print(f"  [foreign-revision-skip] {ctx} — the text sits "
                          f"inside a pre-existing tracked insertion; left "
                          f"untouched")
                    continue
                print(f"  {ctx}  {describe(span, repl)}  ({LEVEL_NAMES[lv]})")
                if apply_fn is not None:
                    apply_fn(ed, p, s, e, repl, ctx)
                stats[ri]["applied"] += 1
                total += 1
    return total, stats


def strip_update_prompts(work_dir, keep_track_revisions):
    """Revert the settings.xml flags the Document helper adds.

    w:updateFields makes Word show the update-fields dialog on open — out.
    w:trackRevisions is kept only when the SOURCE file already had it on,
    so the output opens exactly in the state the user provided.
    w:revisionView (display state of the last Word session, e.g.
    w:markup="0" = Final view) is dropped too: several MDACS sources were
    last saved in Final view, which would open the redline with the
    tracked changes HIDDEN in both Word and LibreOffice — the reviewer
    must see the markup to accept/reject it.
    """
    path = os.path.join(work_dir, "word/settings.xml")
    dom = minidom.parse(path)
    remove = ["w:updateFields", "w:revisionView"]
    if not keep_track_revisions:
        remove.append("w:trackRevisions")
    removed = []
    for tag in remove:
        for elem in list(dom.getElementsByTagName(tag)):
            elem.parentNode.removeChild(elem)
            removed.append(tag)
    with open(path, "wb") as f:
        f.write(dom.toxml(encoding="UTF-8"))
    print(f"  settings: removed {sorted(set(removed)) or 'nothing'}")


def _import_docx_api(skill_dir):
    if skill_dir not in sys.path:
        sys.path.insert(0, skill_dir)
    from scripts.document import Document
    return Document


def _pack_preserving(work_dir, out):
    """Zip work_dir -> out WITHOUT the skill packer's _condense_xml pass.

    That pass strips whitespace-only text nodes from every element whose
    tag does not end in ':t' — which spares w:t but NOT w:delText
    ('…xt'): a <w:delText xml:space="preserve"> </w:delText> (a deletion
    whose span crosses a whitespace-only run, e.g. COP-03E 2.5 'every 12
    ' -> '12-') would be emptied, so REJECTING the tracked change would
    restore 'every12 ' instead of 'every 12 '. The engine's part editors
    serialise compactly and untouched parts keep the source's own bytes,
    so there is no inter-tag whitespace to condense anyway (verified:
    only COP-03E-2026-1.1.docx of the first COP pass was affected; no
    GN/TR output carried an empty delText)."""
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(work_dir):
            for fn in sorted(files):
                fp = os.path.join(root, fn)
                zf.write(fp, os.path.relpath(fp, work_dir))


def rule_leftover_report(out, rules):
    """Post-pack rule check (user's standing requirement, 24 Nov 2026):
    accept every revision of the packed output, then count each rule's
    incorrect text in the FINAL text outside the revision-history table
    (historical rows keep old wording on purpose). Returns {inc: n} for
    the rules with occurrences remaining — {} means every rule replaced
    everything it should have."""
    counts = {}
    with zipfile.ZipFile(out) as zf:
        for n in story_parts_in_zip(zf):
            dom = minidom.parseString(zf.read(n))
            accept_all_revisions(dom)
            strip_comments(dom)
            rev_ids = revision_table_para_ids(dom)
            for p in dom.getElementsByTagName("w:p"):
                if id(p) in rev_ids:
                    continue
                txt = joined_text(p)
                if not txt:
                    continue
                for r in rules:
                    n_hit = 0
                    for lv in LEVELS:
                        ninc = r["_norms"][lv]
                        if not ninc:
                            continue
                        if lv == 0:
                            n_hit = max(n_hit, txt.count(ninc))
                        else:
                            N, _ = build_norm(txt, lv)
                            n_hit = max(n_hit, N.count(ninc))
                    if n_hit:
                        counts[r["inc"]] = counts.get(r["inc"], 0) + n_hit
    return counts


def redline_file(src, out, rows, work_dir, dry_run=False,
                 skill_dir=DEFAULT_SKILL_DIR, doc_id=None, bump=False,
                 accept_existing=True):
    print(f"\n=== {src}")
    with zipfile.ZipFile(src) as zf:
        src_track = "w:trackRevisions" in settings_of(zf)
        if dry_run:
            parts = [(n, _DomOnly(minidom.parseString(zf.read(n))))
                     for n in story_parts_in_zip(zf)]

    if not dry_run:
        shutil.rmtree(work_dir, ignore_errors=True)
        with zipfile.ZipFile(src) as zf:
            zf.extractall(work_dir)
        Document = _import_docx_api(skill_dir)
        doc = Document(work_dir, author=AUTHOR, initials=INITIALS,
                       track_revisions=True)
        parts = [(n, doc[n]) for n in story_parts(work_dir)]

    if accept_existing:
        by_author, marks = {}, 0
        for _name, ed in parts:
            for a, k in revision_authors(ed.dom).items():
                by_author[a] = by_author.get(a, 0) + k
            marks += accept_all_revisions(ed.dom)
        if by_author:
            who = ", ".join(f"{k} mark(s) by {a!r}"
                            for a, k in sorted(by_author.items()))
            print(f"  pre-existing revisions ACCEPTED into the base text "
                  f"({marks} mark(s) in total): {who}")
        else:
            print("  pre-existing revisions: none — nothing to accept")

    # previous reviewers' comments go outright — they are not tracked
    # changes and cannot ride along in a redline output
    n_anchors = 0
    for _name, ed in parts:
        n_anchors += strip_comments(ed.dom)
    if n_anchors:
        print(f"  pre-existing comments REMOVED: {n_anchors} anchor(s)")

    total, stats = process_parts(parts, rows,
                                 apply_fn=None if dry_run else apply_change)

    n_en = sum(1 for r in rows if r["src"] == "EN")
    print(f"  parts scanned: {len(parts)}; rows: {len(rows)} "
          f"(EN {n_en} / TC {len(rows) - n_en})")
    applied = [(r, s) for r, s in zip(rows, stats) if s["applied"]]
    already = [(r, s) for r, s in zip(rows, stats)
               if s["applied"] == 0 and s["hit"]]
    absent = [(r, s) for r, s in zip(rows, stats) if not s["hit"]]
    print(f"  applied: {total} change(s) from {len(applied)} row(s); "
          f"already correct: {len(already)} row(s); "
          f"not present: {len(absent)} row(s)")
    for r, s in already:
        print(f"    [already correct] {r['ref']} — {s['already']} "
              f"occurrence(s) left as-is")
    for r, _ in absent:
        print(f"    [not present] {r['ref']}  {r['inc'][:44]!r}")
    for r, s in zip(rows, stats):
        if r.get("kind") == "rule" and (s["applied"] or s["rev_skipped"]):
            print(f"    [rule] {r['inc']} -> {r['cor']}: "
                  f"{s['applied']} replaced, {s['already']} already "
                  f"correct, {s['rev_skipped']} kept in revision history")

    applied_rows = [dict(r, fires=s["applied"]) for r, s in
                    zip(rows, stats) if s["applied"]]
    n_hdr = 0
    if bump and total > 0:
        _, n_hdr = apply_frontmatter(parts, doc_id, applied_rows,
                                     dry_run=dry_run)

    if dry_run:
        print("  [dry-run] nothing written")
        return 0
    if total == 0:
        print("  no table findings matched this file — output not written")
        return 0
    doc.save()
    strip_update_prompts(work_dir, keep_track_revisions=src_track)
    gone = drop_comment_parts(work_dir)
    if gone:
        print("  comment payload parts removed: "
              + ", ".join(p.rsplit("/", 1)[-1] for p in gone))
    _pack_preserving(work_dir, out)

    rules = [r for r in rows if r.get("kind") == "rule"]
    if rules:
        bad = rule_leftover_report(out, rules)
        if bad:
            print(f"  [rule-check] WARNING — occurrences NOT replaced "
                  f"(outside revision history): {bad}")
        else:
            print("  [rule-check] PASS — every rule's incorrect text is "
                  "gone from the accepted final text (revision-history "
                  "rows excluded)")

    extra = (f" + front matter (revision row"
             f"{' + ' + str(n_hdr) + ' header edition bump(s)' if n_hdr else ''})"
             if bump else "")
    print(f"  -> {out}   ({total} tracked change(s){extra}, author "
          f"{AUTHOR!r}, no previous comments, trackRevisions "
          f"{'kept (source had it on)' if src_track else 'off (as source)'})")
    return 0


def default_output(src):
    d, base = os.path.split(os.path.abspath(src))
    stem = os.path.splitext(base)[0]
    if os.path.basename(d).lower() == "upload":
        d = "/home/z/my-project/download"
    return os.path.join(d, f"{stem}_redline.docx")


def src_ref_plan(src):
    """The reference-code plan pre-parsed from the SOURCE's own revision
    table — bumped_output's view of revision_row_plan's ref logic (same
    table, same code, computed before anything is applied). Returns
    {'ref': new_ref, 'old_ref': old} or None when the file has no usable
    4-column revision table."""
    try:
        with zipfile.ZipFile(src) as zf:
            dom = minidom.parseString(zf.read("word/document.xml"))
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    t = find_revision_table(dom)
    if t is None:
        return None
    trs = t.getElementsByTagName("w:tr")
    cells = row_cells(trs[-1])
    if len(cells) != 4 or not cells[0] or not cells[3]:
        return None
    try:
        bump_decimal(cells[0][0])
    except (InvalidOperation, ValueError):
        return None
    ref = cells[3][0].strip()
    today = date.today()

    def row_year(tr):
        cs = row_cells(tr)
        if len(cs) > 1 and cs[1]:
            return _date_year(cs[1][0])
        return None

    n_prior = sum(1 for tr in trs[1:] if row_year(tr) == today.year)
    return {"ref": year_aligned_ref(ref, today.year, n_prior),
            "old_ref": ref}


def bumped_output(src):
    """Version-bumped output name (user convention, 24 Nov 2026): the
    trailing edition number gets +1.0 — COP-01C-2026-1.0.docx ->
    COP-01C-2026-2.0.docx, GN-06-C-2026-1.2.docx -> GN-06-C-2026-2.2.docx,
    GN-01-C-2026-3.0.docx -> GN-01-C-2026-4.0.docx.

    Year-form stems — the trailing number is a YEAR, or a counter behind
    one — are never number-bumped (that would turn 2026 into 2027).
    Their suffix is derived from the NEW year-aligned reference code
    (src_ref_plan pre-parses the source's revision table):
      TR007C-2026.docx    (code TR-007:2026-1(C) ahead) -> TR007C-2026.1.docx
      TR009C-2025.docx    (code TR-009:2026(C))         -> TR009C-2026.docx
      TR003E-2024-1.docx  (code TR-003:2026(E))         -> TR003E-2026.docx
      GN-00-C-2026-1.docx (code GN-00:2026-2(C))        -> GN-00-C-2026-2.docx
    A counter appended to a bare-year stem uses the established dot
    form ('TR007C-2026.1'); a stem already carrying a dash counter keeps
    the dash ('GN-00-C-2026-2'). Returns None when the stem has no
    trailing number or no plan can be parsed (caller falls back to the
    default naming)."""
    d, base = os.path.split(os.path.abspath(src))
    stem = os.path.splitext(base)[0]
    m = re.search(r"(\d+(?:\.\d+)?)$", stem)
    if not m:
        return None
    if os.path.basename(d).lower() == "upload":
        d = "/home/z/my-project/download"
    my = re.search(r"(-)((?:19|20)\d{2})(-(\d+)(\.\d+)?)?$", stem)
    if my:
        head, year = stem[:my.start()], my.group(2)
        if my.group(5):                   # edition stem '-YYYY-N.M'
            try:
                ed = bump_decimal(my.group(4) + my.group(5))
            except (InvalidOperation, ValueError):
                return None
            return os.path.join(d, f"{head}-{year}-{ed}")
        plan = src_ref_plan(src)          # bare-year / dash-counter stem
        if plan is None:
            return None
        mc = re.search(r":\s*((?:19|20)\d{2})(?:-(\d+))?", plan["ref"])
        if mc is None:
            return None
        tail = f"-{mc.group(1)}"
        if mc.group(2):                   # in-year counter
            tail += (f"-{mc.group(2)}" if my.group(3)   # dash kept
                     else f".{mc.group(2)}")            # dot appended
        return os.path.join(d, head + tail)
    try:
        bumped = bump_decimal(m.group(1))
    except (InvalidOperation, ValueError):
        return None
    return os.path.join(d, f"{stem[:m.start(1)]}{bumped}.docx")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="mdacs_redline.py",
        description="Apply the MDACS typo tables (EN + Traditional Chinese) "
                    "as tracked changes. Table rows only — no re-verification, "
                    "no comments, author 'denis'.",
    )
    ap.add_argument("input", help="source .docx (any name)")
    ap.add_argument("-o", "--output", help="output .docx "
                    "(default <stem>_redline.docx; upload/ -> download/)")
    ap.add_argument("--doc", help="pin the document id, e.g. TR-007 "
                    "(default: detected from the file name)")
    ap.add_argument("--all", action="store_true",
                    help="try every document's rows (context-dependent rows "
                    "excluded)")
    ap.add_argument("--keep-existing", action="store_true",
                    help="leave pre-existing tracked changes (other "
                    "authors) pending instead of accepting them into the "
                    "base text first (default: accept, then redline)")
    ap.add_argument("--bump", action="store_true",
                    help="edition bump: output named +1.0 "
                    "(GN-00-C-2026-1.docx -> GN-00-C-2026-2.docx; "
                    "GN-01-C-2026-3.0.docx -> GN-01-C-2026-4.0.docx), a "
                    "tracked row appended to the revision-history table "
                    "with ONE merged summary line (更正了第X、Y及Z節的"
                    "拼寫錯誤 / Typos in clauses X, Y and Z are fixed; "
                    "appendix targets join the same line) and the "
                    "YEAR-ALIGNED reference code (12 Nov 2026): the code's year is "
                    "this update's year and the counter counts that year's updates "
                    "- first 'TR-003:2026(C)', second 'TR-007:2026-1(C)', third "
                    "'GN-00:2026-2(C)'; '(Ed. X.Y)' codes keep their own "
                    "convention ('(Ed. 3.0)' -> '(Ed. 4.0)'). Headers carrying the "
                    "current code are bumped to it, year-form header codes get "
                    "their year refreshed; stale codes left alone")
    ap.add_argument("--dry-run", action="store_true",
                    help="report planned changes, write nothing")
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                    help="directory holding typo_data.py / typo_data_cn.py")
    ap.add_argument("--skill-dir", default=DEFAULT_SKILL_DIR)
    ap.add_argument("--work-dir", help="scratch directory (default "
                    "work_redline/<stem>)")
    args = ap.parse_args(argv)

    rows = load_rows(args.data_dir)
    doc_ids = sorted({r["doc"] for r in rows} - {"*"})
    if args.doc:
        doc_id, scan = canonical_doc_id(args.doc, doc_ids), False
    elif args.all:
        doc_id, scan = None, True
    else:
        doc_id = detect_doc_id(args.input, doc_ids)
        scan = doc_id is None
        if scan:
            print("NOTE: document id not recognised from the file name — "
                  "using scan mode (all rows except context-dependent ones). "
                  "Pin it with e.g. --doc TR-007 if that is wrong.")
    sel = select_rows(rows, doc_id, scan, lang=detect_language(args.input))

    if scan:
        print(f"document: <scan mode> — {len(sel)} candidate row(s)")
    else:
        n_en = sum(1 for r in sel if r["src"] == "EN")
        print(f"document: {doc_id} — {len(sel)} row(s) "
              f"(EN {n_en} / TC {len(sel) - n_en})")
    print(f"language: {detect_language(args.input) or 'unknown'} — "
          f"rows of the other language's table are not selected")

    if args.output:
        out = args.output
    elif args.bump:
        out = bumped_output(args.input) or default_output(args.input)
        if not args.dry_run and out == default_output(args.input):
            print("NOTE: no trailing edition number / usable revision-"
                  "table plan to bump from — using default output naming")
    else:
        out = default_output(args.input)
    work = args.work_dir or os.path.join(
        DEFAULT_WORK_ROOT,
        os.path.splitext(os.path.basename(args.input))[0])
    if not args.dry_run:
        print(f"output: {out}")
    return redline_file(args.input, out, sel, work,
                        dry_run=args.dry_run, skill_dir=args.skill_dir,
                        doc_id=doc_id, bump=args.bump,
                        accept_existing=not args.keep_existing)


if __name__ == "__main__":
    sys.exit(main())
