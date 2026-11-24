# -*- coding: utf-8 -*-
"""Build MDACS_Typo_Check_Combined.xlsx — single workbook aggregating BOTH typo
rounds (English + Traditional Chinese) that were previously delivered as two
separate files.

Sheets:
  1. "Typos (EN)"            — 72 verified findings, English editions
  2. "Typos (TC)"             — 60 verified findings, Traditional Chinese editions
  3. "Artifacts (EN)"         — suspected .docx-to-text extraction artifacts (EN round)
  4. "Artifacts & notes (TC)" — extraction artifacts, character variants,
                                per-document statistics (TC round)

Pre-build verification gates (hard abort on failure):
  EN: every INCORRECT quote found in upload/merged_documents.txt (whitespace-flexible).
  TC: every INCORRECT quote found in the user's TC upload (NFC, whitespace-flexible)
      AND verbatim in the corresponding OFFICIAL MDD PDF text (NFC, space-free).
"""
import json
import math
import os
import re
import sys
import textwrap as _tw
import unicodedata

XLSX_SKILL_DIR = "/home/z/my-project/skills/xlsx"
for sub in [XLSX_SKILL_DIR, os.path.join(XLSX_SKILL_DIR, "templates")]:
    if sub not in sys.path:
        sys.path.insert(0, sub)
sys.path.insert(0, "/home/z/my-project/scripts")

from base import (setup_sheet, style_header_row, style_data_row, font_caption,
                  FONT_NAME, NEUTRAL_600, PRIMARY)
from typo_data import TYPOS as TYPOS_EN
from typo_data_cn import TYPOS as TYPOS_TC
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

SRC_EN = "/home/z/my-project/upload/merged_documents.txt"
SRC_TC = "/home/z/my-project/upload/粘贴了内容_1794032824215.txt"
CN_DIR = "/home/z/my-project/mdd_pdfs_cn"
EN_DIR = "/home/z/my-project/mdd_pdfs"
ART = "/home/z/my-project/scripts/artifacts.json"
OUT = "/home/z/my-project/download/MDACS_Typo_Check_Combined.xlsx"

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
             "GN-09", "GN-10", "RS-01", "TR-001", "TR-002", "TR-003", "TR-004",
             "TR-005", "TR-006", "TR-007", "TR-008", "TR-009", "TR-010"]

def flexible_pattern(quote):
    chars = [c for c in unicodedata.normalize("NFC", quote) if not c.isspace()]
    return re.compile(r"\s*".join(re.escape(c) for c in chars))

def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s))

def est_height(values, widths, base=15, minh=22, maxh=118):
    n = 1
    for v, w in zip(values, widths):
        v = str(v or "")
        eff = sum(2 if ord(ch) > 0x2E80 else 1 for ch in v)
        n = max(n, math.ceil(eff / max(1, w - 2)))
    return min(maxh, max(minh, n * base + 7))

def add_notes(ws, start_row, notes, width=118):
    for k, n in enumerate(notes):
        for j, chunk in enumerate(_tw.wrap(n, width=width)):
            rr = start_row + k * 4 + j
            cell = ws.cell(row=rr, column=2, value=chunk)
            cell.font = font_caption()
            cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=False)
            ws.row_dimensions[rr].height = 14

def finish_sheet(ws, last_col):
    ws.freeze_panes = "B5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "4:4"

# ---------------- 1. verification gates ----------------
probs = []

# EN gate
with open(SRC_EN, encoding="utf-8") as f:
    lines = f.readlines()

def doc_text_en(doc):
    a, b = DOC_RANGE[doc]
    return "".join(lines[a - 1:b])

for idx, (ref, inc, cor, rem) in enumerate(TYPOS_EN, 1):
    doc = ref.split()[0]
    if doc not in DOC_RANGE:
        probs.append(f"EN row {idx}: unknown doc '{doc}' in '{ref}'")
        continue
    text = doc_text_en(doc)
    for frag in [x.strip() for x in inc.split(";") if x.strip()]:
        if not flexible_pattern(frag).search(text):
            probs.append(f"EN row {idx} [{ref}]: NOT FOUND -> '{frag[:40]}'")

