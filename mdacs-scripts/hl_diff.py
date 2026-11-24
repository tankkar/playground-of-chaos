# -*- coding: utf-8 -*-
"""Shared highlight-diff engine for the MDACS typo deliverables.

Given a (incorrect_text, correct_text) quote pair, produce two span lists:
  spans_inc — segments of the INCORRECT text, tagged  ''  (plain) or 'bad'
  spans_cor — segments of the CORRECT   text, tagged  ''  (plain) or 'fix'

Rendering (xlsx rich text / reportlab inline markup) then shows:
  'bad' -> dark red bold     (the wrong letter/word as printed)
  'fix' -> dark green bold   (the proposed correction)

Diff granularity:
  * text containing CJK  -> character-level SequenceMatcher
  * pure Latin text      -> word-token level; single similar token pairs are
                            further refined to LETTER level (ratio >= 0.7),
                            so e.g. "FACILITIY" highlights only the stray "I".

Pure insertions (missing text) have no 'bad' span on the incorrect side —
like a git diff, the addition shows only in green on the correct side.
"""
import re
from difflib import SequenceMatcher

_TOKEN_RE = re.compile(r"\s+|\S+")
_SIMILAR = 0.7


def _has_cjk(s):
    for ch in s:
        o = ord(ch)
        if 0x2E80 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
            return True
    return False


def _merge(spans):
    """Join adjacent spans carrying the same tag."""
    out = []
    for t, tag in spans:
        if not t:
            continue
        if out and out[-1][1] == tag:
            out[-1] = (out[-1][0] + t, tag)
        else:
            out.append((t, tag))
    return out


def _char_spans(a, b):
    """Character-level diff of two strings -> (a_spans, b_spans)."""
    sm = SequenceMatcher(None, a, b, autojunk=False)
    A, B = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            A.append((a[i1:i2], ""))
            B.append((b[j1:j2], ""))
        elif tag == "delete":
            A.append((a[i1:i2], "bad"))
        elif tag == "insert":
            B.append((b[j1:j2], "fix"))
        else:  # replace
            A.append((a[i1:i2], "bad"))
            B.append((b[j1:j2], "fix"))
    return _merge(A), _merge(B)


def diff_spans(inc, cor):
    """Return (spans_inc, spans_cor) for a quote pair.

    Each span is (text, tag) with tag in {'', 'bad'} for the incorrect side
    and {'', 'fix'} for the correct side. Concatenating the texts of either
    list reproduces the original string exactly (round-trip guarantee).
    """
    if _has_cjk(inc) or _has_cjk(cor):
        return _char_spans(inc, cor)

    # ---- pure Latin: word-token level ----
    ta = _TOKEN_RE.findall(inc)
    tb = _TOKEN_RE.findall(cor)
    sm = SequenceMatcher(None, ta, tb, autojunk=False)
    A, B = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            A.append(("".join(ta[i1:i2]), ""))
            B.append(("".join(tb[j1:j2]), ""))
        elif tag == "delete":
            A.append(("".join(ta[i1:i2]), "bad"))
        elif tag == "insert":
            B.append(("".join(tb[j1:j2]), "fix"))
        else:  # replace
            aa, bb = ta[i1:i2], tb[j1:j2]
            if (len(aa) == 1 and len(bb) == 1
                    and not aa[0].isspace() and not bb[0].isspace()
                    and SequenceMatcher(None, aa[0], bb[0]).ratio() >= _SIMILAR):
                sa, sb = _char_spans(aa[0], bb[0])
                A.extend(sa)
                B.extend(sb)
            else:
                A.append(("".join(aa), "bad"))
                B.append(("".join(bb), "fix"))
    return _merge(A), _merge(B)


def roundtrip_ok(spans, original):
    return "".join(t for t, _ in spans) == original


def has_highlight(spans):
    return any(tag for _, tag in spans)


def render_plain(spans):
    """debug helper: [text] brackets around highlighted parts"""
    return "".join("[%s]" % t if tag else t for t, tag in spans)


if __name__ == "__main__":
    # smoke tests
    tests = [
        ("HEALTHCARE FACILITIY INFORMATION", "HEALTHCARE FACILITY INFORMATION"),
        ("a compressive summary", "a comprehensive summary"),
        ("Undesirable Medical Advertisement Ordinance",
         "Undesirable Medical Advertisements Ordinance"),
        ("this document and theMDACS should", "this document and the MDACS should"),
        ("可接受的例外情况", "可接受的例外情況"),
        ("或系統被暫時中止或撤回認證須於，以較早的期間為準",
         "或系統認證被暫時中止或撤回，以較早的期間為準"),
        ("the three-year validity period", "the five-year validity period"),
        ("Delisting Application tin MDIS", "Delisting Application in MDIS"),
    ]
    for inc, cor in tests:
        si, sc = diff_spans(inc, cor)
        assert roundtrip_ok(si, inc) and roundtrip_ok(sc, cor), (inc, cor)
        print("INC :", render_plain(si))
        print("COR :", render_plain(sc))
        print()
