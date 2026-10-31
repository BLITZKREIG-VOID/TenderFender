# P2 Graph Engine

The graph engine reads five structural files from `data/`: `vendors.csv`,
`directors.csv`, `vendor_directors.csv`, `tenders.csv`, and `bids.csv`. It never
loads `labels.json`; labels belong to the separate evaluation path.

Run it from the repository root with:

```powershell
python -m graph.run
```

The internal graph is a `networkx.MultiDiGraph` so each relationship has a
direction, type, and attributes. Node IDs are the source IDs used for joins.
Only observed vendor attributes are placed in node `features`; identifiers,
names, labels, and screen outputs are not model features.

## Internal relationships

| Direction | Type | Source |
|---|---|---|
| vendor → person | `directed_by` | `vendor_directors.csv` |
| vendor → address | `located_at` | `vendors.csv` |
| vendor → contact | `has_contact` | `vendors.csv` |
| vendor → tender | `submitted_bid` | `bids.csv` |
| tender → buyer | `issued_by` | `tenders.csv` |

Bid-edge features are `bid_amount_cr`, `bid_ratio`, `rank`, `won`, and
`submitted_at`. Duplicate vendor/director links and duplicate vendor/tender
bids are errors. Missing address/contact IDs omit those optional relationships;
missing vendor, director, tender, or buyer references are errors.

## Display graph

`artifacts/graph/graph_output.json` contains the compact graph for the existing
API and UI. It uses only `vendor`, `person`, `address`, and `buyer` nodes, with
`directed_by`, `located_at`, and collapsed `bid_to` edges. Tender and contact
nodes stay internal. Display fields follow SOURCE_OF_TRUTH.md §8.3 and the
existing mock; no shared contract files are changed.

The baseline screens use shared directors, shared addresses, repeated same-
buyer co-bidding with rotating winners, and repeated bids 1–3% above the
winner. The graph builder and screens are data-driven and do not special-case
reserved vendor or tender IDs.

## Explainable vendor scores

`vendor_scores` remains a map of vendor IDs to normalized heuristic scores in
`[0, 1]`; scores are not probabilities. The additive `vendor_explanations`
array gives each evidence-bearing vendor its category, related vendors,
relevant tenders, relationship types, observed resource IDs, buyer and bid
ratios where applicable, plus separate group context.

The baseline allocates up to 100 transparent points: 20 for shared director,
20 for shared address, 30 for same-buyer rotating wins, and 30 for repeated
near-cover bids. Each relationship signal contributes at most once per vendor.
Rotation and cover points scale with distinct evidence tenders (caps 12 and 10
respectively); duplicate events on the same tender do not add points. Group
membership is context only and contributes no additional score. The sum is
capped at 100 and divided by 100. Categories are low (0–0.19), guarded
(0.20–0.39), elevated (0.40–0.69), and high (0.70–1.00). These are initial
interpretable heuristic weights, not calibrated probabilities.

One shared director or address is retained as evidence, but the ownership
ring screen still requires two distinct relationship types for stronger group
evidence. The rotation and cover screens require repeated observations for a
buyer; naturally occurring near-cover bids can therefore produce additional
candidate vendors and false positives. Review the underlying evidence before
treating a score as an investigative conclusion.

GraphSAGE vendor features use log turnover, scaled experience, registration
class one-hot values, log bid count, win rate, mean bid ratio, and mean rank.
Tender features use log estimated value and scaled bid duration. Person,
address, contact, and buyer nodes receive a constant feature and learn through
typed relations. Names, raw IDs, tender titles/dates, ring labels, scenario
metadata, and heuristic scores are excluded. Numeric bid summaries are
computed only from observed bid edges.

Metrics stay in the pending shape unless `scripts/evaluate.py` finishes a
training and held-out evaluation run. The graph builder itself never consumes
evaluation labels.
