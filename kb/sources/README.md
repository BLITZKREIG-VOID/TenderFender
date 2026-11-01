# Local source texts (`kb/sources/`)

`scripts/check_passages.py` verifies that each excerpt in `kb/passages/KB-xxx.md` appears in the official document it cites. It needs the document's text as **plain text that you supply**. The checker has no PDF-parsing dependency and never downloads anything.

## How to save a source text

1. Open the official document at the `source_url` in the passage front matter (the four documents are listed in `kb/passages/README.md`).
2. Copy the document's text (or export it to text with a tool of your choice) and save it as a UTF-8 `.txt` file here. Do not retype or paraphrase: the check is for verbatim text.
3. Make the checker find it, in one of two ways:
   - **By name:** a file whose name starts with the passage id, e.g. `KB-012.txt` or `KB-012.pdf.txt`. One file per passage.
   - **By index:** one file for a whole document, mapped in `kb/sources/index.json`:
     ```json
     {"KB-009": "gfr2017.txt", "KB-010": "gfr2017.txt", "KB-011": "gfr2017.txt"}
     ```
     Paths are relative to `kb/sources/`. An index entry takes precedence over name matching. A passage with no source is reported `UNCHECKED`.
4. Run `make check-passages` (or `python scripts/check_passages.py --kb-dir kb/passages --sources-dir kb/sources`).

## What is compared

Whitespace is normalised, case is folded, quote characters are ignored and dash variants are unified. The passage body is split on `…` / `...` gaps and every fragment must appear in the source, in order. A PDF footnote or page break inside a sentence will make a fragment `FAIL`; save the text so such interruptions are removed or split the fragment in the passage.

Results: `PASS`, `FAIL` (first missing fragment shown), `UNCHECKED` (no source). `UNCHECKED` is not a pass; it is counted separately. Exit code is 1 on any `FAIL`; `--strict` also exits 1 on `UNCHECKED`.

## Git

If a document's licence forbids redistribution, keep it out of git. `.gitignore` ignores everything in `kb/sources/` except this README and `index.json`, so source texts stay local by default. Only force-add a source (`git add -f`) if you have checked its licence allows it.
