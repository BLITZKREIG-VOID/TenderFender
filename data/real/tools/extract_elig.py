"""Build a TenderFender intake file from a bilingual ISRO NIT PDF.

Text is copied as printed. The only changes are:
  * Hindi (Devanagari) words are dropped; the PDF text layer renders them as broken glyphs.
    A line that is pure English is kept whole. A mixed line keeps only its English part,
    and only if that part has at least two English words (otherwise it is a stray number
    left over from the Hindi text).
  * Table cells are emitted cell by cell, so the criteria and documentary-proof columns
    do not interleave. "Documentary proof:" is a marker added to show which column a line
    came from.
"""
import re
import sys

import pdfplumber

BAD = re.compile(r"[ऀ-ॿ�]|\(cid:\d+\)")
WORD = re.compile(r"[A-Za-z]{2,}")


ENUM = re.compile(r"^(\(?([ivx]{1,4}|[a-z]|\d{1,2})[\.\)]|[A-N]-|Note:?|where,?|\(?or\)?)$", re.I)


def latin_token(tok: str) -> str:
    """English part of a bilingual token such as 'नोट/Note:' or '(या/or)'; '' if none."""
    if not BAD.search(tok):
        return tok
    parts = [p for p in tok.split("/") if p and not BAD.search(p)]
    if not parts:
        return ""
    kept = "/".join(parts)
    if tok.startswith("(") and tok.endswith(")") and not kept.startswith("("):
        kept = "(" + kept
    return kept


CONNECTIVE = re.compile(r"^\(?\s*/?\s*(or|and)\s*\)?$", re.I)


def english_tail(toks: list[str]) -> tuple[str, list[str]]:
    """Split a bilingual line laid out as '[marker] <Hindi> / <English>'.

    Returns (marker, english_tokens): the list marker if the line starts with one, and the
    tokens after the last Hindi word (plus the English half of that word if it is 'हिंदी/English').
    Latin fragments inside the Hindi part (numbers, 'Rs.') are dropped: they repeat the English.
    """
    marker = toks[0] if toks and not BAD.search(toks[0]) and ENUM.match(toks[0]) else ""
    last = max((i for i, t in enumerate(toks) if BAD.search(t)), default=-1)
    tail = toks[last + 1:]
    if last >= 0 and "/" in toks[last]:
        after = toks[last].rsplit("/", 1)[1]
        if after and not BAD.search(after):
            tail = [after] + tail
    if marker and tail and tail[0] == marker:
        marker = ""
    return marker, tail


