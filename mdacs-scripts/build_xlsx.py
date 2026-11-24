# -*- coding: utf-8 -*-
"""Build MDACS_Typo_Check_Summary.xlsx
Sheet 1 "Typos": 4-column typo summary table (Reference | Incorrect text | Proposed correct text | Remark)
Sheet 2 "Suspected extraction artifacts": artifact list for manual verification
Includes a pre-build verification step: every INCORRECT quote must be found in the
source text (whitespace-flexible, within the document's line range)."""
import sys, os, re, json, math

XLSX_SKILL_DIR = "/home/z/my-project/skills/xlsx"
for sub in [XLSX_SKILL_DIR, os.path.join(XLSX_SKILL_DIR, "templates")]:
    if sub not in sys.path:
        sys.path.insert(0, sub)
sys.path.insert(0, "/home/z/my-project/scripts")

from base import (setup_sheet, style_header_row, style_data_row, font_caption,
                  FONT_NAME, NEUTRAL_600, PRIMARY)
from typo_data import TYPOS
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

SRC = "/home/z/my-project/upload/merged_documents.txt"
OUT = "/home/z/my-project/download/MDACS_Typo_Check_Summary.xlsx"
ART = "/home/z/my-project/scripts/artifacts.json"

DOC_RANGE = {
    "COP-01": (4, 439), "COP-02": (440, 766), "COP-03": (767, 1123),
    "COP-04": (1124, 1490), "COP-05": (1491, 1874), "ExpSch": (1875, 1940),
    "GN-00": (1941, 2566), "GN-01": (2567, 3537), "GN-02": (3538, 4569),
    "GN-03": (4570, 6096), "GN-04": (6097, 6553), "GN-06": (6554, 7464),
    "GN-07": (7465, 8565), "GN-08": (8566, 9063), "GN-09": (9064, 10279),
    "GN-10": (10280, 11727), "TR-001": (11728, 12378), "TR-002": (12379, 12892),
    "TR-003": (12893, 13698), "TR-004": (13699, 14507), "TR-005": (14508, 14838),
    "TR-006": (14839, 15375), "TR-007": (15376, 16538), "TR-008": (16539, 17248),
    "TR-009": (17249, 17639), "TR-010": (17640, 18067),
}
DOC_ORDER = ["COP-01", "COP-02", "COP-03", "COP-04", "COP-05", "ExpSch", "GN-00",
             "GN-01", "GN-02", "GN-03", "GN-04", "GN-06", "GN-07", "GN-08",
             "GN-09", "GN-10", "TR-001", "TR-002", "TR-003", "TR-004", "TR-005",
             "TR-006", "TR-007", "TR-008", "TR-009", "TR-010"]

# ---------------- 1. verification ----------------
with open(SRC, encoding="utf-8") as f:
    lines = f.readlines()

def flexible_pattern(quote):
    chars = [c for c in quote if not c.isspace()]
    return re.compile(r"\s*".join(re.escape(c) for c in chars))

def doc_text(doc):
    a, b = DOC_RANGE[doc]
    return "".join(lines[a - 1:b])

def verify():
    problems = []
    for idx, (ref, inc, cor, rem) in enumerate(TYPOS, 1):
        doc = ref.split()[0]
        if doc not in DOC_RANGE:
            problems.append(f"Row {idx}: unknown doc '{doc}' in reference '{ref}'")
            continue
        text = doc_text(doc)
        frags = [x.strip() for x in inc.split(";") if x.strip()]
        for frag in frags:
            if not flexible_pattern(frag).search(text):
                problems.append(f"Row {idx} [{ref}]: NOT FOUND -> '{frag}'")
    return problems

probs = verify()
print(f"Verification: {len(TYPOS)} rows checked, {len(probs)} problems")
for p in probs:
    print("  !!", p)
if probs:
    print("ABORT: fix quotes before building.")
    sys.exit(1)

# ---------------- 2. build workbook ----------------
wb = Workbook()

def est_height(values, widths, base=15, minh=22, maxh=118):
    n = 1
    for v, w in zip(values, widths):
        v = str(v or "")
        n = max(n, math.ceil(len(v) / max(1, w - 2)))
    return min(maxh, max(minh, n * base + 7))

# ===== Sheet 1: Typos =====
ws = wb.active
ws.title = "Typos"
HEADERS1 = ["Reference", "Incorrect text", "Proposed correct text", "Remark"]
LAST1 = 1 + len(HEADERS1)  # B..E -> 5
setup_sheet(ws, title="Typo Summary — MDACS Document Set (COP / GN / TR)", last_col=LAST1)
for c, h in enumerate(HEADERS1, start=2):
    ws.cell(row=4, column=c, value=h)
style_header_row(ws, row_num=4, col_start=2, col_end=LAST1)

W1 = [30, 42, 42, 58]
for c, w in enumerate(W1, start=2):
    ws.column_dimensions[get_column_letter(c)].width = w

