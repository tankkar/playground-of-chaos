# -*- coding: utf-8 -*-
"""Verified typo findings — MDACS document set, TRADITIONAL CHINESE versions.

Each row: (reference, incorrect_text, correct_text, remark).
Quotes are NFC-normalised (Big5 compatibility ideographs folded) and
spurious extraction spaces are re-joined (whitespace-flexible matching).

Verification (7 Nov 2026): every finding was double-checked against the
official Chinese PDFs downloaded from the MDD website (www.mdd.gov.hk,
Information & Publications > Code of Practice, Traditional Chinese pages).
All findings below appear verbatim in the current official files.
Cross-language items (working days, reference titles, access dates, form
codes, quoted English) were additionally verified against the official
English PDFs. Deliberately NOT flagged: Cap. 231 cited as 《不良廣告(醫藥)條例》
(matches current Department of Health usage), mainland-standard titles quoted
in simplified Chinese inside RS-01 / TR-010, TOC/clause-numbering and
version-date observations, and stylistic variants (爲/為, 疱/皰, 内/內).
Removed 9 Nov 2026 per review feedback: GN-00 2.48 note (c) 必需施行 → 必須施行
(必需/必須 before a verb is widely tolerated in Hong Kong usage — treated as
acceptable, not a typo); COP-05 5.1 and GN-06 6.1 十四(14)個曆日內 → 工作日
(the appeal window runs in CALENDAR days, so 曆日 is correct — the proposed
「工作日」 fixes were wrong and the unit wording elsewhere is a policy question,
not a typo).

Terminology directive RETRACTED (9 Nov 2026, later the same day): the
corpus-wide 品質管理 -> 質量管理 rule was withdrawn — the senior team will
decide that substitution case by case. GLOBAL_RULES below is now EMPTY;
the table rows are again the ONLY source of changes. Per-document rows
that happen to contain the phrase (GN-00/GN-04 2.45 「品質管理所相關」 ->
「品質管理所需」) are unaffected: they fix the wording, not the term, and
keep 品質管理 exactly as the document has it.
"""