# TC gate
FILE2ID = {
    "COP-01C": "COP-01", "COP-02C": "COP-02", "COP-03C": "COP-03",
    "COP-04C": "COP-04", "COP-05C": "COP-05", "ExpSch-Notes-E": "ExpSch",
    "GN-00-C": "GN-00", "GN-01-C": "GN-01", "GN-02-C": "GN-02",
    "GN-03-C": "GN-03", "GN-04-C": "GN-04", "GN-06-C": "GN-06",
    "GN-07-C": "GN-07", "GN-08-C": "GN-08", "GN-09-C": "GN-09",
    "GN-10-C": "GN-10", "RS-01-E": "RS-01", "TR001C": "TR-001",
    "TR002C": "TR-002", "TR003C": "TR-003", "TR004-2022-C": "TR-004",
    "TR005C": "TR-005", "TR006C": "TR-006", "TR007C": "TR-007",
    "TR008C": "TR-008", "TR009C": "TR-009", "TR010C": "TR-010",
}
raw = open(SRC_TC, encoding="utf-8").read()
user_nfc = {}
cur, buf = None, []
for line in raw.splitlines():
    m = re.match(r"^FILE: (\S+)\.docx\s*$", line)
    if m:
        if cur:
            user_nfc[cur] = unicodedata.normalize("NFC", "\n".join(buf))
        cur = FILE2ID.get(m.group(1))
        buf = []
    elif cur is not None:
        buf.append(line)
if cur:
    user_nfc[cur] = unicodedata.normalize("NFC", "\n".join(buf))

official_norm = {}
for d in DOC_ORDER:
    p = f"{CN_DIR}/txt_{d}.txt"
    if not os.path.exists(p):
        p = f"{EN_DIR}/txt_{d}.txt"
    official_norm[d] = norm(open(p, encoding="utf-8", errors="ignore").read()) if os.path.exists(p) else ""

for idx, (ref, inc, cor, rem) in enumerate(TYPOS_TC, 1):
    doc = ref.split()[0].rstrip("，")
    if doc not in user_nfc:
        probs.append(f"TC row {idx}: unknown doc '{doc}' in '{ref}'")
        continue
    if not flexible_pattern(inc).search(user_nfc[doc]):
        probs.append(f"TC row {idx} [{ref}]: NOT FOUND in upload -> '{inc[:40]}'")
    if norm(inc) not in official_norm[doc]:
        probs.append(f"TC row {idx} [{ref}]: NOT in official PDF -> '{inc[:40]}'")

print(f"Verification: {len(TYPOS_EN)} EN + {len(TYPOS_TC)} TC rows checked, {len(probs)} problems")
for p in probs:
    print("  !!", p)
if probs:
    print("ABORT: fix data before building.")
    sys.exit(1)

N_EN, N_TC = len(TYPOS_EN), len(TYPOS_TC)

# ---------------- 2. build workbook ----------------
wb = Workbook()
HEADERS1 = ["Reference", "Incorrect text", "Proposed correct text", "Remark"]
LAST1 = 1 + len(HEADERS1)  # B..E

# ===== Sheet 1: Typos (EN) =====
ws = wb.active
ws.title = "Typos (EN)"
setup_sheet(ws, title=f"Typo Summary — MDACS Document Set, English editions (COP / GN / TR) — {N_EN} findings", last_col=LAST1)
for c, h in enumerate(HEADERS1, start=2):
    ws.cell(row=4, column=c, value=h)
style_header_row(ws, row_num=4, col_start=2, col_end=LAST1)

W1 = [30, 42, 42, 58]
for c, w in enumerate(W1, start=2):
    ws.column_dimensions[get_column_letter(c)].width = w

