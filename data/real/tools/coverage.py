"""Completeness check: English lines that poppler finds in the eligibility section but the intake file lacks."""
import re, subprocess, sys
BAD = re.compile(r"[ऀ-ॿ�]")
norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")).strip()

intake, pdf = sys.argv[1], sys.argv[2]
txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
start = txt.find("Eligibility Criteria")
m = re.search(r"Downloading of tender|Tender documents can be downloaded|tender documents? can be downloaded from", txt[start:], re.I)
region = txt[start: start + (m.start() if m else 20000)]
out = norm(open(intake, encoding="utf-8").read().split("---", 1)[1].replace("Documentary proof:", " "))
missing, total = [], 0
for line in region.splitlines():
    # split layout columns on runs of 3+ spaces, keep English-only segments of 3+ words
    for seg in re.split(r"\s{3,}", line):
        seg = norm(seg)
        if not seg or BAD.search(seg) or len(re.findall(r"[A-Za-z]{2,}", seg)) < 3:
            continue
        if re.search(r"Sl\.? ?No|Eligibility Criteria|Documentary proof|scanned|Self attested|DOS/ ISRO", seg, re.I):
            continue
        total += 1
        w = seg.split()
        grams = [" ".join(w[i:i+3]) for i in range(len(w)-2)]
        hit = sum(g in out for g in grams) / max(1, len(grams))
        if hit < 0.6:
            missing.append(seg)
print(f"{intake.rsplit('/',1)[-1]}: {total-len(missing)}/{total} poppler English segments present")
for s in missing[:12]:
    print("   MISSING:", s[:120])
