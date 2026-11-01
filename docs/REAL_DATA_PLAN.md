# Real-data plan (Phase 3)

Status: research and plan only. No code, no data and no schema changes in this PR.

Evidence rules used in this document:

- Everything marked **verified** was seen on 2026-11-01 by fetching the named URL with
  `curl -sSL --max-time 20 -A 'TenderFender-research (contact: repo owner)'`.
- Everything marked **unverified** was not observed. Nothing unverified is relied on.
- Only `robots.txt`, portal home pages and terms / policy / copyright pages were fetched. No search
  or servlet endpoint was called. No tender document, bid PDF or CCI order was downloaded.
  Nothing was saved under `data/`.
- Quotes are copied from the HTML text of the page. HTML tags were stripped; whitespace was
  collapsed. They are not legal advice and the user must read the pages (see the checklist).

## 1. Per-source findings

### 1.1 CPPP (`eprocure.gov.in`)

| Item | Finding |
|---|---|
| Fetched pages | `https://eprocure.gov.in/` (200; meta-refresh to `/cppp`), `https://eprocure.gov.in/cppp/` (200; a JavaScript single-page app titled "GeM-CPPP", HTML contains no tender content) |
| Fields available | **unverified.** The pages fetched are an app shell only. No title, NIT, award result or bidder list was seen. The GeM home page has a menu item "CPPP tenders" and "GeM-CPPP" (https://gem.gov.in/), which only shows that CPPP is linked from GeM |
| Public without login? CAPTCHA? | **unverified** for both. The shell is public; the data pages were not requested |
| robots.txt | `https://eprocure.gov.in/robots.txt` -> HTTP 404 (Apache "Not Found" page). `https://eprocure.gov.in/cppp/robots.txt` -> HTTP 200, `text/plain`, full body: `User-agent: *` / `Disallow:` (empty, i.e. nothing disallowed) |
| Terms / copyright | **not found.** No terms, policy or copyright link exists in the static HTML of `/` or `/cppp/` (the app is JavaScript-rendered). The URL is unknown, so none is guessed |
| Personal data | **unverified** (no tender seen). Expect signatory and contact names in tender documents; handling in the table at the end of this section |
| Closed tenders with results public? | **unverified** |

### 1.2 GeM (`gem.gov.in`, `bidplus.gem.gov.in`)

| Item | Finding |
|---|---|
| Fetched pages | `https://gem.gov.in/` (200), `https://gem.gov.in/terms-of-use` (200), `https://gem.gov.in/support/terms_conditions` (200), `https://gem.gov.in/page/gtc` (200), `https://gem.gov.in/websitePolicies` (200). `https://bidplus.gem.gov.in/` was requested with HEAD only to learn the redirect: 303 to `https://bidplus.gem.gov.in/bidlists` (a bid listing, not fetched) |
| Fields available | **unverified** as to data. Menu labels seen on the home page (https://gem.gov.in/): "Bids", "Ongoing Bids", "Bid/RA Status", "View Contracts", "CPPP tenders". Labels are not evidence that an eligibility section, award result or bidder list is readable. `bidlists` / bid documents were not fetched |
| Public without login? CAPTCHA? | **unverified.** The home page HTML contains "captcha" once, only as a CSS selector (`#captchaimg{`); that says nothing about bid pages |
| robots.txt | `https://gem.gov.in/robots.txt` -> HTTP 200. Relevant lines verbatim: `User-agent: *` / `Disallow: ` / `Disallow: /cgi-bin/` / `Disallow: /resources/` / `Sitemap: https://gem.gov.in/sitemap.xml`. `https://bidplus.gem.gov.in/robots.txt` -> HTTP 200. Verbatim: `User-agent: *` / `Disallow: /resources/` / `Disallow: /bg_emd/epbgservice/CallBG_Performance_Status` / `Disallow: /bg_emd/epbgservice/PBGIntimation` / `Disallow: /bg_emd/epbgservice/AddSellerIssuinginfo`. GeM's published GTC PDFs are linked from `assets-bg.gem.gov.in/resources/...` (seen on https://gem.gov.in/terms-of-use); where bid documents are hosted, and whether the `/resources/` rule covers them, is **unverified** |
| Terms / copyright | https://gem.gov.in/websitePolicies, section "Copyright Policy for GeM": "Contents of this website may not be reproduced partially or fully without due permission in writing in advance from the GeM SPV, Ministry of Commerce & Industries, Government of India. However, the content must be reproduced accurately and not used in a derogatory manner or in a misleading context. Wherever the material is published or issued to others, the source must be prominently acknowledged." The pages https://gem.gov.in/terms-of-use and https://gem.gov.in/support/terms_conditions only list GTC documents (HTML/PDF links); the GTC PDFs themselves were not downloaded and not read |
| Personal data | **unverified** for bid pages. Privacy policy (https://gem.gov.in/websitePolicies) states: "We do not sell any personally identifiable information volunteered on the GeM to any third party (public or private)." |
| Closed tenders with results public? | **unverified** ("Bid/RA Status", "View Contracts" exist as menu labels only) |

### 1.3 Karnataka (`kppp.karnataka.gov.in`)

| Item | Finding |
|---|---|
| Fetched pages | `https://kppp.karnataka.gov.in/` -> 200, titled "KPPP Portal", an Angular app shell (references `main.js`, `polyfills.js`); no tender content in the HTML |
| Fields available | **unverified** (no data page seen) |
| Public without login? CAPTCHA? | **unverified.** The shell's inline script contains URL-path checks for `/general`, `/user`, `/supplier`, `/tender` etc.; their meaning was not investigated |
| robots.txt | not reachable: `https://kppp.karnataka.gov.in/robots.txt` -> HTTP 403 Forbidden (empty body, `Content-Type: text/html; charset=iso-8859-1`) with the research User-Agent. Whether other clients get a different answer is unverified; no workaround was attempted |
| Terms / copyright | **not found.** No link in the static HTML (JavaScript-rendered) |
| Personal data | **unverified** |
| Closed tenders with results public? | **unverified** |

### 1.4 Maharashtra (`mahatenders.gov.in`) - NIC GePNIC platform

| Item | Finding |
|---|---|
| Fetched pages | `https://mahatenders.gov.in/` (200; meta-refresh to `/nicgep/app`), `https://mahatenders.gov.in/nicgep/app` (200, portal home), `https://mahatenders.gov.in/nicgep/app?page=Disclaimer&service=page` (200, "Portal policies") |
| Fields available | The home page menu (https://mahatenders.gov.in/nicgep/app) has links labelled "Active Tenders", "Tenders by Closing Date", "Results of Tenders", "Tenders in Archive", "Tenders Status", "Cancelled/Retendered", "Debarment List". Contents behind them: **unverified** (not fetched: they are search/list endpoints). Eligibility-section availability: **unverified** |
| Public without login? CAPTCHA? | Home page and policy page are public (verified). The word "captcha" does not occur in the home page HTML. List pages: **unverified** |
| robots.txt | `https://mahatenders.gov.in/robots.txt` -> HTTP 200, `text/plain`, verbatim: `User-agent: *` / `Disallow: /`. **All automated crawling is disallowed.** User-placed files only |
| Terms / copyright | https://mahatenders.gov.in/nicgep/app?page=Disclaimer&service=page, "Copyright Policy": "Material featured on this Portal maybe reproduced free of charge after taking proper permission from the respective Organisation / Department. However, the material has to be reproduced accurately and not to be used in a derogatory manner or in a misleading context and as per the guidelines provided by the respective Government / Department. Wherever the material is being published or issued to others, the source must be prominently acknowledged." Same page: "the Tenders are owned, published and maintained by the concerned Government Departments." |
| Personal data | **unverified** in tender documents. Policy page: "Users are hereby informed not to use, display, upload, modify, publish, transmit, update, share or store any information that: ... discloses sensitive personal information of other person or to which the user does not have any right to" |
| Closed tenders with results public? | **unverified.** Menu labels "Results of Tenders" and "Tenders in Archive" exist; contents were not opened |

### 1.5 Tamil Nadu (`tntenders.gov.in`) - NIC GePNIC platform

| Item | Finding |
|---|---|
| Fetched pages | `https://tntenders.gov.in/` (200; meta-refresh to `/nicgep/app`), `https://tntenders.gov.in/nicgep/app` (200), `https://tntenders.gov.in/nicgep/app?page=Disclaimer&service=page` (200) |
| Fields available | Same menu labels as Maharashtra ("Active Tenders", "Results of Tenders", "Tenders in Archive", "Tenders Status", "Cancelled/Retendered") on https://tntenders.gov.in/nicgep/app. Contents **unverified** |
| Public without login? CAPTCHA? | Home and policy pages public (verified). "captcha" does not occur in the home page HTML. List pages **unverified** |
| robots.txt | `https://tntenders.gov.in/robots.txt` -> HTTP 404 (Apache "Not Found" page). No crawl rules are published; this is not a permission |
| Terms / copyright | https://tntenders.gov.in/nicgep/app?page=Disclaimer&service=page, "Copyright Policy": "Material featured on this Portal maybe reproduced free of charge after taking proper permission from the respective Organisation / Department. However, the material has to be reproduced accurately and not to be used in a derogatory manner or in a misleading context and as per the guidelines provided by the respective Government / Department. Wherever the material is being published or issued to others, the source must be prominently acknowledged." Same page: "the Tenders are owned, published and maintained by the concerned Government Departments." |
| Personal data | **unverified** in tender documents (same policy text as Maharashtra) |
| Closed tenders with results public? | **unverified** (menu labels only) |

### 1.6 CCI (`cci.gov.in`) - reference ground truth only

| Item | Finding |
|---|---|
| Fetched pages | `https://cci.gov.in/` (200), `/contents/disclaimer`, `/contents/copyright`, `/contents/termncond`, `/contents/privacypolicy` (all 200). The home page links to `https://cci.gov.in/antitrust/orders`; that page and any order were **not** fetched |
| Fields available | Order content, parties and findings: **unverified** (no order opened, by design) |
| Public without login? CAPTCHA? | Home and policy pages public (verified). Orders page: **unverified** |
| robots.txt | `https://cci.gov.in/robots.txt` -> HTTP 200, verbatim: `User-agent: *` / `Disallow: /images/combination_pre_filling_form_consultations/` / `Disallow: /images/internship/` / `Disallow: /public/images/combination_pre_filling_form_consultations/` / `Disallow: /public/images/internship/` / `Disallow: /images/stakeholdersconsultations/` / `Disallow: /public/images/stakeholdersconsultations/`. Whether `/antitrust/orders` and where order PDFs live fall under these rules: **unverified** |
| Terms / copyright | https://cci.gov.in/contents/copyright: "Material featured on Competition Commission of India (CCI) may be reproduced free of charge after taking proper permission by sending a mail to us. However, the material has to be reproduced accurately and not to be used in a derogatory manner or in a misleading context. Wherever the material is being published or issued to others, the source must be prominently acknowledged." Also https://cci.gov.in/contents/termncond: "the same should not be construed as a statement of law or used for any legal purposes." |
| Personal data | **unverified** in orders. Orders about bid rigging may name individuals (officers, directors). Not imported |
| Closed tenders with results public? | Not applicable (not a tender source) |

### 1.7 Personal data handling (all sources)

Proposal, for the user to confirm:

1. Store only the verbatim eligibility clauses of a tender (the text the rules check).
2. Never import bidder personal data: no director names, signatory names, phone numbers, e-mail
   addresses, DIN, PAN, Aadhaar. If a clause quoted for eligibility contains such a string, set
   `needs_review: true` and redact it by hand before commit. Redaction must be marked in the clause
   (e.g. `[redacted]`); never paraphrase silently.
3. CCI orders are reference only: read by a human to decide which tenders / firms are worth
   examining. They are not imported, not copied into the repo and not parsed by code.
4. Raw files in `data/real/raw/` are never committed (section 3).
5. Output language remains "risk indicators". Nothing real is labelled corrupt or guilty.

## 2. What you must check (STOP 1)

Nothing below has been decided by this plan. Please confirm each item.

- [ ] Read the terms pages linked above for each source you want to use. Every reuse clause
  seen asks for prior permission (GeM: "due permission in writing in advance"; NIC portals and
  CCI: "after taking proper permission"). Decide whether short verbatim eligibility excerpts for
  analysis fall inside, and whether you want to request permission first.
- [ ] Decide on the permission route: GeM SPV, the concerned department (NIC portals: the tender is
  "owned, published and maintained by the concerned Government Departments"), or CCI by mail.
- [ ] `mahatenders.gov.in` robots.txt says `Disallow: /`. Confirm we only use files you download
  by hand, never a script.
- [ ] `kppp.karnataka.gov.in` robots.txt answered 403 to our User-Agent. Open it in your browser and
  tell us what you see.
- [ ] CPPP: robots.txt differs between `/robots.txt` (404) and `/cppp/robots.txt` (empty
  Disallow). Find the CPPP terms page (not found by us) and read it.
- [ ] For each tender you pick, confirm in your browser: public without login, any CAPTCHA, whether
  the NIT / bid document is downloadable and has an eligibility section, whether a closed tender
  shows award results and bidder names. All of these are currently **unverified**.
- [ ] Confirm the personal-data rule in 1.7 and the clause-only storage.
- [ ] Confirm that CCI orders are used only as reference.
- [ ] Confirm the `data/real/raw/` gitignore decision (section 3).
- [ ] Pick the tender(s) to start with (suggest 1 to 3) and place the PDFs / text under
  `data/real/raw/`. We do not select or fetch them.

## 3. Proposed file layout

Reuses the existing tender format (`contracts/schemas/tender.json`, SoT section 7), whose current
required fields are `tender_id` (`^T-\d{3}$`), `title` and `clauses[]` of `{clause_id (^CL\d+$), text}`,
with `additionalProperties: false` at both levels.

```text
data/real/raw/            user-placed PDFs / text; NOT committed (see decision)
data/real/tenders/RT-001.json   one file per real tender, committed
```

**Gitignore decision (proposed):** add `data/real/raw/` to `.gitignore` in Phase 4. Reasons: the
sources' terms require permission to reproduce whole documents, and whole documents may contain
personal data. Committed files hold only the eligibility clauses (section 1.7). The user decides.

Fields of `data/real/tenders/RT-xxx.json`:

| Field | Meaning |
|---|---|
| `tender_id` | `RT-\d{3}` |
| `title` | as printed on the source |
| `source_url` | page the user took the document from |
| `retrieved` | date the user retrieved it (ISO date) |
| `source_ref` | the portal's own tender id, as printed |
| `clauses` | `[{clause_id, text, needs_review?}]`, `text` copied verbatim from the eligibility section |

Schema consequence (Phase 4, not done here): the existing `tender.json` rejects these files
(`tender_id` pattern `^T-\d{3}$` and `additionalProperties: false` reject `RT-` ids and the extra
fields). Phase 4 needs either a new `contracts/schemas/real_tender.json` or a widened tender schema,
with `contracts/examples`, `mocks`, `docs/CONTRACT_CHANGES.md` and an SoT section 13 entry in the same
commit, keeping `make validate-contracts` green. A new schema is the safer choice: the synthetic
`T-` schema and its 50 contract checks stay untouched. Note also that anything that globs
`data/tenders/T-*.json` or assumes the `T-` pattern will not see `data/real/tenders/`.

ILLUSTRATIVE skeleton (placeholders only, not a real tender):

```json
{
  "tender_id": "RT-001",
  "title": "<title as printed on the source>",
  "source_url": "<page URL the user took the document from>",
  "retrieved": "<YYYY-MM-DD>",
  "source_ref": "<portal tender id as printed>",
  "clauses": [
    {"clause_id": "CL1", "text": "<copied verbatim>"},
    {"clause_id": "CL2", "text": "<copied verbatim>", "needs_review": true}
  ]
}
```

## 4. Recommendation (recommendation, not a decision)

**Start with CPPP (`eprocure.gov.in/cppp`), tenders chosen and downloaded by the user.** Why:
`/cppp/robots.txt` is the only one of the tender portals with an explicit allow-all rule (empty
`Disallow:`); `mahatenders.gov.in` disallows everything and `kppp.karnataka.gov.in` answers 403
to us. CPPP carries central-government tenders, which keeps the first sample to one platform and
one document style. Caveats: the CPPP terms page was not found, and its data fields, login and
CAPTCHA behaviour are unverified. If CPPP shows no downloadable NIT with an eligibility section,
fall back to a NIC portal (`tntenders.gov.in`: robots.txt 404, so no crawl rules are published,
and it shares the Maharashtra policy text), with the same hand-download rule.

**For the later network check** (shared-director / bidder-overlap indicators over real data) we would
need, per tender, the award result and the bidder list: bidder legal-entity names and the awarded
bidder. NIC portals label a "Results of Tenders" page and GeM labels "Bid/RA Status" and "View
Contracts", but whether they show bidder names is unverified. Director linkage needs a source
outside the tender portals (company registry data); none was researched here. CCI bid-rigging
orders would be the ground truth for validating the check: a human reads published orders, notes
which tenders and firms were found to have colluded, and we test whether our indicators would flag
them. Nothing from an order is imported (section 1.7). Open question for the user: whether such
reference work is within the sources' terms (section 2).

## 5. Phase 4: compiled vs not-checked table


## STOP 1 decision (2026-11-01)

1. Sources: a mix of CPPP (eprocure.gov.in) and state portals.
2. The user has read the portal terms. We store only short verbatim eligibility excerpts with attribution; no whole documents and no bidder personal data.
3. The user provides 10-12 text files with the eligibility section pasted in, under `data/real/raw/`. `data/real/raw/*` is gitignored except its README.
4. Rule-format widening (`rules/ir.py`) waits for the real files; it is not widened in the prep work.

## STOP 1 revision (2026-11-01): ISRO

1. **Source switch:** Switched from CPPP/state portals to ISRO public notice PDFs on `isro.gov.in` (Government of India, Department of Space).
2. **Verbatim Copyright Policy quote:** ISRO's Copyright Policy (`https://www.isro.gov.in/Copyright_Policy.html`) states:
   > "Material featured on this site belongs to the DOS/ISRO and the same may be reproduced free of charge in any format or media without requiring specific permission. This is subject to the material being reproduced accurately and not being used in a derogatory manner or in a misleading context."
   and:
   > "Wherever the material is being published or issued to others, the source must be prominently acknowledged".
3. **Robots / access:** `isro.gov.in` has no robots.txt (HTTP 404). `tenderwizard.com` is not used.
4. **Neutral framing & attribution:** Every real-tender page and API response states that excerpts are reproduced from DOS/ISRO public notices, with the notice URL. It also states the checks are automated and may be wrong, and that findings are risk indicators for human review, not a judgement on ISRO or any bidder. No ranking or "worst tenders" list anywhere.
5. **Provenance:** Intake scripts and conversion tools are committed under `data/real/tools/`, with source documentation in `data/real/tools/SOURCE_README.md`. Raw `.txt` files remain gitignored under `data/real/raw/`.

## 6. Phase 4: compiled vs not-checked table

| Tender ID | Centre / Location | Total Clauses | Expressible Clauses | Not Checked Clauses (Reason) | Needs Review Clauses | Amount Mismatch Findings |
|---|---|---|---|---|---|---|
| RT-001 | VSSC, Thiruvananthapuram | 10 | 6 (CL1, CL5, CL6, CL7, CL8, CL9) | 4 (CL2: completion period, CL3: download window, CL4: receipt date, CL10: bidding capacity formula) | 5 | 0 (all printed figures match computed percentages within 0.004L) |
| RT-002 | VSSC, Thiruvananthapuram | 10 | 6 (CL1, CL5, CL6, CL7, CL8, CL9) | 4 (CL2: completion period, CL3: download window, CL4: receipt date, CL10: bidding capacity formula) | 5 | 0 (all printed figures match computed percentages within 0.004L) |
| RT-003 | VSSC, Thiruvananthapuram | 10 | 6 (CL1, CL5, CL6, CL7, CL8, CL9) | 4 (CL2: completion period, CL3: download window, CL4: receipt date, CL10: bidding capacity formula) | 5 | 0 (all printed figures match computed percentages within 0.005L) |
| RT-004 | LPSC, Valiamala | 11 | 6 (CL1, CL6, CL7, CL8, CL9, CL10) | 5 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL11: bidding capacity formula) | 7 | 0 (printed figures match computed percentages within 0.005L) |
| RT-005 | LPSC, Valiamala | 11 | 6 (CL1, CL6, CL7, CL8, CL9, CL10) | 5 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL11: bidding capacity formula) | 6 | 0 (printed figures match computed percentages within 0.005L) |
| RT-006 | LPSC, Valiamala | 11 | 6 (CL1, CL6, CL7, CL8, CL9, CL10) | 5 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL11: bidding capacity formula) | 6 | 0 (printed figures match computed percentages within 0.000L) |
| RT-007 | SDSC SHAR, Sriharikota | 12 | 6 (CL1, CL6, CL7, CL9, CL10, CL11) | 6 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL8: definition text, CL12: bidding capacity formula) | 10 | 0 (printed figures match computed percentages within 0.000L) |
| RT-008 | SDSC SHAR, Sriharikota | 12 | 6 (CL1, CL6, CL7, CL9, CL10, CL11) | 6 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL8: definition text, CL12: bidding capacity formula) | 10 | 0 (printed figures match computed percentages within 0.000L) |
| RT-009 | SDSC SHAR, Sriharikota | 12 | 6 (CL1, CL6, CL7, CL9, CL10, CL11) | 6 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL8: definition text, CL12: bidding capacity formula) | 10 | 0 (printed figures match computed percentages within 0.000L) |
| RT-010 | SDSC SHAR, Kulasekarapattinam / Thoothukudi | 12 | 6 (CL1, CL6, CL7, CL9, CL10, CL11) | 6 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL8: definition text, CL12: bidding capacity formula) | 10 | 0 (printed figures match computed percentages within 0.000L) |
| RT-011 | SDSC SHAR, Sriharikota | 12 | 6 (CL1, CL6, CL7, CL9, CL10, CL11) | 6 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL8: definition text, CL12: bidding capacity formula) | 10 | 0 (printed figures match computed percentages within 0.000L) |
| RT-012 | SDSC SHAR, Sriharikota | 11 | 6 (CL1, CL6, CL7, CL9, CL10, CL11) | 5 (CL2: completion period, CL3: request period, CL4: download period, CL5: receipt date, CL8: electrical license requirement) | 7 | 0 (printed figures match computed percentages within 0.001L) |
| RT-013 | SDSC SHAR, Kulasekarapattinam / Thoothukudi | 5 | 5 (CL1, CL2, CL3, CL4, CL5) | 0 (all clauses expressible) | 4 | 0 (amounts match percentage thresholds within 0.000L) |
| RT-014 | SDSC SHAR, Sriharikota | 4 | 4 (CL1, CL2, CL3, CL4) | 0 (all clauses expressible) | 2 | 0 (amounts match percentage thresholds within 0.000L) |

### Amount Mismatch Analysis

The deterministic `amount_mismatch` check inspects every clause that states both a percentage of estimated cost and a printed rupee amount in Lakhs (or EMD). The configured tolerance is:
- Relative tolerance: 0.5% (`0.005`)
- Absolute rounding tolerance: ₹0.01 Lakh (`1,000` INR)

Across all 14 tenders, every printed figure in the official ISRO notices matches the computed percentage of estimated cost within normal rounding (maximum discrepancy observed was ₹0.005 Lakh = ₹500 on multi-crore works, well below the ₹0.01 Lakh threshold). Consequently, no tender has an erroneous printed figure, yielding 0 `amount_mismatch` findings.