r = 5
for i, (ref, inc, cor, rem) in enumerate(TYPOS_EN):
    vals = [ref, inc, cor, rem]
    for c, v in enumerate(vals, start=2):
        ws.cell(row=r, column=c, value=v)
    style_data_row(ws, row_num=r, col_start=2, col_end=LAST1, row_index=i)
    for c in range(2, LAST1 + 1):
        ws.cell(row=r, column=c).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws.row_dimensions[r].height = est_height(vals, W1)
    r += 1
last_data1 = r - 1

notes_en = [
    "Scope: word-level typos only — misspellings, wrong words, missing/extra words and punctuation slips. Grammar, style, TOC/clause-numbering and superseded-reference observations were excluded per review feedback.",
    "Source: merged_documents.txt (25 MDACS documents: COP-01–05, GN-00–10, TR-001–010). Quotes are normalised: spurious spaces inserted by text extraction are re-joined.",
    f"Verification (6 Nov 2026): every finding was re-checked against the official PDFs downloaded from the MDD website (www.mdd.gov.hk → Information & Publications → Code of Practice). All {N_EN} errors are present verbatim in the current official files; names were confirmed against the MDD document list and HK e-Legislation (Cap. 231).",
]
add_notes(ws, last_data1 + 2, notes_en)
finish_sheet(ws, LAST1)

# ===== Sheet 2: Typos (TC) =====
ws2 = wb.create_sheet("Typos (TC)")
setup_sheet(ws2, title=f"Typo Summary — MDACS Document Set, Traditional Chinese versions (COP / GN / TR / RS-01) — {N_TC} findings", last_col=LAST1)
for c, h in enumerate(HEADERS1, start=2):
    ws2.cell(row=4, column=c, value=h)
style_header_row(ws2, row_num=4, col_start=2, col_end=LAST1)

W1C = [34, 44, 44, 60]
for c, w in enumerate(W1C, start=2):
    ws2.column_dimensions[get_column_letter(c)].width = w

r = 5
for i, (ref, inc, cor, rem) in enumerate(TYPOS_TC):
    vals = [ref, inc, cor, rem]
    for c, v in enumerate(vals, start=2):
        ws2.cell(row=r, column=c, value=v)
    style_data_row(ws2, row_num=r, col_start=2, col_end=LAST1, row_index=i)
    for c in range(2, LAST1 + 1):
        ws2.cell(row=r, column=c).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws2.row_dimensions[r].height = est_height(vals, W1C)
    r += 1
last_data2 = r - 1

notes_tc = [
    "Scope: character- and word-level errors only — wrong/simplified characters, wrong, missing, extra or duplicated words, punctuation slips, wrong terms and mistranslations verified against the official English editions. TOC/clause-numbering, version-date and stylistic observations were deliberately excluded per review feedback.",
    "Source: the 27-document Traditional Chinese set provided (COP-01C–05C, GN-00C–10C, TR-001C–010C, plus the English-only ExpSch-Notes-E and RS-01-E). Quotes are NFC-normalised (legacy Big5 compatibility ideographs folded) and spurious extraction spaces re-joined.",
    f"Double confirmation (7 Nov 2026): every finding was re-checked, character by character, against the official Chinese PDFs downloaded from the MDD website (www.mdd.gov.hk → Information & Publications → Code of Practice). All {N_TC} errors appear verbatim in the current official files; cross-language items (appeal-period units, reference titles, access dates, form codes) were additionally verified against the official English PDFs.",
    "Not flagged, for the record: Cap. 231 is cited as 《不良廣告(醫藥)條例》, which matches current Department of Health usage (Drug Office pages, 2026 LegCo replies) — older papers use 《不良醫藥廣告條例》; mainland GB/YY standard titles inside RS-01 and the quoted NMPA notice in TR-010 are in simplified Chinese by design; GN-00 2.48 note (c) 必需施行 vs 必須施行 — 必需 before a verb is widely tolerated in Hong Kong usage and was removed from the findings per review feedback (9 Nov 2026); COP-05 5.1 and GN-06 6.1 十四(14)個曆日內 — the appeal window runs in calendar days, so 「曆日」 is correct and those proposed 「工作日」 corrections were withdrawn (9 Nov 2026).",
]
add_notes(ws2, last_data2 + 2, notes_tc)
finish_sheet(ws2, LAST1)

