#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify every candidate flaw finding against the corpus text.

Each check = (id, description, list of (file, fragment) that must ALL be
present; optional (file, fragment, min_count) count checks).
Run:  python3 scripts/verify_flaws.py   -> PASS/FAIL per check.
"""

import re
import sys

C = "/home/z/my-project/corpus"

FILES = [
    "COP-01C-2026-1.1", "COP-01E-2026-1.1", "COP-03C-2026-1.1",
    "COP-03E-2026-1.1", "COP-04C-2026-1.1", "COP-04E-2026-1.1",
    "COP-05C-2026-1.1", "COP-05E-2026-1.1", "GN-00-C-2026-2",
    "GN-00-E-2026-2", "GN-01-C-2026-3.1", "GN-01-E-2026-3.1",
    "GN-02-E-2026-1.2", "GN-06-C-2026-1.3", "GN-06-E-2026-1.2",
    "GN-07-C-2026-1.1", "GN-07-E-2026-1.1", "GN-08-C-2026-1.1",
    "GN-08-E-2026-1.1", "GN-09-C-2026-1.1", "GN-09-E-2026-1.1",
    "GN-10-E-2026.1", "RS-01-E-2026.1", "TR001E-2026", "TR003C-2026",
    "TR003E-2026", "TR004C-2026", "TR004E-2026", "TR005C-2026.1",
    "TR005E-2026", "TR006C-2026", "TR006E-2026", "TR007C-2026.1",
    "TR007E-2026.1", "TR008C-2026.1", "TR008E-2026.1", "TR009C-2026",
    "TR010C-2026.1", "TR010E-2026.1",
]

TEXT = {}
for f in FILES:
    with open(f"{C}/{f}.txt", encoding="utf-8") as fh:
        TEXT[f] = fh.read()

CHECKS = [
    # ---------------- HIGH ----------------
    ("H1a", "COP-01E appeal = calendar days",
     [("COP-01E-2026-1.1", "fourteen (14) calendar days")]),
    ("H1b", "COP-01C appeal = working days",
     [("COP-01C-2026-1.1", "14)個工作日內")]),
    ("H1c", "COP-03E appeal = working days",
     [("COP-03E-2026-1.1", "fourteen (14) working days")]),
    ("H2a", "COP-03E renewal: five-year validity",
     [("COP-03E-2026-1.1", "five-year validity period")]),
    ("H2b", "COP-03C renewal: three-year validity",
     [("COP-03C-2026-1.1", "三年有效期")]),
    ("H2c", "GN-08E manufacturer listing validity 5 years",
     [("GN-08-E-2026-1.1", "five (5) years")]),
    ("H3a", "GN-01C cl 3.4 cites TR-002 for EP",
     [("GN-01-C-2026-3.1", "TR-002 號技術參考文件所載")]),
    ("H3b", "GN-01E cl 3.4 cites TR-004 for EP",
     [("GN-01-E-2026-3.1", "in TR-004")]),
    ("H3c", "GN-00E: EP described in TR-004",
     [("GN-00-E-2026-2", "as described in TR-004")]),
    ("H4a", "COP-05E appeal = working days",
     [("COP-05E-2026-1.1", "fourteen (14) working days")]),
    ("H4b", "COP-05C appeal = calendar days (曆日)",
     [("COP-05C-2026-1.1", "曆日")]),
    ("H5a", "TR-003E Rule 15 NOTE physical action",
     [("TR003E-2026", "by means of physical action")]),
    ("H5b", "TR-003C NOTE excludes contact lenses",
     [("TR003C-2026", "以實質動作清洗隱形眼鏡以外的醫")]),
    ("H5c", "TR-003E contact-lens products Class III",
     [("TR003E-2026", "in which case they are in Class III")]),
    ("H6a", "TR-004E 5.13.1 animal/plant/bacterial",
     [("TR004E-2026", "animal, plant, or bacterial origin")]),
    ("H6b", "TR-004E 5.13.3 'other than 5.13.1/2 (e.g. plant/bacterial)'",
     [("TR004E-2026", "for example, materials of plant or bacterial origin")]),
    ("H6c", "TR-004C same defect",
     [("TR004C-2026", "例如：植物或細菌來源的物料")]),
    # ---------------- COP medium ----------------
    ("M3a", "COP-01E TOC lists Enquiries as section 5",
     [("COP-01E-2026-1.1", "Enquiries\t12")]),
    ("M3b", "COP-01E body: section 5 = POBO compliance",
     [("COP-01E-2026-1.1", "Compliance with the Prevention of Bribery Ordinance")]),
    ("M4a", "COP-01E row0 2005 with code 2010",
     [("COP-01E-2026-1.1", "1 Sep 2005 | First issue of COP-01 | COP-01:2010(E)")]),
    ("M4b", "COP-01C row0 code 2005",
     [("COP-01C-2026-1.1", "COP-01:2005(C)")]),
    ("M5a", "COP-03C row5 dated 2025 with 2026 code",
     [("COP-03C-2026-1.1", "2025年9月1日")]),
    ("M5b", "COP-03C row5 code",
     [("COP-03C-2026-1.1", "COP-03:2026(C)")]),
    ("M6a", "COP-05E adv clause cites 2.4.2(a)/(b)",
     [("COP-05E-2026-1.1", "2.4.2(a) and 2.4.2(b)")]),
    ("M6b", "COP-05C cites 2.4.1(a)/(b)",
     [("COP-05C-2026-1.1", "2.4.1(a)及2.4.1(b)")]),
    ("M7a", "COP-05E 2026 row names 2.2.2",
     [("COP-05E-2026-1.1", "Clause 2.2.2, 2.5.1, 2.6.1, 2.6.2, 5.1, 5.4 and 7.1 are revised")]),
    ("M7b", "COP-05C 2026 row names 2.5",
     [("COP-05C-2026-1.1", "修改了第2.5、2.5.1")]),
    ("M7c", "COP-05C has 2024-08-08 edition",
     [("COP-05C-2026-1.1", "2024年8月8日")]),
    ("M7d", "COP-05E lacks 2024-08-08 edition",
     [("ABSENT:COP-05E-2026-1.1", "8 August 2024")]),
    ("M8a", "COP-05E FSN issuers incl. MDD/overseas authorities",
     [("COP-05E-2026-1.1", "product safety alerts issued by MDD or other overseas authorities")]),
    ("M8b", "COP-05C narrower issuer list",
     [("COP-05C-2026-1.1", "製造商、本地負責人或其他規管當局")]),
    # ---------------- GN core ----------------
    ("M9a", "GN-00E latest typo row",
     [("GN-00-E-2026-2", "Typos in clauses 2.2, 2.25 and 3.1 are fixed")]),
    ("M9b", "GN-00C latest typo row lists many clauses",
     [("GN-00-C-2026-2", "2.10、2.16、2.20")]),
    ("M10a", "GN-00E refs item 1: N41R9 titled EP",
     [("GN-00-E-2026-2", "Essential Principles of Safety and Performance of Medical Devices. Final Document SG1-N41R9:2005")]),
    ("M10b", "GN-00C refs item 1: STED title",
     [("GN-00-C-2026-2", "技術文件摘要")]),
    ("M12", "GN-01C delisting cites cl 3.5",
     [("GN-01-C-2026-3.1", "第 3.5 節訂明")]),
    ("M12b", "GN-01E 'as stipulated above'",
     [("GN-01-E-2026-3.1", "as stipulated above")]),
    ("M13a", "GN-02E cites samples in Clause 12/13",
     [("GN-02-E-2026-1.2", "Clause 12"), ("GN-02-E-2026-1.2", "Clause 13")]),
    # ---------------- GN tech ----------------
    ("M14a", "GN-06E LRP pointers GN-01/GN-03/COP-01",
     [("GN-06-E-2026-1.2", "Guidance Notes GN-01, Guidance Notes GN-03, and Code of Practice COP-01")]),
    ("M14b", "GN-06C points only GN-01 ss3-5",
     [("GN-06-C-2026-1.3", "GN-01 號第 3、4 及 5 節")]),
    ("M2a", "GN-06E appeal working days",
     [("GN-06-E-2026-1.2", "fourteen (14) working days")]),
    ("M2b", "GN-06C appeal calendar days",
     [("GN-06-C-2026-1.3", "曆日")]),
    ("M15a", "GN-07E Appendix I broken 'Clause 1.1'",
     [("GN-07-E-2026-1.1", "summarised in Clause 1.1")]),
    ("M15b", "GN-07C same",
     [("GN-07-C-2026-1.1", "1. 1 節")]),
    ("M16a", "GN-07 body: 7 years from supply",
     [("GN-07-E-2026-1.1", "seven (7) years from the date on which the medical device is supplied")]),
    ("M16b", "GN-07 sample: 7 years from import",
     [("GN-07-E-2026-1.1", "seven (7) years from the date of product import")]),
    ("M17", "GN-07E cl 8.1 'subject to Clause 8.4'",
     [("GN-07-E-2026-1.1", "subject to Clause 8.4")]),
    ("M18a", "GN-07 sample: Class IV under EU classification",
     [("GN-07-E-2026-1.1", "Class IV (Rule 8) under EU")]),
    ("M18b", "GN-07C same",
     [("GN-07-C-2026-1.1", "歐盟醫療器械分級第IV")]),
    ("M19a", "GN-08E body cites cl 4.1.3",
     [("GN-08-E-2026-1.1", "referred to in clause 4.1.3")]),
    ("M19b", "GN-08E 2026 row cites 4.3/4.8",
     [("GN-08-E-2026-1.1", "Clause 4.3, 4.8, 5.2, 8.1 and 8.4 are revised")]),
    ("M20a", "GN-08C names listed importer",
     [("GN-08-C-2026-1.1", "表列進口商必須為該等巡查作好準備")]),
    ("M20b", "GN-08E names listed local manufacturer",
     [("GN-08-E-2026-1.1", "listed local manufacturer must make provision for such inspections")]),
    ("M23", "GN-08E 'see also clause 5.3'",
     [("GN-08-E-2026-1.1", "see also clause 5.3")]),
    ("M24a", "GN-09E Appendix I 5.1.4 x3",
     [("GN-09-E-2026-1.1", "5.1.4")], {"GN-09-E-2026-1.1": ("5.1.4", 3)}),
    ("M24b", "GN-09E 5.4.1 (f) x2",
     [("GN-09-E-2026-1.1", "5.4.1 (f)")], {"GN-09-E-2026-1.1": ("5.4.1 (f)", 2)}),
    ("M25a", "GN-09E uses GACI",
     [("GN-09-E-2026-1.1", "(GACI)")]),
    ("M25b", "GN-09C uses Global ACI",
     [("GN-09-C-2026-1.1", "Global ACI")]),
    ("M26a", "GN-09C complaints for imported devices",
     [("GN-09-C-2026-1.1", "以處理有關已進口醫療器械的投訴")]),
    ("M26b", "GN-09E complaints for distributed devices",
     [("GN-09-E-2026-1.1", "distributed medical devices")]),
    ("M27a", "GN-10E App I: address change = Major",
     [("GN-10-E-2026.1", "Change of address of manufacturer")]),
    ("M27b", "GN-10E flowchart G: address change = Minor",
     [("GN-10-E-2026.1", "Is the manufacturer's address on the labelling changing?")]),
    ("M28a", "GN-10E 5.3.1 supplier replacement non-reportable",
     [("GN-10-E-2026.1", "Replacement, addition or removal of raw material suppliers")]),
    ("M28b", "GN-10E App I supplier change = Minor",
     [("GN-10-E-2026.1", "A change in supplier that extrudes the polymer tubing")]),
    # ---------------- TR ----------------
    ("M29a", "TR001E TOC: References page 2",
     [("TR001E-2026", "References\t2")]),
    ("M30a", "TR001E intro says tables in Clause 5.2",
     [("TR001E-2026", "tables in Clause 5.2")]),
    ("M30b", "TR001E 6.2 says tables at Appendix 1",
     [("TR001E-2026", "The three tables at Appendix 1")]),
    ("M33a", "TR-005E 'other than 4.2.1.4'",
     [("TR005E-2026", "other than those covered by 4.2.1.4")]),
    ("M33b", "TR-005C same",
     [("TR005C-2026.1", "4.2.1.4")]),
    ("M34a", "TR-005C 2024-04-02 substantive row",
     [("TR005C-2026.1", "修改了第4.2.2.3項")]),
    ("M35a", "TR-006E row0 2009 with 2006 code",
     [("TR006E-2026", "1 Dec 2009 | First issue of TR-006 | TR-006:2006(E)")]),
    ("M36a", "TR-007E 2026 row: added set",
     [("TR007E-2026.1", "Clauses 1.1.3, 3.3, 5.5.1.3, 7 are added")]),
    ("M36b", "TR-007C 2026 row: same set marked 修改",
     [("TR007C-2026.1", "修改第 1.1.3、3.3、5.5.1.3、7節內容")]),
    ("M36c", "TR-007C 2026 row: revised set marked 增加",
     [("TR007C-2026.1", "增加第4.1.1")]),
    ("M37a", "TR-007E HSA ref 2024.03",
     [("TR007E-2026.1", "2024.03")]),
    ("M37b", "TR-007C HSA ref 2022-04",
     [("TR007C-2026.1", "2022年4月")]),
    ("M38", "TR-007C wrong TR-008 title",
     [("TR007C-2026.1", "《人工醫療器械》")]),
    ("M39a", "TR-007E SaMD note (c) EN",
     [("TR007E-2026.1", "not necessary for a hardware MD to achieve its intended medical purpose")]),
    ("M39b", "TR-007C note (c) CN",
     [("TR007C-2026.1", "不需要醫療器械硬件也能達到自身原擬醫療用途")]),
    ("M40a", "TR-008E 2025 row: 4.4 revised",
     [("TR008E-2026.1", "Clause 4.4 and 5.1 are revised")]),
    ("M40b", "TR-008E 2026 row: 4.4 added",
     [("TR008E-2026.1", "Clause 4.4 and 4.5 are added")]),
    ("M42", "TR-009C row cites 第8節",
     [("TR009C-2026", "第8節")]),
    ("M43a", "TR-010E row cites 5.1.1",
     [("TR010E-2026.1", "clause 5.1.1 and Appendix II are fixed")]),
    ("M43b", "TR-010C row cites 5.1.5/5.1.6",
     [("TR010C-2026.1", "5.1.5、5.1.6")]),
    ("M44a", "TR-010C extra origin category",
     [("TR010C-2026.1", "包含或組成自該等組織或細胞的產品")]),
    ("M45a", "TR-010E 'within scope of MDACS'",
     [("TR010E-2026.1", "are considered to be within scope of MDACS")]),
    ("M45b", "TR-010C '方可被定為醫療器械'",
     [("TR010C-2026.1", "方可被定為醫療器械")]),
    ("L31", "TR-010E truncated cell 'of human'",
     [("TR010E-2026.1", "blood cells of human")]),
    # ---------------- RS-01 ----------------
    ("M47a", "RS-01 YY/T 0664-2020 twice",
     [], {"RS-01-E-2026.1": ("YY/T 0664-2020", 2)}),
    ("M47b", "RS-01 GB/T 7341.3-2024 twice",
     [], {"RS-01-E-2026.1": ("GB/T 7341.3-2024", 2)}),
    ("M47c", "RS-01 YY/T 0273-2022 twice",
     [], {"RS-01-E-2026.1": ("YY/T 0273-2022", 2)}),
    ("M47d", "RS-01 ISO 8872:2022 twice",
     [], {"RS-01-E-2026.1": ("ISO 8872:2022", 2)}),
    ("M47e", "RS-01 ISO 11810:2015 twice",
     [], {"RS-01-E-2026.1": ("ISO 11810:2015", 2)}),
    ("M47f", "RS-01 YY/T 0855.1-2011 twice",
     [], {"RS-01-E-2026.1": ("YY/T 0855.1-2011", 2)}),
    ("M47g", "RS-01 YY/T 0528-2025 twice",
     [], {"RS-01-E-2026.1": ("YY/T 0528-2025", 2)}),
    ("M48", "RS-01 YY 9706.231-2023 present",
     [], {"RS-01-E-2026.1": ("YY 9706.231-2023", 1)}),
    ("M49", "RS-01 corrupted EN 14180 title",
     [("RS-01-E-2026.1", "coSterilizers")]),
    ("M50a", "RS-01 truncated 11073-10407 title",
     [("RS-01-E-2026.1", "ISO/IEEE 11073-10407:2022 | Health informatics — Device interoperability |")]),
    ("M51a", "RS-01 ANSI combination set without year",
     [("RS-01-E-2026.1", "ANSI Z136.1 and Z136.2 Combination Set")]),
    ("M51b", "RS-01 intro requires year/version",
     [("RS-01-E-2026.1", "specific publication year or version")]),
    ("M52a", "RS-01 10993-17 old title",
     [("RS-01-E-2026.1", "allowable limits for leachable substances")]),
    ("M52b", "RS-01 odd 2026d designator",
     [("RS-01-E-2026.1", "ISO 10993-3:2026d")]),
    # ---------------- LOW spot checks ----------------
    ("L1a", "COP-03E clause 2.11 mention exists (rev row)",
     [("COP-03E-2026-1.1", "moved to Clause 2.11")]),
    ("L3a", "COP-04E lowercase listed importer survives",
     [("COP-04E-2026-1.1", "listed  importer must make provision")]),
    ("L4a", "COP-04C old office name survives",
     [("COP-04C-2026-1.1", "醫療器械管制辦公室")]),
    ("L5a", "COP-03E should apply for renewal",
     [("COP-03E-2026-1.1", "should apply for renewal")]),
    ("L6a", "COP-01E should-not (ads)",
     [("COP-01E-2026-1.1", "should not mention listing number")]),
    ("L6b", "COP-01C 不可 (ads)",
     [("COP-01C-2026-1.1", "不可在任何廣告")]),
    ("L8a", "COP-05E row cites nonexistent 2.2.5.1",
     [("COP-05E-2026-1.1", "2.2.5.1")]),
    ("L9a", "GN-00C row cites 2.43.1",
     [("GN-00-C-2026-2", "2.43.1")]),
    ("L10a", "GN-00E cl 2.13 ties EP to TR-004",
     [("GN-00-E-2026-2", "under TR-004")]),
    ("L13a", "GN-01E list shows manufacturer and model",
     [("GN-01-E-2026-3.1", "manufacturer and model of the device")]),
    ("L13b", "GN-01C list shows 品牌和型號",
     [("GN-01-C-2026-3.1", "品牌和型號")]),
    ("L15a", "GN-01E cites GN-00 under variant title",
     [("GN-01-E-2026-3.1", "Guidance Notes for Definitions and Abbreviations for")]),
    ("L15b", "GN-00E printed title",
     [("GN-00-E-2026-2", "Definitions and Abbreviations for the Medical Device Administrative Control System")]),
    ("L16a", "GN-02E TR-003 title variant 1",
     [("GN-02-E-2026-1.2", "Classification of Medical Devices")]),
    ("L16b", "GN-02E TR-003 title variant 2",
     [("GN-02-E-2026-1.2", "Classification of General Medical Devices")]),
    ("L17a", "GN-06E body cites GN-03",
     [("GN-06-E-2026-1.2", "Guidance Notes GN-01, Guidance Notes GN-03, Code of Practice COP-01")]),
    ("L20a", "GN-07E scope import AND supply",
     [("GN-07-E-2026-1.1", "import and supply medical devices")]),
    ("L21a", "GN-07C surviving 醫療事故",
     [("GN-07-C-2026-1.1", "醫療事故呈報指南")]),
    ("L22a", "GN-07C row 2.0: 2021 date, 2020 code",
     [("GN-07-C-2026-1.1", "GN-07:2020(C)")]),
    ("L24a", "TR-006E pathogens list holds EGFR",
     [("TR006E-2026", "EGFR stands for")]),
    ("L24b", "TR-006E pathogens header",
     [("TR006E-2026", "Abbreviations of the pathogens")]),
    ("L25a", "TR-007E row1 combined 3.3/3.4",
     [("TR007E-2026.1", "3.3 and 3.4 are combined")]),
    ("L26a", "TR-007E should have a QMS",
     [("TR007E-2026.1", "should have a QMS established")]),
    ("L26b", "TR-007E shall implement a QMS",
     [("TR007E-2026.1", "shall implement a QMS")]),
    ("L27a", "TR-008E OGCIO entry",
     [("TR008E-2026.1", "Ethical Artificial Intelligence Framework")]),
    ("L28a", "TR-008E cl 4.5 shall",
     [("TR008E-2026.1", "shall be properly recorded, maintained and made available")]),
    ("L28b", "TR-008C cl 4.5 應",
     [("TR008C-2026.1", "應妥善記錄")]),
    ("L29a", "TR-008C Taiwan-style terms",
     [("TR008C-2026.1", "人工智慧醫療設備")]),
    ("L30a", "TR-009C empty design-feature cell",
     [("TR009C-2026", "適合病人的輪椅")]),
    ("L33a", "GN-10E Minor def captures non-reportable",
     [("GN-10-E-2026.1", "does not fall in the definition of Major Change")]),
    ("L33b", "GN-10E 5.3 no reporting",
     [("GN-10-E-2026.1", "do not require reporting to the MDD")]),
    ("L34a", "GN-09E MD Chair with insufflator",
     [("GN-09-E-2026-1.1", "MD Chair")]),
]


def run():
    npass = nfail = 0
    fails = []
    for chk in CHECKS:
        cid, desc, pairs, *rest = chk
        counts = rest[0] if rest else {}
        ok = True
        why = []
        for fname, frag in pairs:
            absent = fname.startswith("ABSENT:")
            fname = fname.replace("ABSENT:", "")
            found = frag in TEXT[fname]
            if absent:
                found = not found
            if not found:
                ok = False
                why.append(f"{'ABSENT-OK' if absent else 'MISS'} {fname}: {frag[:60]!r}")
        for fname, (frag, n) in counts.items():
            k = TEXT[fname].count(frag)
            if k != n:
                ok = False
                why.append(f"COUNT {fname}: {frag!r} = {k} (want {n})")
        if ok:
            npass += 1
        else:
            nfail += 1
            fails.append((cid, desc))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {cid}  {desc}")
        for w in why:
            print(f"         {w}")
    print(f"\n{npass} passed, {nfail} failed")
    if fails:
        print("FAILED:", ", ".join(c for c, _ in fails))
    return 0 if not nfail else 1


if __name__ == "__main__":
    sys.exit(run())
