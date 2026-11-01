# Real tender eligibility sections (14 tenders)

Collected 2026-11-01 for TenderFender. Each `RT-xxx_*.txt` file follows the intake format: five header lines, `---`, then the eligibility section in the notice's own numbering, with the estimated cost and bid-window rows from the notice's details table above it.

## Source

All 14 are works tenders published by ISRO as open PDF notices on **isro.gov.in** (Government of India, Department of Space), from three centres:

| Centre | Files | Location of works |
|---|---|---|
| VSSC (Vikram Sarabhai Space Centre) | RT-001 to RT-003 | Thiruvananthapuram, Kerala |
| LPSC (Liquid Propulsion Systems Centre) | RT-004 to RT-006 | Valiamala, Kerala |
| SDSC SHAR (Satish Dhawan Space Centre) | RT-007 to RT-014 | Sriharikota, Andhra Pradesh; RT-010 and RT-013 are in Thoothukudi district, Tamil Nadu |

Bids for these tenders are made on ISRO's e-tendering site (tenderwizard.com/ISRO), not CPPP, TN eProcurement or Maharashtra eTenders. That's why `source_portal` is `ISRO website (isro.gov.in)`, not one of the three listed values. **The importer must accept this value**, or you must map it yourself.

`source_url` is the notice PDF itself. Tender dates run from June 2025 to October 2026. Estimated costs range from ₹28.97 lakh to ₹3,547 lakh.

## How the text was copied

The notices are bilingual (Hindi and English) tables. In the PDF text layer the Hindi renders as broken glyphs, so only the **English text** is copied. Words are copied exactly as printed, including the notices' own typos (for example "submision", "preceeding", "charted Accountant"). Line breaks follow the PDF.

Changes from the printed page:

- **Hindi omitted.** Where a line had Hindi and then English, only the English part is kept.
- **Column markers added.** `Documentary proof:` marks text from the table's right-hand column, indented under each row. In RT-012 that column holds amounts on some rows, so those rows are marked `Amount:` instead.
- **Details table rows** are written as `label | value`, with the Hindi removed.
- **30 hand fixes**, logged one per line in `tools/hand_fixes.log`. Each fix either restored English text the extractor missed (a heading line, a note outside the table, a cost row), removed a fragment of the Hindi line, joined a reference split over two lines, or repaired letter-spacing in the PDF text layer (`d u r i n g` → `during`). Nothing was reworded.

## How it was checked

- **No invented text:** every line in every file was matched against an independent extraction of the same PDF (poppler `pdftotext`). Every run of four words had to appear in the PDF. All lines pass, except the `Amount:` labels added in RT-012 and one RT-012 formula line split across a Hindi line. I checked both of those by hand.
- **Nothing missing:** every English line poppler finds in the eligibility section was looked for in the file. The only lines left out are column headings, page footers ("TECH.BID PART-I", "DOS/ ISRO") and the first line of the next section.
- **No personal data:** no contractor names, phone numbers or award results. Each file starts at the details table, below the letterhead phone line.

The scripts are in `tools/` (`extract_elig.py`, `verify_intake.py`, `coverage.py`, `hand_fixes.py`), so the extraction can be rerun.

## Left out

| Notice | Why |
|---|---|
| 4 VSSC notices (E01/09, E01/06, M01/03 of 2026-27; E01/14 of 2025-26) | Scanned images with a poor text layer. OCR errors would break "copied exactly". |
| SDSC SHAR street-lights notice (SHAR/CMD/E/O 2487215/2024-25) | Its table layout lost English words in extraction, such as "Should", "Three" and "One". |

## What the rules contain (for the rule-format decision)

| Rule type | Tenders that have it | Checkable today? |
|---|---|---|
| Similar works (3 / 2 / 1 works worth 40 / 60 / 80% of cost, last 7 years) | 14 / 14 | No: needs a new field (≥3 tenders, so it qualifies) |
| Average annual turnover (usually 30% of cost, last 3 years) | 14 / 14 | Yes: `turnover_cr` (amounts are in lakh, so 1 crore = 100 lakh) |
| Solvency (usually 40% of cost) | 14 / 14 | No: new field candidate |
| No loss in more than 2 of the last 5 years | 14 / 14 | No: new field candidate |
| Bidding capacity formula (AxNx2)-B > estimated cost | 14 / 14 | No: needs bidder data; list as "Not checked automatically" |
| EMD amount | 14 / 14 | Partly: given as ₹ amount, not %. Convert using the estimated cost |
| Bid window (download period and last date) | 14 / 14 | Yes: `bid_days`, from the dates |
| Electrical licence | 1 / 14 (RT-012) | No: "Not checked automatically" |
| Contractor registration class | 0 / 14 | Not used by ISRO |

Two points for the rule checker:
- **Amounts are in lakh, not crore.** 1 crore = 100 lakh.
- **Most thresholds are percentages of the estimated cost**, with the rupee figure printed next to them. Use the printed figure, and check it against the percentage. A mismatch would itself be a finding.
