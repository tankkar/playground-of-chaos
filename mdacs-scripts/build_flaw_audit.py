#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build MDACS_Flaw_Audit_Summary.xlsx — ONE sheet, ONE table of every
verified contradiction / flaw found across the 39 MDACS deliverables.

Styling per the xlsx skill design system (templates/base.py): B2 canvas
origin, primary header, alternating row fills, no gridlines, accent
colors on the Severity column only. Coverage note as caption block
under the table."""

import os
import sys

XLSX_SKILL_DIR = "/home/z/my-project/skills/xlsx"
for sub in (os.path.join(XLSX_SKILL_DIR, "templates"),
            "/home/z/my-project/scripts"):
    if sub not in sys.path:
        sys.path.insert(0, sub)

from base import (FONT_NAME, HEADER_BOLD, PRIMARY, ACCENT_NEGATIVE,   # noqa
                 ACCENT_WARNING, NEUTRAL_600, setup_sheet, font_caption,
                 style_header_row, style_data_row)                     # noqa
from flaw_audit_data import FINDINGS                                   # noqa
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
import math
import unicodedata

OUT = "/home/z/my-project/download/MDACS_Flaw_Audit_Summary.xlsx"

HEADERS = ["No.", "Severity", "Document(s)", "Location", "Category",
           "Finding", "Evidence (verbatim from source)"]
WIDTHS = [5.5, 10, 16, 21, 21, 44, 44]
LAST_COL = 1 + len(HEADERS)          # B..I -> 8

SEV_COLOR = {"High": ACCENT_NEGATIVE, "Medium": ACCENT_WARNING,
             "Low": NEUTRAL_600}


def disp_w(text):
    w = 0.0
    for ch in str(text):
        w += 1.7 if unicodedata.east_asian_width(ch) in ("W", "F") else 1.0
    return w


def est_lines(text, col_width):
    per_line = max(6.0, col_width - 1.5)
    return max(1, math.ceil(disp_w(text) / per_line))


def main():
    wb = Workbook()
    ws = wb.active
    ws.title = "Flaw Audit"

    setup_sheet(ws, title="MDACS Document Flaw Audit — "
                          "contradictions & inconsistencies",
                last_col=LAST_COL)

    # subtitle (row 3, caption style)
    ws.merge_cells(start_row=3, start_column=2, end_row=3, end_column=LAST_COL)
    sub = ws.cell(row=3, column=2, value=(
        "39 deliverables audited in full (21 English + 18 Traditional "
        "Chinese) · 20 Nov 2026 · every quote below verified verbatim "
        "against the source text"))
    sub.font = font_caption()
    sub.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[3].height = 16

    # headers (row 4)
    for col, h in enumerate(HEADERS, start=2):
        ws.cell(row=4, column=col, value=h)
    style_header_row(ws, 4, 2, LAST_COL)

    # data rows (row 5+)
    for i, (sev, docs, loc, cat, finding, evidence) in enumerate(FINDINGS):
        r = 5 + i
        values = [i + 1, sev, docs, loc, cat, finding, evidence]
        for c, v in enumerate(values, start=2):
            ws.cell(row=r, column=c, value=v)
        style_data_row(ws, r, 2, LAST_COL, i)
        # alignment: No./Severity centred, rest left + wrapped, top-aligned
        for c in range(2, LAST_COL + 1):
            cell = ws.cell(row=r, column=c)
            if c in (2, 3):
                cell.alignment = Alignment(horizontal="center",
                                            vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left",
                                           vertical="top", wrap_text=True)
        # severity accent color
        ws.cell(row=r, column=3).font = Font(name=FONT_NAME, size=11,
                                             color=SEV_COLOR[sev])
        # row height from wrapped-line estimate (max across text cells)
        lines = 1
        for c, w in ((4, WIDTHS[2]), (5, WIDTHS[3]), (6, WIDTHS[4]),
                     (7, WIDTHS[5]), (8, WIDTHS[6])):
            text = ws.cell(row=r, column=c).value or ""
            lines = max(lines, est_lines(text, w))
        ws.row_dimensions[r].height = min(150, max(22, lines * 13.5 + 7))

    # column widths
    for idx, w in enumerate(WIDTHS):
        ws.column_dimensions[
            chr(ord("B") + idx) if idx < 7 else "I"].width = w

    # coverage note (caption block under the table)
    last_row = 4 + len(FINDINGS)
    note_row = last_row + 2
    ws.merge_cells(start_row=note_row, start_column=2, end_row=note_row,
                   end_column=LAST_COL)
    note = (
        "Scope & coverage: COP-01/03/04/05 (E+C), GN-00/01/02/06/07/08/09/10 "
        "(E; C except GN-02 & GN-10), TR-001/003/004/005/006/007/008/010 "
        "(E+C), TR-009 (C only) and RS-01 (E) — 39 files, all read in full. "
        "98 verified findings: 7 High / 69 Medium / 22 Low. "
        "Method: six parallel family audits, then scripted verbatim "
        "verification of every quoted fragment against the source text; "
        "one candidate finding was dropped after verification (TR-010 §5 "
        "“Within the scope of MDACS” column — the cells contain Wingdings "
        "tick symbols, not empty). "
        "Notes: the 12 Nov 2026 typo-fix rows legitimately differ between "
        "the E and C versions (each language received its own typo "
        "corrections) and are not counted as contradictions. GN-03/04/05, "
        "COP-02 and TR-002 are outside the audited set."
    )
    nc = ws.cell(row=note_row, column=2, value=note)
    nc.font = font_caption()
    nc.alignment = Alignment(horizontal="left", vertical="top",
                              wrap_text=True)
    ws.row_dimensions[note_row].height = 96

    # freeze header rows; landscape print
    ws.freeze_panes = "B5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "4:4"

    wb.properties.creator = "Z.ai"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print(f"saved {OUT}  ({len(FINDINGS)} findings, "
          f"{sum(1 for f in FINDINGS if f[0]=='High')} High / "
          f"{sum(1 for f in FINDINGS if f[0]=='Medium')} Medium / "
          f"{sum(1 for f in FINDINGS if f[0]=='Low')} Low)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
