"""Hand fixes to the raw extractions, each an exact replacement checked against the PDF (poppler text).

Every fix either restores English text the extractor missed, removes a fragment left over from the
Hindi text, or repairs letter-spacing in the PDF text layer. Nothing is reworded.
Fails loudly if any target text is not found exactly once.
"""
import sys
from pathlib import Path

INTAKE = Path(sys.argv[1])
LOG = []

SDSC_INTRO = "The Main Bidder shall fulfill the following conditions."

FIXES = {
    "c09": [("source_ref: Tender Notice No : LPSC-V/CMD/CS",
             "source_ref: e-Tender Notice No : LPSC-V/CMD/CS/01/1176/C/TE-06/2026-27 Dated 10.07.2026",
             "reference was split over two lines in the PDF")],
    "c11": [("source_ref: Tender Notice No : LPSC-V/CMD/CS",
             "source_ref: e-Tender Notice No : LPSC-V/CMD/CS/01/1175/C/TE-07/2026-27 Dated 16.07.2026",
             "reference was split over two lines in the PDF")],
    "c16": [("source_ref: Tender Notice No : LPSC-V CMD/CS/01",
             "source_ref: e-Tender Notice No : LPSC-V/CMD/CS/01/1120/C/TE-010/2025-26 dated 06.06.2025",
             "reference was split over two lines in the PDF")],
    "c12": [
        ("source_ref: E - Notice Inviting Tender Number 2687204 / 2026-27 SHAR / CMD / E /",
         "source_ref: E - Notice Inviting Tender Number SHAR / CMD / E / D 2687204 / 2026-27",
         "reference words were out of order (cell mixes Hindi and English)"),
        ("    i. ii. i. Certified copy of work orders and completion",
         "    i. Certified copy of work orders and completion",
         "stray list markers from the Hindi lines"),
        ("than 40% of the estimated cost i.e.:\n(or)\nDocumentary proof:\n    ₹ 94.09 Lakhs",
         "than 40% of the estimated cost i.e.:\nAmount: ₹ 94.09 Lakhs\n(or)",
         "third column holds the amount here, not documentary proof"),
        ("60% of the estimated cost i.e.:\n(or)\nDocumentary proof:\n    ₹ 141.14 Lakhs",
         "60% of the estimated cost i.e.:\nAmount: ₹ 141.14 Lakhs\n(or)",
         "third column holds the amount here, not documentary proof"),
        ("of the estimated cost. i.e.:\nDocumentary proof:\n    ₹ 188.18 Lakhs\n",
         "of the estimated cost. i.e.:\nAmount: ₹ 188.18 Lakhs\n"
         "i. Note: Similar Works means Electrical Works : Internal electrification (or) Electrical works for Construction of\n"
         "building\"\n"
         "ii. The value of executed works shall be brought to current costing level by enhancing the actual value of work at\n"
         "simple rate of 7% per annum, calculated from the date of completion to last date of submission of bids\n"
         "iii. Work executed as sub-contract or joint venture will not merit for eligibility / evaluation.\n",
         "amount column label; Note block sits outside the table and was missed"),
        ("ending 31st March of preceeding year.\nDocumentary proof:\n    ₹ 70.57 Lakhs",
         "ending 31st March of preceeding year.\nAmount: ₹ 70.57 Lakhs",
         "third column holds the amount here, not documentary proof"),
        ("(1) ₹ 94.09 Lakhs)\n", "", "fragment of the Hindi line; the English line below states the same amount"),
        ("(AxNx2)-B, where, - 5 A- ", "(AxNx2)-B, where, A- ", "fragment of the Hindi line"),
        ("work in progress. - ‘N’ B- ", "work in progress. B- ", "fragment of the Hindi line"),
        ("current price level. - N- ", "current price level. N- ", "fragment of the Hindi line"),
        ("    ii. (ii)\n", "    ii.\n", "duplicated marker from the Hindi line"),
    ],
    "c05": [
        ("these works d u r i n g t he", "these works during the", "letter-spacing in the PDF text layer"),
        ("s t i p u l a t ed period of completion", "stipulated period of completion", "letter-spacing in the PDF text layer"),
    ],
    "c14": [("__END__",
             "Important Note: Bidders may note that above criteria are only minimum qualifying criteria. For\n"
             "obtaining the required marks in qualifying criteria of stage 2 evaluation, bidders may refer criteria in\n"
             "section A-4 (evaluation part) and submit the required qualifying documents for Financial Strength\n"
             "and Experience in similar class etc.",
             "note printed after the table was missed")],
    "c17": [("__END__",
             "Important Note: Bidders may note that above criteria are only minimum qualifying\n"
             "criteria. For obtaining the required qualifying marks in Stage 2 evaluation, bidder may\n"
             "refer to criteria in Section A-4 (evaluation part) and submit the required qualifying\n"
             "documents for Financial Strength and Experience in similar class etc.",
             "note printed after the table was missed")],
}
for c in ("c04", "c05", "c06", "c08", "c10"):
    FIXES.setdefault(c, []).insert(0, ("__INTRO__", SDSC_INTRO, "heading line above the table was missed"))


def apply(code: str, text: str) -> str:
    for old, new, why in FIXES.get(code, []):
        if old == "__END__":
            text = text.rstrip("\n") + "\n\n" + new + "\n"
        elif old == "__INTRO__":
            head, body = text.split("---\n", 1)
            details, rest = body.split("\n\n", 1)
            text = f"{head}---\n{details}\n\n{new}\n\n{rest}"
        else:
            n = text.count(old)
            if n != 1:
                raise SystemExit(f"{code}: expected 1 match, found {n}: {old[:60]!r}")
            text = text.replace(old, new)
        LOG.append(f"{code}: {why}")
    return text


for f in sorted(INTAKE.glob("c*.txt")):
    f.write_text(apply(f.stem, f.read_text(encoding="utf-8")), encoding="utf-8")
print("\n".join(LOG))
print(f"{len(LOG)} fixes applied")