r = 5
for i, (ref, inc, cor, rem) in enumerate(TYPOS):
    vals = [ref, inc, cor, rem]
    for c, v in enumerate(vals, start=2):
        ws.cell(row=r, column=c, value=v)
    style_data_row(ws, row_num=r, col_start=2, col_end=LAST1, row_index=i)
    for c in range(2, LAST1 + 1):
        ws.cell(row=r, column=c).alignment = Alignment(
            horizontal="left", vertical="top", wrap_text=True)
    ws.row_dimensions[r].height = est_height(vals, W1)
    r += 1
last_data1 = r - 1

note_r = last_data1 + 2
notes1 = [
    "Scope: word-level typos only — misspellings, wrong words, missing/extra words and punctuation slips. Grammar, style, TOC/clause-numbering and superseded-reference observations were excluded per review feedback.",
    "Source: merged_documents.txt (25 MDACS documents: COP-01–05, GN-00–10, TR-001–010). Quotes are normalised: spurious spaces inserted by text extraction are re-joined.",
    "Verification (6 Nov 2026): every finding was re-checked against the official PDFs downloaded from the MDD website (www.mdd.gov.hk → Information & Publications → Code of Practice). All 71 errors are present verbatim in the current official files; names were confirmed against the MDD document list and HK e-Legislation (Cap. 231).",
]
import textwrap as _tw
for k, n in enumerate(notes1):
    for j, chunk in enumerate(_tw.wrap(n, width=120)):
        rr = note_r + k * 4 + j
        cell = ws.cell(row=rr, column=2, value=chunk)
        cell.font = font_caption()
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=False)
        ws.row_dimensions[rr].height = 14
ws.freeze_panes = "B5"
ws.page_setup.orientation = "landscape"
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0
ws.print_title_rows = "4:4"

# ===== Sheet 2: Suspected extraction artifacts =====
with open(ART, encoding="utf-8") as f:
    art = json.load(f)

rows2 = []
for a in art["A"]:
    rows2.append((a["doc"], a["line"], "Word split by space", a["text"], a["snippet"][:80]))
for b in art["B"]:
    rows2.append((b["doc"], b["line"], "Hyphen split", b["text"], b["snippet"][:80]))
rows2.sort(key=lambda x: (DOC_ORDER.index(x[0]) if x[0] in DOC_ORDER else 99, x[1]))

ws2 = wb.create_sheet("Suspected extraction artifacts")
HEADERS2 = ["Document", "Line in merged file", "Artifact type", "Text as extracted", "Context"]
LAST2 = 1 + len(HEADERS2)  # B..F -> 6
setup_sheet(ws2, title="Suspected Text-Extraction Artifacts — Verify in Original Files", last_col=LAST2)
for c, h in enumerate(HEADERS2, start=2):
    ws2.cell(row=4, column=c, value=h)
style_header_row(ws2, row_num=4, col_start=2, col_end=LAST2)

W2 = [14, 10, 20, 24, 64]
for c, w in enumerate(W2, start=2):
    ws2.column_dimensions[get_column_letter(c)].width = w

r = 5
for i, (doc, ln, typ, txt, ctx) in enumerate(rows2):
    vals = [doc, ln, typ, txt, ctx]
    for c, v in enumerate(vals, start=2):
        ws2.cell(row=r, column=c, value=v)
    style_data_row(ws2, row_num=r, col_start=2, col_end=LAST2, row_index=i)
    for c in range(2, LAST2 + 1):
        ws2.cell(row=r, column=c).alignment = Alignment(
            horizontal="left", vertical="top", wrap_text=True)
    ws2.cell(row=r, column=3).alignment = Alignment(
        horizontal="center", vertical="top")
    ws2.row_dimensions[r].height = est_height(vals, W2, minh=18)
    r += 1
last_data2 = r - 1

cnts = art["summary"]["C_punct_space_docs"]
cnt_str = ", ".join(f"{d} {n}" for d, n in cnts.items())
note_r2 = last_data2 + 2
notes2 = [
    "These entries are suspected artifacts of the .docx-to-text conversion (spurious spaces inside words and around hyphens). They are probably NOT typos in the original Word documents — verify against the original files before changing anything.",
    f"In addition, {art['summary']['C_total']} occurrences of spurious spaces next to punctuation (e.g. \"stocks .\", \"( Global ACI )\") were detected. Per-document counts: {cnt_str}.",
]
for k, n in enumerate(notes2):
    for j, chunk in enumerate(_tw.wrap(n, width=120)):
        rr = note_r2 + k * 4 + j
        cell = ws2.cell(row=rr, column=2, value=chunk)
        cell.font = font_caption()
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=False)
        ws2.row_dimensions[rr].height = 14
ws2.freeze_panes = "B5"
ws2.page_setup.orientation = "landscape"
ws2.page_setup.fitToWidth = 1
ws2.page_setup.fitToHeight = 0
ws2.print_title_rows = "4:4"

wb.properties.creator = "Z.ai"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)

print(f"Saved: {OUT}")
print(f"Sheet 'Typos': {len(TYPOS)} findings (rows 5-{last_data1})")
print(f"Sheet 'Suspected extraction artifacts': {len(rows2)} entries (rows 5-{last_data2})")