def clean_cell(cell: str | None, min_words: int = 2) -> list[str]:
    """English lines of a table cell. min_words=0 is for the details table (keeps all Latin tokens)."""
    out: list[str] = []
    carry = ""
    for line in (cell or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if not BAD.search(line):
            kept = line
        elif min_words == 0:
            toks = [latin_token(t) for t in line.split()]
            kept = re.sub(r"^[/|\s]+", "", " ".join(t for t in toks if t).strip())
            if not kept:
                continue
        else:
            marker, tail = english_tail(line.split())
            text = re.sub(r"^[/|\s]+", "", " ".join(tail)).strip()
            if CONNECTIVE.match(text) or (not text and re.search(r"/\s*or\)?", line)):
                carry = (carry + " " + marker + " (or)").strip()
                continue
            if len(WORD.findall(text)) < 1 or (len(WORD.findall(text)) < 2 and not marker and len(text.split()) < 2):
                if marker:
                    carry = (carry + " " + marker).strip()
                continue
            kept = (marker + " " + text).strip()
        if carry:
            kept = f"{carry} {kept}"
            carry = ""
        out.append(kept)
    if carry:
        out.append(carry)
    return out


def is_elig_header(rows) -> bool:
    head = " ".join(c or "" for r in rows[:2] for c in r)
    return "Eligibility Criteria" in head or "following conditions" in head


def details_rows(pdf):
    """English (label, value) rows of the details table, which sits on page 1 or 2."""
    rows, title = [], ""
    for page in pdf.pages[:3]:
        for t in page.find_tables():
            ext = t.extract(x_tolerance=1.5)
            if is_elig_header(ext):
                return rows, title
            for r in ext:
                cells = [" ".join(clean_cell(c, min_words=0)) for c in r]
                cells = [c for c in cells if c]
                if not cells:
                    continue
                rows.append(cells)
                raw = " ".join(x or "" for x in r)
                if not title and len(r) > 1 and re.search(r"Title of work|Name of work", raw, re.I):
                    title = " ".join(clean_cell(r[-1], min_words=2))
    return rows, title


def notice_ref(pdf, det) -> str:
    for cells in det:
        joined = " ".join(cells)
        m = re.search(r"((?:E\s*-\s*)?Notice Inviting Tender Number.*|NIT No\.?.*)", joined)
        if m:
            return m.group(1).strip()
    text = "\n".join((pg.extract_text() or "") for pg in pdf.pages[:2])
    for line in text.splitlines():
        for tok in line.split():
            pass
        m = re.search(r"((?:E-)?Tender Notice No\.?\s*:?.*)", line)
        if m:
            return " ".join(latin_token(t) for t in m.group(1).split() if latin_token(t)).strip()
        m = re.search(r"(File No\.?\s*:.*)", line)
        if m:
            return m.group(1).strip()
    return ""


def section_end_y(page):
    """Top y of the next top-level paragraph ('3.' at the left margin), or None."""
    for w in page.extract_words(x_tolerance=1.5):
        if w["x0"] < 90 and re.match(r"^3\s*[\.\)]$|^3$|^3\.", w["text"]) and not re.match(r"^3\.\d", w["text"]):
            return w["top"]
    return None


def eligibility(pdf) -> list[str]:
    out: list[str] = []
    started = False
    for page in pdf.pages:
        stop_y = section_end_y(page) if started or any(
            is_elig_header(t.extract()) for t in page.find_tables()) else None
        for t in page.find_tables():
            rows = t.extract(x_tolerance=1.5)
            if not rows:
                continue
            if not started:
                if not is_elig_header(rows):
                    continue
                started = True
                stop_y = section_end_y(page)
                if stop_y is not None and stop_y < t.bbox[1]:
                    stop_y = None          # the '3.' found is above the table (e.g. a details row)
            if stop_y is not None and t.bbox[1] >= stop_y:
                return out
            if len(rows) == 1 and sum(1 for c in rows[0] if c) <= 1:
                continue                   # page footer such as 'DOS/ ISRO'
            for r in rows:
                if is_elig_header([r]) or re.search(r"Sl\.?\s*No|S\.No", " ".join(c or "" for c in r)):
                    continue               # repeated column headings
                label = " ".join(clean_cell(r[0], min_words=0)) if len(r) > 0 else ""
                crit = clean_cell(r[1]) if len(r) > 1 else []
                proof = clean_cell(r[2]) if len(r) > 2 else []
                if not (crit or proof):
                    continue
                if label:
                    out.append(label)
                out.extend(crit)
                if proof:
                    out.append("Documentary proof:")
                    out.extend("    " + x for x in proof)
                out.append("")
        if started and stop_y is not None:
            return out
    return out


def main(path: str, url: str, retrieved: str) -> None:
    with pdfplumber.open(path) as pdf:
        det, title = details_rows(pdf)
        elig = eligibility(pdf)
        ref = notice_ref(pdf, det)
    title = re.sub(r"^[/\s]+", "", title)
    keep = []
    for cells in det:
        joined = " | ".join(cells)
        if re.search(r"Estimated cost|Earnest money|Last date|Period during which|downloaded|Period of completion", joined, re.I):
            keep.append(joined)
    print(f"title: {title}")
    print("source_portal: ISRO website (isro.gov.in)")
    print(f"source_url: {url}")
    print(f"source_ref: {ref}")
    print(f"retrieved: {retrieved}")
    print("---")
    for k in keep:
        print(k)
    print()
    print("\n".join(elig).rstrip())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