# ===== Sheet 3: Artifacts (EN) =====
with open(ART, encoding="utf-8") as f:
    art = json.load(f)

rows3 = []
for a in art["A"]:
    rows3.append((a["doc"], a["line"], "Word split by space", a["text"], a["snippet"][:80]))
for b in art["B"]:
    rows3.append((b["doc"], b["line"], "Hyphen split", b["text"], b["snippet"][:80]))
rows3.sort(key=lambda x: (DOC_ORDER.index(x[0]) if x[0] in DOC_ORDER else 99, x[1]))

ws3 = wb.create_sheet("Artifacts (EN)")
HEADERS3 = ["Document", "Line in merged file", "Artifact type", "Text as extracted", "Context"]
LAST3 = 1 + len(HEADERS3)
setup_sheet(ws3, title="Suspected Text-Extraction Artifacts (English set) — Verify in Original Files", last_col=LAST3)
for c, h in enumerate(HEADERS3, start=2):
    ws3.cell(row=4, column=c, value=h)
style_header_row(ws3, row_num=4, col_start=2, col_end=LAST3)

W3 = [14, 10, 20, 24, 64]
for c, w in enumerate(W3, start=2):
    ws3.column_dimensions[get_column_letter(c)].width = w

r = 5
for i, (doc, ln, typ, txt, ctx) in enumerate(rows3):
    vals = [doc, ln, typ, txt, ctx]
    for c, v in enumerate(vals, start=2):
        ws3.cell(row=r, column=c, value=v)
    style_data_row(ws3, row_num=r, col_start=2, col_end=LAST3, row_index=i)
    for c in range(2, LAST3 + 1):
        ws3.cell(row=r, column=c).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws3.cell(row=r, column=3).alignment = Alignment(horizontal="center", vertical="top")
    ws3.row_dimensions[r].height = est_height(vals, W3, minh=18)
    r += 1
last_data3 = r - 1

cnts = art["summary"]["C_punct_space_docs"]
cnt_str = ", ".join(f"{d} {n}" for d, n in cnts.items())
notes3 = [
    "These entries are suspected artifacts of the .docx-to-text conversion (spurious spaces inside words and around hyphens). They are probably NOT typos in the original Word documents — verify against the original files before changing anything.",
    f"In addition, {art['summary']['C_total']} occurrences of spurious spaces next to punctuation (e.g. \"stocks .\", \"( Global ACI )\") were detected. Per-document counts: {cnt_str}.",
]
add_notes(ws3, last_data3 + 2, notes3)
finish_sheet(ws3, LAST3)

# ===== Sheet 4: Artifacts & notes (TC) =====
ws4 = wb.create_sheet("Artifacts & notes (TC)")
HEADERS4 = ["Document", "Location", "Category", "Text as extracted", "Explanation"]
LAST4 = 1 + len(HEADERS4)
setup_sheet(ws4, title="Extraction Artifacts, Character Variants & Cross-language Notes — Traditional Chinese Set", last_col=LAST4)
for c, h in enumerate(HEADERS4, start=2):
    ws4.cell(row=4, column=c, value=h)
style_header_row(ws4, row_num=4, col_start=2, col_end=LAST4)

W4 = [12, 22, 24, 40, 58]
for c, w in enumerate(W4, start=2):
    ws4.column_dimensions[get_column_letter(c)].width = w

