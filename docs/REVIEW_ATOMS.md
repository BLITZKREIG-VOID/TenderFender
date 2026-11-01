# Reviewing formalized atoms (real tenders)

The rule compiler turns each tender clause into IR atoms (`field op value`). An atom is only trusted once a human has compared it with the clause's verbatim text and confirmed it. Decisions are saved in `data/real/confirmations.json`:

```json
{"RT-001": {"CL2.1": {"status": "confirmed", "note": "", "at": "2026-11-01T10:00:00+00:00"},
            "CL3.1": {"status": "rejected", "note": "threshold is 3 years, not 5", "at": "..."}}}
```

A tender's `formalization_status` is `confirmed` only when every atom is confirmed.

## 1. Start the app locally (single URL)

```
make pipeline                                   # synthetic tenders T-001..T-003 -> artifacts/
# real tenders (needs PR #28 and the compiler setup from PR #25):
python scripts/import_tender.py data/real/raw/RT-001.txt
RULES_USE_CACHE=0 python -m rules.run --data-dir data/real --tender RT-001 --out-dir artifacts/rules_real --write-cache
npm --prefix ui ci && VITE_API_BASE=/api npm --prefix ui run build
UI_DIST=ui/dist make api                        # http://127.0.0.1:8000
```

There is no `make pipeline-real` target; the `rules.run` line above is PR #28's real mode (it also writes `data/real/tenders/ir_RT-001.json`, the IR cache that the export step reads). Use `PY=.venv/bin/python` as in the Makefile. The API serves `/tender/<id>` from `artifacts/rules/<id>.json` and `artifacts/fused/<id>.json`, so a real tender's page needs both files for that id.

## 2. Open each tender's page

`http://127.0.0.1:8000/tender/T-001`, `.../tender/RT-001`, `.../tender/RT-002`, ... (one page per tender id; the list at `http://127.0.0.1:8000/` links them).

## 3. Compare

In the "Formalized Tender Criteria" list, each atom shows the clause's verbatim text in quotes and the IR formula below it (`field op value`). Check:

- `field` names the thing the clause constrains (turnover, years of experience, registration class, bid days, EMD %).
- `op` matches the wording (`at least` = `>=`, `not more than` = `<=`, `one of` = `in`).
- `value` equals the number or class in the text, with the same units (the clause's own unit, e.g. crore).
- Every clause that was left out appears under "Clauses Not Checked Automatically"; those are never confirmed or exported.

## 4. Confirm or reject

- **Confirm** saves `confirmed` for that atom.
- **Reject** asks for a short note and saves `rejected`. Rejected atoms are not fixed by the app: edit the atom in `data/real/tenders/ir_RT-xxx.json`, rerun `rules.run` for the tender (cache mode), reload the page and confirm it again. If you edit an atom that was already confirmed, reject and re-confirm it so the record is current (decisions are keyed by atom id only).
- If the file cannot be written, the API answers `503 {"error": ..., "code": "confirmations_readonly"}` and the page shows the message; nothing is saved.

Commit `data/real/confirmations.json` to keep the review record.

## 5. Export the confirmed IR

```
python scripts/export_confirmed_ir.py RT-001
```

- Any atom undecided or rejected: exit 1 and the atoms are listed; nothing is written.
- All confirmed: writes `data/real/tenders/ir_RT-001.confirmed.json` (the atoms as a plain array, readable by `rules.ir.load_atoms`, which is what `rules.run` uses for its cache) and `ir_RT-001.confirmed.meta.json` (`"confirmed": true`, time, SHA-256 of the source IR, per-atom decisions). Metadata is a separate file because the cache loader accepts only a bare array of atoms. Re-running on unchanged inputs gives byte-identical files.
- Options: `--ir PATH`, `--confirmations PATH`, `--out PATH`.

## Lambda

The deployed package is read-only. `infra/template.yaml` sets `CONFIRMATIONS_PATH=/tmp/confirmations.json`; on first use the API copies the packaged `data/real/confirmations.json` (included by `scripts/package_lambda.sh` when present) there. Clicks on the live site are ephemeral: they vanish when the execution environment is recycled and are not shared between instances. The committed file is the source of truth; review locally, commit the file, redeploy.

The server is a single process; two API processes sharing one file can overwrite each other's updates.
