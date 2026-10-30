"""
TenderFender – Synthetic Data Verifier (P2)
===========================================
Validates all six generated datasets against the SOURCE_OF_TRUTH.md
section 7 contracts and the planted-scenario constraints.

Raises ``VerificationError`` (a subclass of ValueError) listing all failures.
Callers must call ``verify_all()`` before writing any file.
"""

from __future__ import annotations

from typing import Any

from synth.generate import (
    qualifies_t002,
    qualifies_t003,
    R1_VENDOR_IDS,
    R1_SHARED_DIRECTOR,
    R1_SHARED_ADDRESS,
    R2_VENDOR_IDS,
    R2_ROTATION_TENDER_COUNT,
    R3_TENDER_COUNT,
    R3_OVERLAP_FIRST,
    R3_OVERLAP_LAST,
    T003_MIN_QUALIFIERS,
    T003_MAX_QUALIFIERS,
    _vid,
    _pid,
    _aid,
    _tid,
)


class VerificationError(ValueError):
    """Raised when one or more validation checks fail."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        joined = "\n".join(f"  [{i+1}] {e}" for i, e in enumerate(errors))
        super().__init__(f"Verification failed with {len(errors)} error(s):\n{joined}")


# ---------------------------------------------------------------------------
# Column contracts (SOURCE_OF_TRUTH.md §7)
# ---------------------------------------------------------------------------

VENDORS_COLUMNS = {
    "vendor_id", "name", "turnover_cr", "years_experience",
    "registration_class", "address_id", "contact_id",
}
DIRECTORS_COLUMNS = {"person_id", "name"}
VENDOR_DIRECTORS_COLUMNS = {"vendor_id", "person_id"}
TENDERS_COLUMNS = {
    "tender_id", "buyer_id", "title", "estimated_value_cr",
    "bid_days", "open_date",
}
BIDS_COLUMNS = {
    "tender_id", "vendor_id", "bid_amount_cr", "bid_ratio",
    "rank", "won", "submitted_at",
}
LABELS_KEYS = {"rings", "vendor_labels", "planted_type"}
LABELS_RING_KEYS = {"ring_id", "vendor_ids", "type"}

VALID_REG_CLASSES = {"MSE", "Class-A", "Class-B", "Class-C"}
VALID_RING_TYPES = {"shell_ring", "rotation", "cover"}
VALID_PLANTED_TYPES = {"shell_ring", "rotation", "cover", "none"}
VALID_SEVERITIES = {0, 1}

# Feature columns that must never appear in labels-like positions
# (not enforced here since labels are a separate file, but we verify
#  that the CSV column sets contain no 'label', 'ring', 'planted' etc.)
PROHIBITED_FEATURE_NAMES = {"label", "ring_id", "planted_type", "flagged"}


def _check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


# ---------------------------------------------------------------------------
# Schema validators
# ---------------------------------------------------------------------------

def _validate_columns(
    errors: list[str],
    rows: list[dict[str, Any]],
    expected: set[str],
    table: str,
) -> None:
    if not rows:
        errors.append(f"{table}: table is empty")
        return
    actual = set(rows[0].keys())
    extra = actual - expected
    missing = expected - actual
    if extra:
        errors.append(f"{table}: unexpected columns {sorted(extra)}")
    if missing:
        errors.append(f"{table}: missing columns {sorted(missing)}")

    # Ensure no prohibited feature names leaked in
    for col in actual:
        if col in PROHIBITED_FEATURE_NAMES:
            errors.append(f"{table}: column '{col}' is a prohibited feature name")


def validate_vendors_schema(errors: list[str], vendors: list[dict[str, Any]]) -> None:
    _validate_columns(errors, vendors, VENDORS_COLUMNS, "vendors")


def validate_directors_schema(errors: list[str], directors: list[dict[str, Any]]) -> None:
    _validate_columns(errors, directors, DIRECTORS_COLUMNS, "directors")


def validate_vendor_directors_schema(
    errors: list[str], vd: list[dict[str, Any]]
) -> None:
    _validate_columns(errors, vd, VENDOR_DIRECTORS_COLUMNS, "vendor_directors")


def validate_tenders_schema(errors: list[str], tenders: list[dict[str, Any]]) -> None:
    _validate_columns(errors, tenders, TENDERS_COLUMNS, "tenders")


def validate_bids_schema(errors: list[str], bids: list[dict[str, Any]]) -> None:
    _validate_columns(errors, bids, BIDS_COLUMNS, "bids")


def validate_labels_schema(errors: list[str], labels: dict[str, Any]) -> None:
    missing = LABELS_KEYS - set(labels.keys())
    if missing:
        errors.append(f"labels: missing top-level keys {sorted(missing)}")
        return
    for ring in labels.get("rings", []):
        missing_r = LABELS_RING_KEYS - set(ring.keys())
        if missing_r:
            errors.append(f"labels.rings entry missing keys {sorted(missing_r)}: {ring}")
    if not isinstance(labels["vendor_labels"], dict):
        errors.append("labels.vendor_labels must be a dict")
    if not isinstance(labels["planted_type"], dict):
        errors.append("labels.planted_type must be a dict")


# ---------------------------------------------------------------------------
# Uniqueness validators
# ---------------------------------------------------------------------------

def validate_unique_ids(
    errors: list[str],
    rows: list[dict[str, Any]],
    id_field: str,
    table: str,
) -> None:
    seen: set[str] = set()
    for row in rows:
        vid = row.get(id_field)
        if vid in seen:
            errors.append(f"{table}: duplicate {id_field} '{vid}'")
        seen.add(vid)


def validate_vendor_director_pairs(
    errors: list[str], vd: list[dict[str, Any]]
) -> None:
    seen: set[tuple[str, str]] = set()
    for row in vd:
        pair = (row["vendor_id"], row["person_id"])
        if pair in seen:
            errors.append(f"vendor_directors: duplicate pair {pair}")
        seen.add(pair)


# ---------------------------------------------------------------------------
# Foreign-key validators
# ---------------------------------------------------------------------------

def validate_foreign_keys(
    errors: list[str],
    vendors: list[dict[str, Any]],
    directors: list[dict[str, Any]],
    vendor_directors: list[dict[str, Any]],
    tenders: list[dict[str, Any]],
    bids: list[dict[str, Any]],
) -> None:
    vendor_ids = {v["vendor_id"] for v in vendors}
    director_ids = {d["person_id"] for d in directors}
    tender_ids = {t["tender_id"] for t in tenders}

    for row in vendor_directors:
        if row["vendor_id"] not in vendor_ids:
            errors.append(
                f"vendor_directors: unknown vendor_id '{row['vendor_id']}'"
            )
        if row["person_id"] not in director_ids:
            errors.append(
                f"vendor_directors: unknown person_id '{row['person_id']}'"
            )

    for row in bids:
        if row["tender_id"] not in tender_ids:
            errors.append(f"bids: unknown tender_id '{row['tender_id']}'")
        if row["vendor_id"] not in vendor_ids:
            errors.append(f"bids: unknown vendor_id '{row['vendor_id']}'")


# ---------------------------------------------------------------------------
# Eligibility validators
# ---------------------------------------------------------------------------

def validate_t002_eligibility(
    errors: list[str], vendors: list[dict[str, Any]]
) -> None:
    """Exactly one vendor must qualify T-002: V-047."""
    qualifiers = [v for v in vendors if qualifies_t002(v)]
    qualifier_ids = [v["vendor_id"] for v in qualifiers]

    if len(qualifiers) != 1:
        errors.append(
            f"T-002 eligibility: expected exactly 1 qualifier, "
            f"got {len(qualifiers)}: {qualifier_ids}"
        )
    elif qualifiers[0]["vendor_id"] != _vid(47):  # only reached when count == 1
        errors.append(
            f"T-002 eligibility: qualifier must be V-047, "
            f"got '{qualifiers[0]['vendor_id']}'"
        )

    # Ensure V-047 does qualify
    v047 = next((v for v in vendors if v["vendor_id"] == _vid(47)), None)
    if v047 is None:
        errors.append("T-002 eligibility: V-047 not found in vendors")
    elif not qualifies_t002(v047):
        errors.append(
            f"T-002 eligibility: V-047 should qualify but does not. "
            f"Attributes: {v047}"
        )

    # Ensure V-045 and V-046 do NOT qualify
    for reserved_n in [45, 46]:
        v = next((v for v in vendors if v["vendor_id"] == _vid(reserved_n)), None)
        if v is not None and qualifies_t002(v):
            errors.append(
                f"T-002 eligibility: {_vid(reserved_n)} must NOT qualify "
                f"but does. Attributes: {v}"
            )


def validate_t003_eligibility(
    errors: list[str], vendors: list[dict[str, Any]]
) -> None:
    """Between T003_MIN_QUALIFIERS and T003_MAX_QUALIFIERS vendors must qualify T-003."""
    qualifiers = [v for v in vendors if qualifies_t003(v)]
    if len(qualifiers) < T003_MIN_QUALIFIERS:
        errors.append(
            f"T-003 eligibility: expected at least {T003_MIN_QUALIFIERS} "
            f"qualifiers, got {len(qualifiers)}"
        )
    if len(qualifiers) > T003_MAX_QUALIFIERS:
        errors.append(
            f"T-003 eligibility: expected at most {T003_MAX_QUALIFIERS} "
            f"qualifiers (target 20-30), got {len(qualifiers)}"
        )


# ---------------------------------------------------------------------------
# Planted-scenario validators
# ---------------------------------------------------------------------------

def validate_r1(
    errors: list[str],
    vendors: list[dict[str, Any]],
    vendor_directors: list[dict[str, Any]],
) -> None:
    """V-045, V-046, V-047 share director P-010 and address A-007."""
    r1_vids = [_vid(n) for n in R1_VENDOR_IDS]
    shared_dir = _pid(R1_SHARED_DIRECTOR)
    shared_addr = _aid(R1_SHARED_ADDRESS)

    for vid in r1_vids:
        v = next((v for v in vendors if v["vendor_id"] == vid), None)
        if v is None:
            errors.append(f"R-1: vendor {vid} not found")
            continue
        if v["address_id"] != shared_addr:
            errors.append(
                f"R-1: {vid} has address_id '{v['address_id']}', "
                f"expected '{shared_addr}'"
            )

        has_director = any(
            row["vendor_id"] == vid and row["person_id"] == shared_dir
            for row in vendor_directors
        )
        if not has_director:
            errors.append(
                f"R-1: {vid} does not have shared director {shared_dir}"
            )


def validate_r2(
    errors: list[str],
    bids: list[dict[str, Any]],
) -> None:
    """V-100..V-103 rotate wins across exactly R2_ROTATION_TENDER_COUNT tenders."""
    r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
    r2_tender_ids = {_tid(n) for n in range(1, R2_ROTATION_TENDER_COUNT + 1)}

    # Check all R-2 tenders have a winner that is one of the R-2 vendors
    wins_by_tender: dict[str, list[str]] = {}
    for bid in bids:
        if bid["tender_id"] in r2_tender_ids and bid["won"] == 1:
            wins_by_tender.setdefault(bid["tender_id"], []).append(bid["vendor_id"])

    tenders_with_r2_winner = {
        tid: vids for tid, vids in wins_by_tender.items()
        if any(v in r2_vids for v in vids)
    }

    if len(tenders_with_r2_winner) < R2_ROTATION_TENDER_COUNT:
        errors.append(
            f"R-2: expected wins in {R2_ROTATION_TENDER_COUNT} tenders, "
            f"got {len(tenders_with_r2_winner)}"
        )

    # Each R-2 member must win at least one R-2 tender
    r2_winners: set[str] = set()
    for vids in tenders_with_r2_winner.values():
        r2_winners.update(v for v in vids if v in r2_vids)

    for rv in r2_vids:
        if rv not in r2_winners:
            errors.append(f"R-2: {rv} never wins a rotation tender")

    # Bid table must have all R-2 vendors bidding on every R-2 tender
    bids_by_tender_vendor = {
        (b["tender_id"], b["vendor_id"]) for b in bids
    }
    for tid in r2_tender_ids:
        for rv in r2_vids:
            if (tid, rv) not in bids_by_tender_vendor:
                errors.append(f"R-2: {rv} has no bid on {tid}")


def validate_r3(
    errors: list[str],
    bids: list[dict[str, Any]],
    num_tenders: int = 0,
) -> None:
    """
    R-3 cover bids: the last R3_TENDER_COUNT R-2 tenders (T-003..T-012) each
    carry 2-3 planted cover bids that sit 1-3% above the R-2 rotation winner.

    Approved ratio requirement: 1.01 <= cover_amount / winner_amount <= 1.03
    (both boundaries inclusive).

    Generation guarantees this exactly by rounding bid amounts to 2 dp and
    clamping via _clamp_cover_amount.  No additional tolerance is applied here.

    Cover bidders are drawn from the general pool (not R-1, not R-2) so they
    are cleanly separate from the rotating winners.

    Skip logic:
    - num_tenders < R3_OVERLAP_FIRST (=3): not enough tenders for any R-3
      overlay; skip entirely.
    - num_tenders in [R3_OVERLAP_FIRST .. R3_OVERLAP_LAST): only a partial
      R-3 overlay exists; validate only tenders that were generated.
    - num_tenders >= R3_OVERLAP_LAST (=12) or num_tenders == 0 (sentinel):
      validate all R3_TENDER_COUNT tenders T-003..T-012.
    """
    if num_tenders > 0 and num_tenders < R3_OVERLAP_FIRST:
        # Below T-003: no R-3 overlay possible.
        return

    # Determine which R-3 tenders actually exist in this dataset.
    actual_last = min(R3_OVERLAP_LAST, num_tenders) if num_tenders > 0 else R3_OVERLAP_LAST
    r3_tender_ids = {_tid(n) for n in range(R3_OVERLAP_FIRST, actual_last + 1)}

    # R-2 members are the rotating winners; they are never cover bidders.
    r1_vids = {_vid(n) for n in R1_VENDOR_IDS}
    r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
    reserved_vids = r1_vids | r2_vids

    for tid in r3_tender_ids:
        tender_bids = [b for b in bids if b["tender_id"] == tid]
        if not tender_bids:
            errors.append(f"R-3: no bids found for tender {tid}")
            continue

        # The winner of the R-3/R-2 overlap tender is the R-2 rotation member.
        winner_bids = [b for b in tender_bids if b["won"] == 1]
        if not winner_bids:
            errors.append(f"R-3: no winner found for tender {tid}")
            continue

        winner_amount = winner_bids[0]["bid_amount_cr"]
        winner_vid    = winner_bids[0]["vendor_id"]

        cover_bids_in_tender = []
        for b in tender_bids:
            if b["vendor_id"] in reserved_vids:
                continue
            if b["vendor_id"] == winner_vid:
                continue
            ratio = b["bid_amount_cr"] / winner_amount
            # Approved requirement: 1.01 <= ratio <= 1.03 (both inclusive).
            # No tolerance added: generation guarantees exact compliance.
            if 1.01 <= ratio <= 1.03:
                cover_bids_in_tender.append(b)

        if len(cover_bids_in_tender) < 2:
            errors.append(
                f"R-3: tender {tid} has only {len(cover_bids_in_tender)} "
                f"qualifying cover bids (need >= 2)"
            )


def validate_no_labels_in_features(
    errors: list[str],
    vendors: list[dict[str, Any]],
    bids: list[dict[str, Any]],
) -> None:
    """
    Confirm that no label-like fields appear in vendor or bid feature rows.
    Labels must only live in labels.json.
    """
    label_fields = {"label", "flagged", "planted_type", "ring_id", "ring_member"}
    for table_name, rows in [("vendors", vendors), ("bids", bids)]:
        if rows:
            for col in rows[0].keys():
                if col in label_fields:
                    errors.append(
                        f"label isolation: '{col}' found as a column in "
                        f"{table_name} — labels must only be in labels.json"
                    )


# ---------------------------------------------------------------------------
# Dataset size validators
# ---------------------------------------------------------------------------

def validate_counts(
    errors: list[str],
    vendors: list[dict[str, Any]],
    tenders: list[dict[str, Any]],
    num_vendors: int,
    num_tenders: int,
) -> None:
    if len(vendors) != num_vendors:
        errors.append(
            f"Expected {num_vendors} vendors, got {len(vendors)}"
        )
    if len(tenders) != num_tenders:
        errors.append(
            f"Expected {num_tenders} tenders, got {len(tenders)}"
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def verify_all(
    data: dict[str, Any],
    num_vendors: int,
    num_tenders: int,
) -> None:
    """
    Run all validations on the generated data dict.

    Parameters
    ----------
    data : dict returned by ``generate.generate_all()``
    num_vendors : expected vendor count
    num_tenders : expected tender count

    Raises
    ------
    VerificationError
        If any check fails.  All failures are accumulated and reported together.
    """
    errors: list[str] = []

    vendors = data["vendors"]
    directors = data["directors"]
    vendor_directors = data["vendor_directors"]
    tenders = data["tenders"]
    bids = data["bids"]
    labels = data["labels"]

    # --- Schema ---
    validate_vendors_schema(errors, vendors)
    validate_directors_schema(errors, directors)
    validate_vendor_directors_schema(errors, vendor_directors)
    validate_tenders_schema(errors, tenders)
    validate_bids_schema(errors, bids)
    validate_labels_schema(errors, labels)

    # --- Counts ---
    validate_counts(errors, vendors, tenders, num_vendors, num_tenders)

    # --- Uniqueness ---
    validate_unique_ids(errors, vendors, "vendor_id", "vendors")
    validate_unique_ids(errors, directors, "person_id", "directors")
    validate_unique_ids(errors, tenders, "tender_id", "tenders")
    validate_vendor_director_pairs(errors, vendor_directors)

    # --- Foreign keys ---
    validate_foreign_keys(errors, vendors, directors, vendor_directors, tenders, bids)

    # --- Eligibility ---
    validate_t002_eligibility(errors, vendors)
    validate_t003_eligibility(errors, vendors)

    # --- Planted scenarios ---
    validate_r1(errors, vendors, vendor_directors)
    validate_r2(errors, bids)
    validate_r3(errors, bids, num_tenders=num_tenders)

    # --- Label isolation ---
    validate_no_labels_in_features(errors, vendors, bids)

    if errors:
        raise VerificationError(errors)