rows4 = [
    ("GN-01", "section 1.1.1", "Space inside acronym", "IM DRF",
     "Spurious space inside IMDRF (the official PDF reads IMDRF) — a .docx justification/extraction artifact, not a typo in the original"),
    ("COP-02", "section 2.1.2", "Stray spaces", "（Global ACI ）",
     "Spaces around the abbreviation (same pattern in COP-03 2.3, GN-04 6.2.1.2, GN-08 2.3) — extraction artifact"),
    ("COP-02", "section 6.1", "Stray space", "終止 /暫時中止",
     "Space around the slash — extraction artifact"),
    ("GN-03", "section 7.1", "Full stop inside URL", "(https://www.mdd.gov.hk.)下載",
     "The sentence-ending period is absorbed into the URL — same in the official PDF; cosmetic"),
    ("GN-00", "sections 3.1–3.15", "Non-standard quote mark", "“…＂",
     "The closing quote of the abbreviation entries is U+FF02 ＂ instead of 」 (15 occurrences) — same in the official PDF"),
    ("TR-007", "throughout", "Variant codepoint", "内 (U+5185)",
     "內 written with the variant single-stroke form 10 times (TR-008: 3 more) — same in the official PDFs; visually near-identical"),
    ("TR-006", "section 3.4.5", "Variant character", "疱疹病毒",
     "疱疹 uses the variant 疱 (U+75B1); Hong Kong usage prefers 皰疹 — same in the official PDF; recorded as a variant, not a typo"),
    ("RS-01", "entire document", "Simplified titles (by design)", "GB/T 16886.1-2022 医疗器械生物学评价…",
     "Mainland GB/YY/GB-T standards are quoted with their official simplified-Chinese titles — correct as quoted, not typos"),
    ("TR-010", "References 7.1", "Simplified quote (by design)", "国家药监局关于发布以医疗器械作用为主的药械组合产品等2项注册审查指导原则的通告",
     "The NMPA notice is quoted in simplified Chinese — correct as quoted"),
    ("GN-08", "tail sections", "Missing heading numbers", "續期 / 承諾 / 除名 / 上訴 …",
     "The extraction dropped the automatic numbering of the last section headings (the official PDF shows them numbered)"),
    ("COP-04", "section 5.1", "Stray space", "就拒絕其申請後 、",
     "Space before 、 — extraction artifact (the superfluous 後 itself is flagged on Sheet 'Typos (TC)')"),
    ("GN-06", "body text", "Spacing variants", "（ Global ACI ）/ （GACI）",
     "Inconsistent spacing around the same abbreviation across documents — extraction/typography artifact"),
]
r = 5
for i, row in enumerate(rows4):
    vals = list(row)
    for c, v in enumerate(vals, start=2):
        ws4.cell(row=r, column=c, value=v)
    style_data_row(ws4, row_num=r, col_start=2, col_end=LAST4, row_index=i)
    for c in range(2, LAST4 + 1):
        ws4.cell(row=r, column=c).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws4.row_dimensions[r].height = est_height(vals, W4, minh=18)
    r += 1

# ---- per-document statistics table ----
stat_head_r = r + 2
ws4.cell(row=stat_head_r, column=2, value="Per-document statistics")
ws4.cell(row=stat_head_r, column=2).font = Font(name=FONT_NAME, bold=True, size=11, color=PRIMARY)
hr = stat_head_r + 1
for c, h in enumerate(["Document", "Legacy compatibility ideographs", "Inter-CJK spurious spaces"], start=2):
    ws4.cell(row=hr, column=c, value=h)
style_header_row(ws4, row_num=hr, col_start=2, col_end=4)

