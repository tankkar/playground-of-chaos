#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic verifier for mdacs_redline.py outputs (EN or Traditional Chinese).

Usage:  python batch_verify.py SOURCE.docx REDLINE.docx [--doc ID]

Checks (all must pass):
  1. authors  — every w:ins / w:del in the output is authored 'denis'
                (when the source itself has no revisions, the usual case)
  2. comments — output contains no comments.xml and no comment ranges
  3. settings— no w:updateFields (no update-fields dialog on open);
                w:trackRevisions kept only if the source had it
  4. reject  — Reject-all simulation: per story part, the text with all
                w:ins dropped and all w:delText restored equals the SOURCE
                text exactly — nothing but the tracked edits was touched
  5. accept  — Accept-all simulation equals the expected text computed
                independently from the typo tables on the source
  6. counts  — the number of new w:del / w:ins elements matches the plan
  7. w:br / w:tab — line breaks and tabs inside runs survive

Exit code 0 = all green, 1 = any failure.
"""
import argparse
import os
import sys
import zipfile

from defusedxml import minidom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdacs_redline import (  # noqa: E402
    ParaView, plan_specs, resolve_jobs, load_rows, detect_doc_id,
    select_rows, story_parts_in_zip,
)

AUTHOR = "denis"


def node_text(t):
    return "".join(c.nodeValue or "" for c in t.childNodes
                   if c.nodeType == c.TEXT_NODE)


def inside(node, tag):
    anc = node.parentNode
    while anc is not None and anc.nodeType == anc.ELEMENT_NODE:
        if anc.tagName == tag:
            return True
        anc = anc.parentNode
    return False


def para_text(p, mode):
    """Paragraph text: mode 'plain' (w:t only — accept view), 'reject'
    (w:t outside w:ins + w:delText)."""
    parts = []
    for node in p.getElementsByTagName("*"):
        tag = node.tagName
        if tag == "w:t":
            if mode == "reject" and inside(node, "w:ins"):
                continue
            parts.append(node_text(node))
        elif tag == "w:delText" and mode == "reject":
            parts.append(node_text(node))
    return "".join(parts)


def part_texts(zf, name, mode):
    dom = minidom.parseString(zf.read(name))
    return [para_text(p, mode) for p in dom.getElementsByTagName("w:p")]


def part_counts(zf, name):
    dom = minidom.parseString(zf.read(name))
    out = {}
    for tag in ("w:del", "w:ins", "w:br", "w:tab",
                "w:commentRangeStart", "w:commentReference"):
        out[tag] = len(dom.getElementsByTagName(tag))
    authors = {e.getAttribute("w:author")
               for tag in ("w:ins", "w:del")
               for e in dom.getElementsByTagName(tag)}
    return out, authors


def expected_accept(src_zf, rows):
    """Independent text-level simulation: the tables applied to the source.

    Returns {part_name: [expected accept text per paragraph]}, plus the
    planned (del, ins) element counts.
    """
    exp, n_del, n_ins = {}, 0, 0
    for name in story_parts_in_zip(src_zf):
        dom = minidom.parseString(src_zf.read(name))
        texts = []
        for p in dom.getElementsByTagName("w:p"):
            view = ParaView(p)
            jobs = []
            if view.text:
                for row in rows:
                    _, specs, _ = plan_specs(row, view)
                    jobs.extend(specs)
            kept, _ = resolve_jobs(jobs)
            out = view.text
            for s, e, span, repl in kept:      # kept is right-to-left
                out = out[:s] + repl + out[e:]
                n_del += bool(span)
                n_ins += bool(repl)
            texts.append(out)
        exp[name] = texts
    return exp, n_del, n_ins


def main(argv=None):
    ap = argparse.ArgumentParser(prog="batch_verify.py")
    ap.add_argument("source")
    ap.add_argument("redline")
    ap.add_argument("--doc", help="document id (default: from file name)")
    ap.add_argument("--data-dir", default=os.path.dirname(
        os.path.abspath(__file__)))
    args = ap.parse_args(argv)

    rows = load_rows(args.data_dir)
    doc_ids = sorted({r["doc"] for r in rows})
    doc_id = (args.doc and doc_ids and
              next((d for d in doc_ids
                    if d.replace("-", "") == args.doc.replace("-", "")),
                   None)) or detect_doc_id(args.source, doc_ids)
    if doc_id is None:
        raise SystemExit("ABORT: document id unknown — pass --doc ID")
    sel = select_rows(rows, doc_id, scan=False)
    print(f"verifying doc {doc_id} against {len(sel)} table row(s)")

    fails = []
    with zipfile.ZipFile(args.source) as src, \
            zipfile.ZipFile(args.redline) as out:

        # ---- part inventory ----
        src_parts = set(story_parts_in_zip(src))
        out_parts = set(story_parts_in_zip(out))
        if src_parts != out_parts:
            fails.append(f"story parts differ: +{out_parts - src_parts} "
                         f"-{src_parts - out_parts}")
        print(f"[{'FAIL' if src_parts != out_parts else 'OK'}] "
              f"story parts identical ({len(src_parts)})")

        # ---- 2. comments (no NEW ones; pre-existing MDD comments stay) ----
        names = set(out.namelist())
        src_names = set(src.namelist())

        def comment_state(zf, partnames):
            n_range = n_ref = n_comm = 0
            for n in partnames:
                c, _ = part_counts(zf, n)
                n_range += c["w:commentRangeStart"]
                n_ref += c["w:commentReference"]
            if "word/comments.xml" in zf.namelist():
                cdom = minidom.parseString(zf.read("word/comments.xml"))
                n_comm = len(cdom.getElementsByTagName("w:comment"))
            return n_range, n_ref, n_comm

        s_r, s_f, s_c = comment_state(src, src_parts)
        o_r, o_f, o_c = comment_state(out, out_parts)
        ok = (o_r <= s_r and o_f <= s_f and o_c <= s_c and
              ("word/comments.xml" in names) ==
              ("word/comments.xml" in src_names or o_c > 0))
        if not ok:
            fails.append(f"comments changed: source (ranges {s_r}, refs "
                         f"{s_f}, comments {s_c}) -> output (ranges {o_r}, "
                         f"refs {o_f}, comments {o_c})")
        print(f"[{'FAIL' if not ok else 'OK'}] no new comments "
              f"(source had {s_c} comment(s), {s_r} range(s) — preserved)")

        # ---- 3. settings ----
        sset = src.read("word/settings.xml").decode("utf-8") \
            if "word/settings.xml" in names else ""
        oset = out.read("word/settings.xml").decode("utf-8") \
            if "word/settings.xml" in names else ""
        upd = "w:updateFields" in oset
        tr_ok = ("w:trackRevisions" in oset) == ("w:trackRevisions" in sset)
        if upd:
            fails.append("w:updateFields present in output")
        if not tr_ok:
            fails.append("w:trackRevisions parity broken")
        print(f"[{'FAIL' if upd else 'OK'}] no w:updateFields")
        print(f"[{'FAIL' if not tr_ok else 'OK'}] w:trackRevisions parity "
              f"(source {'on' if 'w:trackRevisions' in sset else 'off'})")

        # ---- 1. authors ----
        out_authors, src_authors = set(), set()
        for n in out_parts:
            out_authors |= part_counts(out, n)[1]
        for n in src_parts:
            src_authors |= part_counts(src, n)[1]
        if src_authors - {""}:
            print(f"[note] source already carries revisions by "
                  f"{sorted(src_authors)} — checking only new ones")
            ok = AUTHOR in out_authors
        else:
            ok = out_authors == {AUTHOR}
        if not ok:
            fails.append(f"revision authors {sorted(out_authors)} != "
                         f"{{{AUTHOR!r}}}")
        print(f"[{'FAIL' if not ok else 'OK'}] revision authors "
              f"{sorted(out_authors) or '(none)'}")

        # ---- 4. reject-all == source ----
        for n in sorted(src_parts & out_parts):
            rej = part_texts(out, n, "reject")
            srctxt = part_texts(src, n, "plain")
            if rej != srctxt:
                fails.append(f"reject-all != source in {n}")
                for i, (a, b) in enumerate(zip(rej, srctxt)):
                    if a != b:
                        fails.append(f"  para {i}: {a!r} vs {b!r}")
                        break
        print(f"[{'FAIL' if any('reject-all' in f for f in fails) else 'OK'}]"
              f" reject-all restores the source text "
              f"({len(src_parts & out_parts)} part(s))")

        # ---- 5/6. accept-all == table plan + revision counts ----
        exp, n_del, n_ins = expected_accept(src, sel)
        acc_ok, cnt_ok, br_ok = True, True, True
        d_del = d_ins = d_br = 0
        for n in sorted(src_parts & out_parts):
            acc = part_texts(out, n, "plain")
            if acc != exp[n]:
                acc_ok = False
                for i, (a, b) in enumerate(zip(acc, exp[n])):
                    if a != b:
                        fails.append(f"accept-all != expected in {n} para {i}:\n"
                                     f"    got      {a!r}\n"
                                     f"    expected {b!r}")
                        break
            oc, _ = part_counts(out, n)
            sc, _ = part_counts(src, n)
            d_del += oc["w:del"] - sc["w:del"]
            d_ins += oc["w:ins"] - sc["w:ins"]
            d_br += oc["w:br"] - sc["w:br"] + oc["w:tab"] - sc["w:tab"]
        if d_del != n_del or d_ins != n_ins:
            cnt_ok = False
            fails.append(f"revision counts: del {d_del} (plan {n_del}), "
                         f"ins {d_ins} (plan {n_ins})")
        if d_br != 0:
            br_ok = False
            fails.append("w:br / w:tab count changed")
        print(f"[{'FAIL' if not acc_ok else 'OK'}] accept-all == table "
              f"expectation")
        print(f"[{'FAIL' if not cnt_ok else 'OK'}] revision counts: "
              f"{d_del} w:del + {d_ins} w:ins (plan: {n_del} + {n_ins})")
        print(f"[{'FAIL' if not br_ok else 'OK'}] w:br / w:tab preserved")

    if fails:
        print("\nFAILURES:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"\nALL GREEN — {args.redline}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
