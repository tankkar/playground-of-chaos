#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MDACS terminology rules — the +1.0 edition's wording directives
(user directive, 24 Nov 2026).

RULES = [(incorrect, correct, remark), ...]

Corpus-wide wording replacements applied ON TOP of the typo tables in the
same tracked-changes pass (author 'denis'), so the +1.0 edition's redline
carries both: the typo corrections AND the terminology updates. Unlike
the typo tables these rows carry no document id and no clause reference —
a rule fires wherever its incorrect text appears (body, tables, headers,
footers, footnotes, endnotes), with one tracked change per occurrence.

EXCLUDED: the revision-history table. Its historical rows record the old
terminology on purpose (e.g. GN-00's 2025 row 「醫療器械行政管理制度」
取代「醫療儀器行政管理制度」 — rewriting the quoted old term would falsify
the record). The engine skips rule rows there, and the post-pack check
counts leftovers OUTSIDE that table only.

VERIFICATION (the user's standing requirement — "we have to make sure
every those rules we set is correctly replacing all correctly"):
mdacs_redline.py re-opens each packed output, accepts every revision and
counts each rule's incorrect text in the final text — the count MUST be
zero; mdacs_verify.py re-checks the same independently.

Terminology direction (example confirmed by the user, 24 Nov 2026):
品質 -> 質量 for 'quality' compounds — the MDD aligns with the mainland
GB-standard term (质量). The user typed the example in Simplified
(品质体系 -> 质量体系); the documents are Traditional Chinese, so the
rule is recorded in its Traditional form.
"""

RULES = [
    # (incorrect, correct, remark)
    ("品質體系", "質量體系",
     "品質 -> 質量 (user example, 24 Nov 2026): quality system"),
    # Further rules to be confirmed by the user before the batch run —
    # candidates sized by scripts/term_scan.py:
    #   品質管理 / 品質保證 / 品質系統 ... -> 質量...
    #   醫療儀器 -> 醫療器械 (2025 rename stragglers, if any in body)
]