COMPAT = {"COP-01": 296, "COP-02": 180, "COP-03": 36, "COP-04": 53, "COP-05": 55,
          "ExpSch": 0, "GN-00": 354, "GN-01": 652, "GN-02": 53, "GN-03": 25,
          "GN-04": 279, "GN-06": 49, "GN-07": 51, "GN-08": 242, "GN-09": 93,
          "GN-10": 35, "RS-01": 0, "TR-001": 370, "TR-002": 228, "TR-003": 428,
          "TR-004": 36, "TR-005": 218, "TR-006": 316, "TR-007": 44, "TR-008": 6,
          "TR-009": 25, "TR-010": 67}
SPACES = {"COP-01": 44, "COP-02": 17, "COP-03": 37, "COP-04": 46, "COP-05": 55,
          "ExpSch": 0, "GN-00": 54, "GN-01": 85, "GN-02": 94, "GN-03": 209,
          "GN-04": 30, "GN-06": 24, "GN-07": 111, "GN-08": 35, "GN-09": 184,
          "GN-10": 85, "RS-01": 578, "TR-001": 112, "TR-002": 30, "TR-003": 78,
          "TR-004": 200, "TR-005": 30, "TR-006": 56, "TR-007": 75, "TR-008": 77,
          "TR-009": 61, "TR-010": 21}
r = hr + 1
for i, d in enumerate(DOC_ORDER):
    vals = [d, COMPAT.get(d, 0), SPACES.get(d, 0)]
    for c, v in enumerate(vals, start=2):
        ws4.cell(row=r, column=c, value=v)
    style_data_row(ws4, row_num=r, col_start=2, col_end=4, row_index=i)
    ws4.cell(row=r, column=3).alignment = Alignment(horizontal="center")
    ws4.cell(row=r, column=4).alignment = Alignment(horizontal="center")
    r += 1

notes4 = [
    "The compatibility ideographs (U+F900–FAD9, e.g. \uF9C1→療, \uFA08→行, \uF99C→列) are legacy Big5 codepoints present in BOTH the provided files and the official MDD PDFs — they render identically and are not typos. NFC normalisation is recommended when machine-processing the text.",
    "Inter-CJK spaces (e.g. 醫療 器械) come from .docx justification and PDF text-layer extraction; the official PDFs show the same pattern.",
    "Appeal-period units (for awareness, not typos): the appeal window runs in CALENDAR days (department confirmation, 9 Nov 2026), so the 「曆日」 wording in COP-05 5.1 and GN-06 6.1 is correct and was removed from the findings that day. For the record the corpus is inconsistent: every English appeal clause says \"working days\" except English COP-01 4.2.4 (\"calendar days\"), and every Chinese appeal clause says 「工作日」 except COP-05 5.1 and GN-06 6.1 (「曆日」) — including Chinese COP-01 4.2.1, which says 「工作日」 although its own English counterpart says calendar days. The unit wording across the corpus may deserve a policy-level review.",
    "GACI → Global ACI: MDD corrected this abbreviation in COP-02/03 and GN-02/04/08 on 29 Oct 2026. GN-06 and GN-09 still carry 「GACI」 in the body text (both languages) — see Sheet 'Typos (TC)'. GN-06's own revision record already claims the correction.",
    "Verification (7 Nov 2026): all official comparison texts were downloaded from www.mdd.gov.hk (Traditional Chinese Code of Practice pages) on that date; the English counterparts from the English pages of the same site.",
]
add_notes(ws4, r + 2, notes4)
finish_sheet(ws4, LAST4)

wb.properties.creator = "Z.ai"
wb.properties.title = "MDACS Typo Check — Combined Summary (EN + TC)"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)

print(f"Saved: {OUT}")
print(f"Sheet 'Typos (EN)': {N_EN} findings (rows 5-{last_data1})")
print(f"Sheet 'Typos (TC)': {N_TC} findings (rows 5-{last_data2})")
print(f"Sheet 'Artifacts (EN)': {len(rows3)} entries (rows 5-{last_data3})")
print(f"Sheet 'Artifacts & notes (TC)': {len(rows4)} artifact rows + {len(COMPAT)} stat rows")
