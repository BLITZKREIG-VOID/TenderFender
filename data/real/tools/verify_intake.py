"""Check every content line of an intake file against an independent text extraction (poppler pdftotext).

A line passes if every run of 4 consecutive words in it also appears, in order, in the poppler text
(lines shorter than 4 words: the whole line must appear). Hindi-free comparison; whitespace normalised.
"""
import re, subprocess, sys

ENUM = re.compile(r"^(\(?([ivx]{1,4}|[a-z]|\d{1,2})[\.\)]|[A-N]-|Note:?|where,?|\(?or\)?)$", re.I)
norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")).strip()

def poppler_words(pdf):
    txt = subprocess.run(["pdftotext", "-raw", pdf, "-"], capture_output=True, text=True).stdout
    txt2 = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
    return norm(txt), norm(txt2)

def main(intake, pdf):
    raw, dflt = poppler_words(pdf)
    lines = open(intake, encoding="utf-8").read().split("---", 1)[1].splitlines()
    bad, n = [], 0
    for line in lines:
        s = line.strip()
        if not s or " | " in s:          # skip blank lines and the details-table rows (checked by hand)
            continue
        s = s.removeprefix("Documentary proof:").strip()
        words = s.split()
        while words and ENUM.match(words[0]):
            words.pop(0)
        if not words:
            continue
        n += 1
        k = 4
        grams = [norm(" ".join(words[i:i+k])) for i in range(max(1, len(words)-k+1))]
        miss = [g for g in grams if g not in raw and g not in dflt]
        if miss:
            bad.append((line, miss[:2]))
    print(f"{intake.rsplit('/',1)[-1]}: {n-len(bad)}/{n} lines matched")
    for line, miss in bad:
        print("   NOMATCH:", line[:110], "| missing:", miss)

main(sys.argv[1], sys.argv[2])
