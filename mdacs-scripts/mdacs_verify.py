#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify an mdacs_redline.py output against its source and the tables.

usage: python mdacs_verify.py SOURCE.docx REDLINE.docx [--doc ID] [--all]
                [--bump] [--keep-existing]

Default mode (matches the engine default): the engine ACCEPTED every
pre-existing tracked change into the base text before redlining, so the
baselines below are the ACCEPTED source. --keep-existing switches to the
old semantics (pre-existing revisions left pending).

Per story part (document + headers/footers/footnotes/endnotes):
  1. REJECT-all simulation == the accepted base text (every revision
     ours; rejecting them restores the accepted base); with --bump the
     inserted revision-history row contributes only empty paragraphs
  2. ACCEPT-all simulation == accepted base text with the tables' minimal
     diffs (recomputed independently) +, with --bump, the inserted row's
     texts and the header/footer edition-reference bumps
  3. paragraph counts (+ the inserted row's paragraphs under --bump)
  4. w:br count preserved; comment anchors REMOVED (all previous
     reviewers' comments go — anchors out of every story part)
Global:
  5. w:ins / w:del added == expected from the tables (+ front matter:
     1 w:trPr row mark + 2 per inserted paragraph + 1 per header bump)
  6. revision authors: default ⊆ {'denis'} (pre-existing accepted away);
     --keep-existing: ⊆ source authors ∪ {'denis'}
  7. no comments in the output at all: zero anchors, no comments.xml
     payload part (12 Nov 2026 — the redline output carries only the
     typo tracked changes, not the reviewers' comment threads)
  8. settings: no w:updateFields; w:trackRevisions mirrors the source

Exit code 0 = all checks passed.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile

from defusedxml import minidom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdacs_redline as mr  # noqa: E402

AUTHOR = mr.AUTHOR
failures = 0


def _text_of(node):
    return "".join(c.nodeValue or "" for c in node.childNodes
                   if c.nodeType == c.TEXT_NODE)


def _inside(node, tag):
    a = node.parentNode
    while a is not None and a.nodeType == a.ELEMENT_NODE:
        if a.tagName == tag:
            return True
        a = a.parentNode
    return False


def para_text(p, mode):
    """Paragraph text. mode 'plain' = accept view (w:t wherever it is —
    deletions carry w:delText instead); 'reject' drops w:t inside w:ins
    and restores w:delText."""
    parts = []
    for node in p.getElementsByTagName("*"):
        t = node.tagName
        if t == "w:t":
            if mode == "reject" and _inside(node, "w:ins"):
                continue
            parts.append(_text_of(node))
        elif t == "w:delText" and mode == "reject":
            parts.append(_text_of(node))
    return "".join(parts)


def check(ok, msg):
    global failures
    print(f"  [{'OK' if ok else 'FAIL'}] {msg}")
    if not ok:
        failures += 1


def count(dom, tag):
    return len(dom.getElementsByTagName(tag))


def leaf_paras(dom):
    """Paragraphs whose text is their own — textbox-aggregation paragraphs
    (w:txbxContent descendants) are excluded: their text merely mirrors
    the nested textbox paragraphs, which are listed themselves."""
    return [p for p in dom.getElementsByTagName("w:p")
            if not p.getElementsByTagName("w:txbxContent")]


def _first_diff(list_a, list_b, label_a, label_b):
    for i, (a, b) in enumerate(zip(list_a, list_b)):
        if a != b:
            print(f"    para {i}:\n      {label_a}: {a[:70]!r}\n"
                  f"      {label_b}: {b[:70]!r}")
            return
    if len(list_a) != len(list_b):
        print(f"    length differs: {len(list_a)} vs {len(list_b)}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="mdacs_verify.py",
        description="Verify a redline docx against its source and the "
                    "MDACS typo tables.")
    ap.add_argument("source")
    ap.add_argument("redline")
    ap.add_argument("--doc", help="pin the document id (default: from the "
                    "file name)")
    ap.add_argument("--all", action="store_true", help="scan mode")
    ap.add_argument("--bump", action="store_true",
                    help="expect the edition-bump front matter (tracked "
                         "revision-history row + header edition bumps)")
    ap.add_argument("--keep-existing", action="store_true",
                    help="old semantics: pre-existing revisions were left "
                         "pending (default: they were accepted into the "
                         "base text before redlining)")
    ap.add_argument("--today", metavar="YYYY-MM-DD",
                    help="the date the redline's revision-history row was "
                         "made (default: today — re-verifying an older "
                         "output needs the date it was produced, e.g. "
                         "--today 2026-11-09 for the 9 Nov 2026 batch)")
    ap.add_argument("--data-dir", default=mr.DEFAULT_DATA_DIR)
    args = ap.parse_args(argv)
    made = None
    if args.today:
        from datetime import datetime as _dt
        made = _dt.strptime(args.today, "%Y-%m-%d").date()

    rows = mr.load_rows(args.data_dir)
    doc_ids = sorted({r["doc"] for r in rows} - {"*"})
    if args.doc:
        doc_id, scan = mr.canonical_doc_id(args.doc, doc_ids), False
    elif args.all:
        doc_id, scan = None, True
    else:
        doc_id = (mr.detect_doc_id(args.source, doc_ids)
                  or mr.detect_doc_id(args.redline, doc_ids))
        scan = doc_id is None
        if scan:
            print("NOTE: doc id unknown — verifying in scan mode")
    lang = mr.detect_language(args.source)
    sel = mr.select_rows(rows, doc_id, scan, lang=lang)
    mode = "keep-existing" if args.keep_existing else "accept-existing"
    print(f"verifying: {args.redline}")
    print(f"document: {'scan mode' if scan else doc_id} — {len(sel)} row(s)"
          f"{' + edition bump' if args.bump else ''} — {mode} mode"
          + (f", language {lang}" if lang else ""))

    exp_ins = exp_del = 0
    with zipfile.ZipFile(args.source) as zs, \
            zipfile.ZipFile(args.redline) as zo:
        parts = sorted(set(mr.story_parts_in_zip(zs))
                       | set(mr.story_parts_in_zip(zo)),
                       key=lambda p: (p != "word/document.xml", p))

        # ---- PASS 1: expectations recomputed from the SOURCE ----
        # (accept-existing mode: from the source AFTER accepting its own
        # pre-existing revisions — exactly the engine's base text)
        # expected[part] is indexed by LEAF paragraph order (textbox-
        # aggregation paragraphs excluded, exactly as the engine does)
        expected, fired, fires = {}, set(), {}
        for part in parts:
            sdom = minidom.parseString(zs.read(part))
            if not args.keep_existing:
                mr.accept_all_revisions(sdom)
            texts = []
            for p in leaf_paras(sdom):
                view = mr.ParaView(p)
                jobs = []
                if view.text:
                    for ri, row in enumerate(sel):
                        _, specs, _ = mr.plan_specs(row, view)
                        for s, e, span, repl in specs:
                            jobs.append((s, e, span, repl, ri))
                kept, _dropped = mr.resolve_jobs(jobs)
                out = view.text
                for s, e, span, repl, ri in kept:      # right-to-left
                    if mr.foreign_conflict(p, s, e):
                        continue          # engine skips these too
                    out = out[:s] + repl + out[e:]
                    if repl:
                        exp_ins += 1
                    if span:
                        exp_del += 1
                    fired.add(ri)
                    fires[ri] = fires.get(ri, 0) + 1
                texts.append(out)
            expected[part] = texts

        # ---- front-matter expectations (edition bump) ----
        fm = K = fm_pos = None
        if args.bump and fired and "word/document.xml" in \
                set(mr.story_parts_in_zip(zs)):
            sdoc = minidom.parseString(zs.read("word/document.xml"))
            if not args.keep_existing:
                mr.accept_all_revisions(sdoc)
            fm = mr.revision_row_plan(
                sdoc, [dict(sel[i], fires=fires[i]) for i in sorted(fires)],
                today=made)
            if fm:
                # the inserted row's position, in leaf coordinates
                t = mr.find_revision_table(sdoc)
                last_p = t.getElementsByTagName("w:tr")[-1] \
                    .getElementsByTagName("w:p")[-1]
                for i, p in enumerate(leaf_paras(sdoc)):
                    if p is last_p:
                        fm_pos = i + 1
                        break
                cell_texts = [tx for cell in fm["cells"] for tx in cell]
                K = len(cell_texts)
                expected["word/document.xml"][fm_pos:fm_pos] = \
                    cell_texts
                exp_ins += 1 + 2 * K        # trPr mark + run wrapper + para mark
                for part in parts:
                    if not mr.HEADER_RE.match(part):
                        continue
                    sdom_h = minidom.parseString(zs.read(part))
                    if not args.keep_existing:
                        mr.accept_all_revisions(sdom_h)   # engine's base
                    for pi, hp in enumerate(leaf_paras(sdom_h)):
                        txt = expected[part][pi]
                        jobs = mr.ref_bump_edits_in_text(
                            txt, fm["doc_prefix"],
                            only_ref=fm.get("old_ref"),
                            bump_year=fm.get("ref_year"),
                            bump_prior=fm.get("ref_prior"),
                            base_ref=fm.get("base_ref"))
                        jobs.sort(key=lambda j: (-j[0], -j[1]))
                        for s, e, span, repl in jobs:
                            if mr.foreign_conflict(hp, s, e):
                                continue    # engine skips these too
                            txt = txt[:s] + repl + txt[e:]
                            if repl:
                                exp_ins += 1
                            if span:
                                exp_del += 1
                        expected[part][pi] = txt

        # ---- PASS 2: compare the OUTPUT ----
        ins_s = ins_o = del_s = del_o = 0
        for part in parts:
            src_dom = minidom.parseString(zs.read(part))
            if not args.keep_existing:
                mr.accept_all_revisions(src_dom)
            out_dom = minidom.parseString(zo.read(part))
            src_xml = zs.read(part).decode("utf-8")
            out_xml = zo.read(part).decode("utf-8")
            print(f"\n-- {part}")

            src_paras = list(src_dom.getElementsByTagName("w:p"))
            out_paras = list(out_dom.getElementsByTagName("w:p"))
            src_leaf = leaf_paras(src_dom)
            out_leaf = leaf_paras(out_dom)
            k = K if (part == "word/document.xml" and fm) else 0
            check(len(src_paras) + k == len(out_paras),
                  f"paragraph count {len(src_paras)}+{k} -> {len(out_paras)}")

            # 1. reject-all round-trip: every revision in the output is
            #    ours, so rejecting them restores the base text — in
            #    accept-existing mode that base is the ACCEPTED source
            #    (accept view == reject view there); in --keep-existing
            #    mode it is the source's own reject view
            src_txt = [para_text(p, "reject") for p in src_leaf]
            if k:
                src_txt = src_txt[:fm_pos] + [""] * k + src_txt[fm_pos:]
            rej_txt = [para_text(p, "reject") for p in out_leaf]
            ok = rej_txt == src_txt
            check(ok, "REJECT-all round-trip == source reject view")
            if not ok:
                _first_diff(rej_txt, src_txt, "reject", "source")

            # 2. accept-all == recomputed expectation (leaf paragraphs)
            acc_txt = [para_text(p, "plain") for p in out_leaf]
            exp_leaf = expected[part]
            ok = acc_txt == exp_leaf
            check(ok, f"ACCEPT-all text == expectation "
                      f"({len(out_leaf)} leaf paragraph(s))")
            if not ok:
                _first_diff(acc_txt, exp_leaf, "got", "expected")

            # 3-5. structure
            check(count(src_dom, "w:br") == count(out_dom, "w:br"),
                  f"w:br {count(src_dom, 'w:br')} -> "
                  f"{count(out_dom, 'w:br')}")
            n_crs_s = len(re.findall(r"<w:commentRangeStart", src_xml))
            n_crs_o = len(re.findall(r"<w:commentRangeStart", out_xml))
            check(n_crs_o == 0,
                  f"comment anchors removed {n_crs_s} -> {n_crs_o}")
            # revision counts: baseline = the ACCEPTED source (raw source
            # under --keep-existing — src_dom is then the untouched parse)
            acc_xml = src_dom.toxml()
            ins_s += len(re.findall(r"<w:ins[ >]", acc_xml))
            ins_o += len(re.findall(r"<w:ins[ >]", out_xml))
            del_s += len(re.findall(r"<w:del[ >]", acc_xml))
            del_o += len(re.findall(r"<w:del[ >]", out_xml))
            a_s = set(re.findall(r'<w:(?:ins|del) [^>]*w:author="([^"]*)"',
                                 src_xml))
            a_o = set(re.findall(r'<w:(?:ins|del) [^>]*w:author="([^"]*)"',
                                 out_xml))
            allowed = (a_s | {AUTHOR}) if args.keep_existing else {AUTHOR}
            check(a_o <= allowed,
                  f"revision authors {a_o or '{}'} ⊆ "
                  f"{'source ' + str(a_s or '{}') + ' ∪ ' if args.keep_existing else ''}"
                  f"{{'{AUTHOR}'}}")

        # 5. revision counts
        check(ins_o - ins_s == exp_ins,
              f"w:ins added {ins_o - ins_s} == expected {exp_ins}")
        check(del_o - del_s == exp_del,
              f"w:del added {del_o - del_s} == expected {exp_del}")

        # 7. comments: none survive into the redline output
        def comment_count(zf):
            try:
                c = zf.read("word/comments.xml").decode("utf-8")
            except KeyError:
                return 0
            return len(re.findall(r"<w:comment[ >]", c))
        cs, co = comment_count(zs), comment_count(zo)
        check(co == 0, f"comments {cs} -> {co} (all previous removed)")
        try:
            ctext = zo.read("word/comments.xml").decode("utf-8")
            ours = len(re.findall(
                rf'<w:comment [^>]*w:author="{AUTHOR}"', ctext))
        except KeyError:
            ours = 0
        check(ours == 0, f"comments by {AUTHOR!r}: {ours}")

        # 8. settings
        s_s, s_o = mr.settings_of(zs), mr.settings_of(zo)
        check("w:updateFields" not in s_o,
              "no w:updateFields (no update-fields dialog on open)")
        check(("w:trackRevisions" in s_s) == ("w:trackRevisions" in s_o),
              f"trackRevisions mirrors source "
              f"({'w:trackRevisions' in s_o})")
        check("w:revisionView" not in s_o,
              "no w:revisionView (markup never hidden on open)")

    print(f"\n{'ALL CHECKS PASSED' if failures == 0 else f'{failures} FAILURES'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
