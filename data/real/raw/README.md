# Raw real-tender inputs

One text file per tender: `data/real/raw/RT-001.txt`, `RT-002.txt`, ... (the file name is the `tender_id`, pattern `^RT-\d{3}$`).
Everything in this directory except this README is gitignored. Convert a file with:

```
python scripts/import_tender.py data/real/raw/RT-001.txt
```

## Format

```
title: <copied from the portal>
source_portal: CPPP | <state portal name>
source_url: <tender page URL>
source_ref: <portal tender id>
retrieved: YYYY-MM-DD
---
<eligibility / qualification section pasted verbatim, keeping the document's own clause numbers>
```

- The five header lines are all required. Header and body are separated by a line containing only `---`.
- The body is the eligibility / qualification section only, copied verbatim, with the document's own clause numbers (`4.2`, `(b)`, `a)` ...). Do not reword, translate or tidy it.
- Store only short excerpts with attribution (the header). No whole documents and no bidder personal data (names of bidders, directors, contact details).
- Use `retrieved` for the date you copied the text from the portal.