TYPOS = [
    # ---------- COP-01 ----------
    ("COP-01 section 3.10.2",
     "可接受的例外情况",
     "可接受的例外情況",
     "Simplified character — 「况」(U+51B5) should be the Traditional 「況」"),
    ("COP-01 section 3.13.1",
     "須跟據指南第GN-10號通知",
     "須根據指南第GN-10號通知",
     "Wrong character — 「跟據」 for 「根據」"),
    # ---------- COP-03 ----------
    ("COP-03 修訂記錄 (version 0 row)",
     "（第 COP-03 號技守則）",
     "（第 COP-03 號守則）",
     "Extra character — stray 「技」 in the first-issue reference"),
    ("COP-03 section 2.11.1",
     "或系統被暫時中止或撤回認證須於，以較早的期間為準",
     "或系統認證被暫時中止或撤回，以較早的期間為準",
     "Garbled sentence — stray 「須於」 and misplaced 「認證」; the English reads "
     "\"…or suspension or withdrawal of certification, …, whichever is the earlier\""),
    ("COP-03 section 4.1(e)",
     "公眾安全問題的情况",
     "公眾安全問題的情況",
     "Simplified character — 「况」 for 「況」 (2 occurrences in this clause)"),
    ("COP-03 page headers (9 pages) (TC only)",
     "COP-03:2026(E) (Ed. 1.0)",
     "COP-03:2026(C) (Ed. 1.0)",
     "Wrong language code — the running headers of the Chinese edition say (E) "
     "throughout, while its own revision record and all other Chinese documents use (C). "
     "Edition flag added 12 Nov 2026: '(E)' is the CORRECT code in the English "
     "edition, so this row must never fire on COP-03E (replaces the blanket "
     "language filter — see mdacs_redline.select_rows)."),
    # ---------- COP-04 ----------
    ("COP-04 section 2.1.2.1",
     "及該產由合資格的製造商生產",
     "及該產品由合資格的製造商生產",
     "Missing character — 「品」 dropped from 「該產品」"),
    ("COP-04 section 4.1(d)",
     "公眾安全問題的情况",
     "公眾安全問題的情況",
     "Simplified character — 「况」 for 「況」"),
    ("COP-04 section 5.1",
     "就拒絕其申請後 、或有條件批准",
     "就拒絕其申請、或有條件批准",
     "Extra character — stray 「後」; the sentence already ends 「…的決定後十四(14)個工作日內」 "
     "(cf. the parallel clauses in COP-01/02/03)"),
    ("COP-04 section 5.1 (end of clause)",
     "就有關決定提出上訴",
     "就有關決定提出上訴。",
     "Missing punctuation — every parallel appeal clause ends with 「。」"),
    # ---------- COP-05 ----------
    ("COP-05 section 2.1.6",
     "既定的適當時間間距",
     "既定的適當時間間隔",
     "Wrong word — 「間距」 denotes physical spacing; the English is "
     "\"at appropriate established time intervals\""),
    ("COP-05 section 4.1(b)",
     "公眾安全問題的情况",
     "公眾安全問題的情況",
     "Simplified character — 「况」 for 「況」"),
    ("COP-05 section 5.1",
     "拒絕其分銷商表列 、",
     "拒絕其分銷商表列申請、",
     "Missing word — 「申請」; the English reads \"a decision … to reject an application\" "
     "(cf. COP-01 4.2.1 「就拒絕其表列申請」)"),
    # ---------- GN-00 ----------
    ("GN-00 section 2.10",
     "頸動脈（頸內總動脈及頸外總動脈）",
     "頸動脈（頸總動脈、頸內動脈及頸外動脈）",
     "Wrong terms — no arteries named 「頸內總動脈」/「頸外總動脈」 exist; the English "
     "\"carotid arteries (common internal and external)\" refers to the common, internal "
     "and external carotid arteries"),
    ("GN-00 section 2.16",
     "按醫療器械管理制度的規定圓滿完成",
     "按醫療器械行政管理制度的規定圓滿完成",
     "Missing word — 「行政」 in the system name (cf. sections 2.13–2.15 「醫療器械行政管理制度」)"),
    ("GN-00 section 2.20 (note)",
     "常稱為測試、測定或分析。",
     "常稱為測試、測定或分析。）",
     "Missing punctuation — the note opens 「(註：」 but the closing 「）」 never appears"),
    ("GN-00 section 2.23",
     "病人如没有及時採取預防措施",
     "病人如沒有及時採取預防措施",
     "Simplified character — 「没」(U+6CA1) should be 「沒」"),
    ("GN-00 section 2.38.3",
     "身體結構器官或生理過程",
     "身體結構或生理過程",
     "Extra word — 「器官」; the English reads \"…of the anatomy or of a physiological process\""),
    ("GN-00 section 2.39",
     "跟據醫療器械的特性及性質",
     "根據醫療器械的特性及性質",
     "Wrong character — 「跟據」 for 「根據」"),
    ("GN-00 section 2.39",
     "大至可歸入",
     "大致可歸入",
     "Wrong character — 「大至」 for 「大致」"),
    ("GN-00 section 2.43.1(b)",
     "負責。；",
     "負責；",
     "Duplicated punctuation — a full stop before the semicolon"),
    ("GN-00 section 2.45",
     "品質管理所相關的組織架構",
     "品質管理所需的組織架構",
     "Wrong wording — 「所相關」 is ungrammatical (and invites misreading as 「品質管理所」); "
     "the English reads \"…resources for implementing quality management\"; "
     "GN-04 section 2.8 has the same slip"),
    ("GN-00 section 2.49",
     "再標籤，消毒或殺菌。",
     "再標籤、消毒或殺菌。",
     "Wrong punctuation — the list should use 「、」 throughout, not a comma before 消毒"),
    ("GN-00 section 2.57",
     "而旨透過檢驗",
     "而旨在透過檢驗",
     "Missing character — 「在」 dropped from 「旨在」"),
    ("GN-00 section 4.1",
     "如對本概覽及醫療器械行政管理制度有任何查詢",
     "如對本指南及醫療器械行政管理制度有任何查詢",
     "Wrong word — GN-00 is the Definitions & Abbreviations guidance, not the 「概覽」 "
     "(Overview = GN-01); the sentence is copied from GN-01's enquiry block"),
    # ---------- GN-01 ----------
    ("GN-01 sections 4.4.9 and 5.13 (2 occurrences)",
     "須跟據指南第GN-10號通知",
     "須根據指南第GN-10號通知",
     "Wrong character — 「跟據」 for 「根據」 (same slip as COP-01 3.13.1)"),
    ("GN-01 section 4.4.11.2",
     "可接受的例外情况",
     "可接受的例外情況",
     "Simplified character — 「况」 for 「況」"),
    # ---------- GN-04 ----------
    ("GN-04 section 2.8",
     "品質管理所相關的組織架構",
     "品質管理所需的組織架構",
     "Wrong wording — same slip as GN-00 section 2.45 (English: \"resources for "
     "implementing quality management\")"),
    # ---------- GN-06 ----------
    ("GN-06 section 1.1",
     "及其他醫療器械科發布的及其他指南及技術參考文件",
     "及其他醫療器械科發布的指南及技術參考文件",
     "Duplicated words — 「及其他」 appears twice (cf. GN-02 section 1.1 「及其他醫療器械科"
     "發布的指南及技術參考文件」)"),
    ("GN-06 section 3.1.1",
     "International Medical Device Regulators Forum, IMRDF",
     "International Medical Device Regulators Forum, IMDRF",
     "Transposed letters — 「IMRDF」 for 「IMDRF」"),
    ("GN-06 section 5.1.1(v)",
     "貯存及運送期間的温度要求",
     "貯存及運送期間的溫度要求",
     "Simplified character — 「温」(U+6E29) should be 「溫」"),
    ("GN-06 section 8 (A003 note)",
     "由全球認可合作組織（GACI）",
     "由全球認可合作組織（Global ACI）",
     "Superseded abbreviation — MDD itself revised 「GACI」 to 「Global ACI」 on 29 Oct 2026 "
     "(COP-02/03, GN-02/04/08); GN-06's own revision record claims this fix, but the body "
     "text still reads GACI"),
    # ---------- GN-07 ----------
    ("GN-07 section 8.5.1",
     "公眾安全問題的情况。",
     "公眾安全問題的情況。",
     "Simplified character — 「况」 for 「況」"),
    ("GN-07 Appendix II (sample address)",
     "Tsim Shai Tsui",
     "Tsim Sha Tsui",
     "Misspelling — the same district-name error as the English edition; the other sample "
     "address on the same page spells it correctly"),
    # ---------- GN-08 ----------
    ("GN-08 section 7(b)",
     "構成危險的情况",
     "構成危險的情況",
     "Simplified character — 「况」 for 「況」 (2 occurrences in this clause)"),
    # ---------- GN-09 ----------
    ("GN-09 section 5.1.5",
     "Recognized Standards RS-01",
     "Recognised Standards RS-01",
     "Inconsistent spelling — the American -ize form clashes with the document title quoted "
     "in the same line (\"List of Recognised Standards\") and with the rest of the corpus; "
     "the official English edition contains the same slip"),
    ("GN-09 section 5.1.6",
     "既定的適當時間間距",
     "既定的適當時間間隔",
     "Wrong word — 「間距」 for 「間隔」 (same as COP-05 2.1.6)"),
    ("GN-09 section 5.2.1",
     "由全球認可合作組織（GACI）",
     "由全球認可合作組織（Global ACI）",
     "Superseded abbreviation — GN-09 has not yet received the 29 Oct 2026 GACI→Global ACI "
     "correction (nor has the English edition)"),
    ("GN-09 section 5.2.3",
     "添加維修服務服務",
     "添加維修服務",
     "Duplicated word — 「服務」 repeated"),
    ("GN-09 section 6.5.1(b)",
     "公眾安全問題的情况",
     "公眾安全問題的情況",
     "Simplified character — 「况」 for 「況」"),
    # ---------- TR-003 ----------
    ("TR-003 section 5.2.5",
     "如器械组合其中一件",
     "如器械組合其中一件",
     "Simplified character — 「组」(U+7EC4) should be 「組」"),
    ("TR-003 section 6.1.3",
     "特色另器械可被置於",
     "特色令器械可被置於",
     "Wrong character — 「另」 for 「令」; the English reads \"Where a medical device has "
     "features that place it into more than one class\""),
    ("TR-003 section 6.1.3",
     "一個級别",
     "一個級別",
     "Simplified character — 「别」 for 「別」 (「最高級别」 in the same sentence is also "
     "affected)"),
    ("TR-003 References 9.2",
     "《醫療器械行改管理制度中的定義及縮寫》",
     "《醫療器械行政管理制度中的定義及縮寫》",
     "Wrong character — 「行改」 for 「行政」 in the GN-00 title"),
    # ---------- TR-004 ----------
    ("TR-004 section 5.3.3",
     "更應特别注意",
     "更應特別注意",
     "Simplified character — 「别」 for 「別」"),
    ("TR-004 section 5.5.4",
     "若干類型之温度計",
     "若干類型之溫度計",
     "Simplified character — 「温」 for 「溫」"),
    ("TR-004 References 9.3",
     "《醫療器械行改管理制度中的定義及縮寫》",
     "《醫療器械行政管理制度中的定義及縮寫》",
     "Wrong character — 「行改」 for 「行政」"),
    # ---------- TR-005 ----------
    ("TR-005 section 4.2.4.9",
     "準確性行 (這是指真實性和準確性的結合 )",
     "準確性 (這是指真實性和精密度的結合 )",
     "Two errors — a stray 「行」 after 準確性, and the gloss mistranslates the English "
     "\"accuracy (which is a combination of trueness and precision)\": the second term "
     "should be 「精密度」, not 「準確性」"),
    ("TR-005 References 6.1",
     "《醫療器械分級原則》( 最終文件 SG1-N43:2005 )",
     "《醫療器械標籤》( 最終文件 SG1-N43:2005 )",
     "Wrong document title — SG1-N43:2005 is the GHTF Labelling document (English reference "
     "6.1: \"Labelling for Medical Devices\"; cf. GN-00 5.3); 《分級原則》 is SG1/N15:2006, "
     "cited correctly in TR-003 9.1"),
    ("TR-005 References 6.2",
     "《醫療器械行改管理制度中的定義及縮寫》",
     "《醫療器械行政管理制度中的定義及縮寫》",
     "Wrong character — 「行改」 for 「行政」"),
    # ---------- TR-006 ----------
    ("TR-006 section 3.2.7",
     "Glycated Heamoglobin",
     "Glycated Haemoglobin",
     "Misspelling — the same error as the English edition (TR-006 3.2.7)"),
    ("TR-006 section 3.4.1",
     "(巨噬細胞病毒)",
     "(巨細胞病毒)",
     "Wrong term — CMV is 「巨細胞病毒」 (cytomegalovirus); 「巨噬細胞」 means macrophage"),
    ("TR-006 section 3.4.6",
     "Human T Lymphotrophic Virus",
     "Human T Lymphotropic Virus",
     "Misspelling — the same error as the English edition (TR-006 3.4.6)"),
    # ---------- TR-007 ----------
    ("TR-007 section 1.1.1",
     "包括醫療器械(MD)中的嵌入的軟件",
     "包括醫療器械(MD)中嵌入的軟件",
     "Extra character — superfluous 「的」 (English: \"software embedded in a Medical "
     "Device (MD)\")"),
    ("TR-007 section 5.4.2.1",
     "表格MD-CLL或IVDMD-CCL",
     "表格MD-CCL或MDIVD-CCL",
     "Wrong form codes — MD-CCL is transposed to MD-CLL, and MDIVD-CCL is reordered to "
     "IVDMD-CCL (cf. GN-02 「表格MD-CCL」; GN-06 「表格MDIVD-CCL」)"),
    ("TR-007 section 5.4.6 (document table)",
     "體外診斷醫療器械表列指南指南》",
     "體外診斷醫療器械表列指南》",
     "Duplicated word — 「指南」 repeated in the GN-06 title"),
    # ---------- TR-008 ----------
    ("TR-008 References (IMDRF/AIMD WG/N67 entry)",
     "於 2004 年 10 月 30 日瀏覽",
     "於 2023 年 11 月 22 日瀏覽",
     "Wrong date — the English edition reads \"accessed on 22 November 2023\"; the IMDRF "
     "document was published in 2022, so a 2004 access date is impossible"),
    # ---------- TR-009 ----------
    ("TR-009 section 8 (table, 2 occurrences)",
     "醫療數位元影像傳輸協定",
     "醫療數位影像傳輸協定",
     "Extra character — 「元」 inserted into 「數位影像」 (English: \"DICOM\")"),
    # ---------- TR-010 ----------
    ("TR-010 sections 5.1.5/5.1.6 and Appendix I/II titles (4 occurrences)",
     "行政管理制度範圍涵蓋範圍內",
     "行政管理制度涵蓋範圍內",
     "Redundant word — the first 「範圍」 is superfluous (English: \"within the scope of "
     "the MDACS\")"),
    # ---------- RS-01 ----------
    ("RS-01 (annotation under the IECEE TRF 60601-2-11D entry)",
     "This Test Report applies to: IEC IEC 60601 2-11:2013",
     "This Test Report applies to: IEC 60601-2-11:2013",
     "Duplicated word — \"IEC\" repeated"),
]

# Global terminology rules — (incorrect, correct, remark), no document id.
# mdacs_redline.py applies these to EVERY file, EVERY occurrence, on top of
# the per-document rows above. Not typo findings: editorial directives.
# EMPTY since 9 Nov 2026: the 品質管理 -> 質量管理 directive was retracted
# (senior review — that substitution will be decided case by case), so no
# corpus-wide replacement fires any more.
GLOBAL_RULES = []
