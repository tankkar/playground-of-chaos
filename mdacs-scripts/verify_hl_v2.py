# -*- coding: utf-8 -*-
"""Post-build verification for the highlighted deliverables, v2
(9 Nov 2026 changes: 必需 item removed, white middle columns, minimal headers)."""
import glob
import re
import subprocess
import sys

from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText

DL = "/home/z/my-project/download"
fails = []


def check(name, cond, detail=""):
    print(("PASS" if cond else "FAIL"), "-", name, detail)
    if not cond:
        fails.append(name)


# ---- 1. highlighted xlsx ----
wb = load_workbook(f"{DL}/MDACS_Typo_Check_Combined_Highlight.xlsx", rich_text=True)
check("sheets", wb.sheetnames == ['Typos (EN)', 'Typos (TC)', 'Artifacts (EN)', 'Artifacts & notes (TC)'],
      wb.sheetnames)


def sheet_rows(ws):
    n = 0
    for r in range(5, ws.max_row + 1):
        if not str(ws.cell(row=r, column=2).value or "").strip():
            break
        n += 1
    return n


en, tc = wb['Typos (EN)'], wb['Typos (TC)']
check("EN rows = 72", sheet_rows(en) == 72, sheet_rows(en))
check("TC rows = 60", sheet_rows(tc) == 60, sheet_rows(tc))

found = []
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None and "必需施行內科或外科治療" in str(c.value):
                found.append((ws.title, c.coordinate))
check("必需施行 row removed", not found, found)

# 曆日 findings removed from typo data rows (the notes legitimately mention 曆日內)
found = []
for sn, nrows in (("Typos (EN)", 72), ("Typos (TC)", 60)):
    ws_ = wb[sn]
    for r in range(5, 5 + nrows):
        for col in (3, 4):  # quote columns only
            v = ws_.cell(row=r, column=col).value
            if v is not None and "曆日" in str(v):
                found.append((sn, ws_.cell(row=r, column=col).coordinate))
check("曆日 finding rows removed", not found, found)
check("appeal-period note present", "Appeal-period units" in " ".join(
    str(c.value) for row in wb["Artifacts & notes (TC)"].iter_rows() for c in row if c.value is not None))

white_ok = True
rich = 0
for r in range(5, 5 + 60):
    for col in (3, 4):
        cell = tc.cell(row=r, column=col)
        f = cell.fill.start_color.rgb if cell.fill and cell.fill.start_color else None
        if not (f and str(f).endswith("FFFFFF")):
            white_ok = False
        if isinstance(cell.value, CellRichText):
            rich += 1
check("TC middle cols white", white_ok)
check("rich text present", rich >= 90, rich)

# ---- 2. highlighted A4 pdf ----
from pypdf import PdfReader
n_pages = len(PdfReader(f"{DL}/MDACS_Typo_Check_Combined_Highlight_A4.pdf").pages)
check("2 pages", n_pages == 2, n_pages)

txt = subprocess.run(["pdftotext", f"{DL}/MDACS_Typo_Check_Combined_Highlight_A4.pdf", "-"],
                     capture_output=True, text=True).stdout
check("title present", "MDACS Typo Check" in txt)
for absent in ["PART A", "PART B", "Incorrect text", "How to read",
               "Consolidated Findings", "必需施行", "Error type", "Reference"]:
    check(f"no '{absent}'", absent not in txt)
for present in ["from the date of medical device supplied",
                "HEALTHCARE FACILITIY INFORMATION", "可接受的例外情况",
                "須跟據指南第GN-10號通知"]:
    check(f"has '{present[:25]}'", present in txt)
check("no markup leakage", not re.findall(r"&amp;|&lt;|&gt;|undefined|NaN", txt))

# title only on page 1
p2 = subprocess.run(["pdftotext", "-f", "2", "-l", "2",
                     f"{DL}/MDACS_Typo_Check_Combined_Highlight_A4.pdf", "-"],
                    capture_output=True, text=True).stdout
check("title NOT on page 2", "MDACS Typo Check" not in p2)

# ---- 3. authoritative: no tint fill colors in the PDF content streams ----
from pypdf import PdfReader as _R
fills = set()
for page in _R(f"{DL}/MDACS_Typo_Check_Combined_Highlight_A4.pdf").pages:
    data = page.get_contents().get_data().decode("latin-1")
    fills.update(re.findall(r"([\d.]+ [\d.]+ [\d.]+) rg", data))


def _hexify(c):
    r_, g_, b_ = c.split()
    return "#%02X%02X%02X" % (round(float(r_) * 255), round(float(g_) * 255), round(float(b_) * 255))


uniq = {_hexify(c) for c in fills}
check("no red tint #FDEDEC in PDF fills", "#FDEDEC" not in uniq)
check("no green tint #E8F5E9 in PDF fills", "#E8F5E9" not in uniq)
check("white fills present", "#FFFFFF" in uniq)
check("red/green highlight colors present", "#C0392B" in uniq and "#1B7D46" in uniq)

# ---- 3b. pixels: red/green text lands in the right columns ----
import os
os.makedirs("/tmp/render", exist_ok=True)
subprocess.run("rm -f /tmp/render/hl3-*.jpg", shell=True, check=True)
subprocess.run(["pdftoppm", "-r", "100", "-jpeg", "-jpegopt", "quality=75",
                f"{DL}/MDACS_Typo_Check_Combined_Highlight_A4.pdf", "/tmp/render/hl3"], check=True)
from PIL import Image

INC_X, COR_X = (170, 458), (458, 739)
for f in sorted(glob.glob("/tmp/render/hl3-*.jpg")):
    img = Image.open(f).convert("RGB")
    W, H = img.size
    px = img.load()
    red_in = green_in = pink = mint = 0
    for y in range(H):
        for x in range(W):
            r_, g_, b_ = px[x, y]
            if abs(r_ - 253) < 10 and abs(g_ - 237) < 10 and abs(b_ - 236) < 10:
                pink += 1
            elif abs(r_ - 232) < 10 and abs(g_ - 245) < 10 and abs(b_ - 233) < 10:
                mint += 1
            elif r_ > 120 and r_ > g_ + 50 and r_ > b_ + 50 and g_ < 110:
                if INC_X[0] <= x <= INC_X[1]:
                    red_in += 1
            elif g_ > 70 and g_ > r_ + 25 and g_ > b_ + 15 and r_ < 130:
                if COR_X[0] <= x <= COR_X[1]:
                    green_in += 1
    check(f"{f}: red in incorrect col", red_in > 100, red_in)
    check(f"{f}: green in correction col", green_in > 100, green_in)

# ---- 4. regular combined rebuilt too ----
wb2 = load_workbook(f"{DL}/MDACS_Typo_Check_Combined.xlsx")
check("regular TC rows = 60", sheet_rows(wb2['Typos (TC)']) == 60, sheet_rows(wb2['Typos (TC)']))
found2 = []
for sn, nrows in (("Typos (EN)", 72), ("Typos (TC)", 60)):
    ws2_ = wb2[sn]
    for r in range(5, 5 + nrows):
        for col in (3, 4):
            v = ws2_.cell(row=r, column=col).value
            if v is not None and ("必需施行內科或外科治療" in str(v) or "曆日" in str(v)):
                found2.append((sn, ws2_.cell(row=r, column=col).coordinate))
check("regular: removed items gone", not found2, found2)

print()
if fails:
    print("FAILURES:", fails)
    sys.exit(1)
print("ALL CHECKS PASSED")
