"""
TenderFender P2 Synthetic Data Tests
======================================

Coverage:
- Default generation (vendors=200, tenders=300, seed=42)
- Minimum valid counts (vendors=103, tenders=12)
- Invalid counts (below minimums) — must fail BEFORE writing files
- Determinism: same seed produces identical output
- Different seeds produce different output
- T-002 eligibility: exactly V-047 qualifies
- T-003 eligibility: >= 10 qualifiers
- R-1: V-045/046/047 share director P-010 and address A-007
- R-2: V-100..V-103 rotate wins across 12 tenders
- R-3: 10 tenders have 2-3 cover bids each 1-3% above winner
- Schema columns (all six files)
- Unique IDs (vendor_id, person_id, tender_id)
- Foreign key references
- Label isolation (no label fields in vendor/bid CSVs)
- Output preservation on verification failure (no files written)
- Safe-write: output files contain correct data after write
"""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from synth.generate import (
    generate_all,
    qualifies_t002,
    qualifies_t003,
    R1_VENDOR_IDS,
    R1_SHARED_DIRECTOR,
    R1_SHARED_ADDRESS,
    R2_VENDOR_IDS,
    R2_ROTATION_TENDER_COUNT,
    R3_TENDER_COUNT,
    R3_COVER_BIDDERS_MAX,
    R3_OVERLAP_FIRST,
    R3_OVERLAP_LAST,
    T003_MIN_QUALIFIERS,
    T003_MAX_QUALIFIERS,
    _vid,
    _pid,
    _aid,
    _tid,
)
from synth.verify import VerificationError, verify_all
from synth.generator import MIN_VENDORS, MIN_TENDERS, run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def default_data() -> dict[str, Any]:
    """Generate the default dataset once for the whole module."""
    return generate_all(num_vendors=200, num_tenders=300, seed=42)


@pytest.fixture(scope="module")
def min_data() -> dict[str, Any]:
    """Generate minimum valid dataset."""
    return generate_all(num_vendors=MIN_VENDORS, num_tenders=MIN_TENDERS, seed=42)


# ---------------------------------------------------------------------------
# 1. Default generation
# ---------------------------------------------------------------------------

class TestDefaultGeneration:
    def test_vendor_count(self, default_data):
        assert len(default_data["vendors"]) == 200

    def test_tender_count(self, default_data):
        assert len(default_data["tenders"]) == 300

    def test_directors_present(self, default_data):
        assert len(default_data["directors"]) > 0

    def test_vendor_directors_present(self, default_data):
        assert len(default_data["vendor_directors"]) > 0

    def test_bids_present(self, default_data):
        assert len(default_data["bids"]) > 0

    def test_labels_present(self, default_data):
        labels = default_data["labels"]
        assert "rings" in labels
        assert "vendor_labels" in labels
        assert "planted_type" in labels

    def test_passes_full_verification(self, default_data):
        """verify_all must not raise for default generation."""
        verify_all(default_data, num_vendors=200, num_tenders=300)


# ---------------------------------------------------------------------------
# 2. Minimum valid counts
# ---------------------------------------------------------------------------

class TestMinimumValidCounts:
    def test_min_vendor_count(self, min_data):
        assert len(min_data["vendors"]) == MIN_VENDORS

    def test_min_tender_count(self, min_data):
        assert len(min_data["tenders"]) == MIN_TENDERS

    def test_min_passes_verification(self, min_data):
        verify_all(min_data, num_vendors=MIN_VENDORS, num_tenders=MIN_TENDERS)


# ---------------------------------------------------------------------------
# 3. Invalid counts — must fail before any file is written
# ---------------------------------------------------------------------------

class TestInvalidCounts:
    def test_vendors_too_low_raises(self, tmp_path):
        with pytest.raises(ValueError, match="vendors"):
            run(num_vendors=MIN_VENDORS - 1, num_tenders=300, output_dir=tmp_path)

    def test_tenders_too_low_raises(self, tmp_path):
        with pytest.raises(ValueError, match="tenders"):
            run(num_vendors=200, num_tenders=MIN_TENDERS - 1, output_dir=tmp_path)

    def test_no_files_written_on_invalid_config(self, tmp_path):
        with pytest.raises(ValueError):
            run(num_vendors=50, num_tenders=300, output_dir=tmp_path)
        # No CSV/JSON files should exist in output dir
        written = list(tmp_path.glob("*.csv")) + list(tmp_path.glob("*.json"))
        assert written == [], f"Files written despite invalid config: {written}"


# ---------------------------------------------------------------------------
# 4. Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_seed_produces_identical_vendors(self):
        d1 = generate_all(num_vendors=200, num_tenders=300, seed=99)
        d2 = generate_all(num_vendors=200, num_tenders=300, seed=99)
        assert d1["vendors"] == d2["vendors"]

    def test_same_seed_produces_identical_bids(self):
        d1 = generate_all(num_vendors=200, num_tenders=300, seed=7)
        d2 = generate_all(num_vendors=200, num_tenders=300, seed=7)
        assert d1["bids"] == d2["bids"]

    def test_same_seed_produces_identical_labels(self):
        d1 = generate_all(num_vendors=200, num_tenders=300, seed=42)
        d2 = generate_all(num_vendors=200, num_tenders=300, seed=42)
        assert d1["labels"] == d2["labels"]

    def test_different_seeds_differ(self):
        d1 = generate_all(num_vendors=200, num_tenders=300, seed=1)
        d2 = generate_all(num_vendors=200, num_tenders=300, seed=2)
        # At least bids or vendors should differ
        assert d1["bids"] != d2["bids"] or d1["vendors"] != d2["vendors"]


# ---------------------------------------------------------------------------
# 5. T-002 eligibility
# ---------------------------------------------------------------------------

class TestT002Eligibility:
    def test_exactly_one_qualifier(self, default_data):
        qualifiers = [v for v in default_data["vendors"] if qualifies_t002(v)]
        assert len(qualifiers) == 1, (
            f"Expected exactly 1 T-002 qualifier, got {len(qualifiers)}: "
            f"{[q['vendor_id'] for q in qualifiers]}"
        )

    def test_qualifier_is_v047(self, default_data):
        qualifiers = [v for v in default_data["vendors"] if qualifies_t002(v)]
        assert qualifiers[0]["vendor_id"] == _vid(47)

    def test_v047_attributes(self, default_data):
        v047 = next(v for v in default_data["vendors"] if v["vendor_id"] == _vid(47))
        assert v047["registration_class"] == "Class-A"
        assert v047["turnover_cr"] >= 100.0
        assert v047["years_experience"] >= 15

    def test_v045_does_not_qualify(self, default_data):
        v045 = next(v for v in default_data["vendors"] if v["vendor_id"] == _vid(45))
        assert not qualifies_t002(v045), f"V-045 must not qualify T-002: {v045}"

    def test_v046_does_not_qualify(self, default_data):
        v046 = next(v for v in default_data["vendors"] if v["vendor_id"] == _vid(46))
        assert not qualifies_t002(v046), f"V-046 must not qualify T-002: {v046}"

    def test_eligibility_boundary_class_a_required(self):
        """A vendor with the right turnover/exp but wrong class must not qualify."""
        vendor = {
            "vendor_id": "V-TEST",
            "registration_class": "Class-B",
            "turnover_cr": 150.0,
            "years_experience": 20,
        }
        assert not qualifies_t002(vendor)

    def test_eligibility_boundary_turnover_required(self):
        """A vendor with Class-A and exp but low turnover must not qualify."""
        vendor = {
            "vendor_id": "V-TEST",
            "registration_class": "Class-A",
            "turnover_cr": 99.9,
            "years_experience": 20,
        }
        assert not qualifies_t002(vendor)

    def test_eligibility_boundary_experience_required(self):
        """A vendor with Class-A and high turnover but low exp must not qualify."""
        vendor = {
            "vendor_id": "V-TEST",
            "registration_class": "Class-A",
            "turnover_cr": 150.0,
            "years_experience": 14,
        }
        assert not qualifies_t002(vendor)

    def test_exactly_one_qualifier_min_dataset(self, min_data):
        qualifiers = [v for v in min_data["vendors"] if qualifies_t002(v)]
        assert len(qualifiers) == 1
        assert qualifiers[0]["vendor_id"] == _vid(47)


# ---------------------------------------------------------------------------
# 6. T-003 eligibility
# ---------------------------------------------------------------------------

class TestT003Eligibility:
    def test_at_least_ten_qualifiers(self, default_data):
        qualifiers = [v for v in default_data["vendors"] if qualifies_t003(v)]
        assert len(qualifiers) >= T003_MIN_QUALIFIERS, (
            f"Expected >= {T003_MIN_QUALIFIERS} T-003 qualifiers, "
            f"got {len(qualifiers)}"
        )

    def test_at_most_max_qualifiers(self, default_data):
        """Qualifier count must stay within the target ceiling."""
        qualifiers = [v for v in default_data["vendors"] if qualifies_t003(v)]
        assert len(qualifiers) <= T003_MAX_QUALIFIERS, (
            f"Expected <= {T003_MAX_QUALIFIERS} T-003 qualifiers (target 20-30), "
            f"got {len(qualifiers)}"
        )

    def test_t003_not_excluding_mse(self, default_data):
        """T-003 excludes MSE class; verify that logic."""
        # MSE vendors should NOT qualify T-003
        mse_vendors = [
            v for v in default_data["vendors"]
            if v["registration_class"] == "MSE"
        ]
        for v in mse_vendors:
            assert not qualifies_t003(v)

    def test_t003_qualifier_count_min_dataset(self, min_data):
        qualifiers = [v for v in min_data["vendors"] if qualifies_t003(v)]
        assert len(qualifiers) >= T003_MIN_QUALIFIERS


# ---------------------------------------------------------------------------
# 7. R-1 planted scenario
# ---------------------------------------------------------------------------

class TestR1Scenario:
    def _get_r1_vendors(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        r1_vids = {_vid(n) for n in R1_VENDOR_IDS}
        return [v for v in data["vendors"] if v["vendor_id"] in r1_vids]

    def test_all_r1_vendors_present(self, default_data):
        r1_vids = {_vid(n) for n in R1_VENDOR_IDS}
        found = {v["vendor_id"] for v in default_data["vendors"]} & r1_vids
        assert found == r1_vids

    def test_r1_shared_address(self, default_data):
        r1_vendors = self._get_r1_vendors(default_data)
        expected_addr = _aid(R1_SHARED_ADDRESS)
        for v in r1_vendors:
            assert v["address_id"] == expected_addr, (
                f"{v['vendor_id']} has address_id '{v['address_id']}', "
                f"expected '{expected_addr}'"
            )

    def test_r1_shared_director(self, default_data):
        shared_dir = _pid(R1_SHARED_DIRECTOR)
        vd_pairs = {
            (row["vendor_id"], row["person_id"])
            for row in default_data["vendor_directors"]
        }
        for vn in R1_VENDOR_IDS:
            assert (_vid(vn), shared_dir) in vd_pairs, (
                f"{_vid(vn)} does not have shared director {shared_dir}"
            )

    def test_r1_in_labels(self, default_data):
        labels = default_data["labels"]
        ring_ids = {r["ring_id"] for r in labels["rings"]}
        assert "R-1" in ring_ids

    def test_r1_label_vendor_ids(self, default_data):
        labels = default_data["labels"]
        r1_ring = next(r for r in labels["rings"] if r["ring_id"] == "R-1")
        assert set(r1_ring["vendor_ids"]) == {_vid(n) for n in R1_VENDOR_IDS}

    def test_r1_planted_type(self, default_data):
        labels = default_data["labels"]
        for vn in R1_VENDOR_IDS:
            vid = _vid(vn)
            assert labels["planted_type"].get(vid) == "shell_ring", (
                f"{vid} planted_type should be 'shell_ring'"
            )


# ---------------------------------------------------------------------------
# 8. R-2 planted scenario
# ---------------------------------------------------------------------------

class TestR2Scenario:
    def test_r2_vendors_present(self, default_data):
        r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
        found = {v["vendor_id"] for v in default_data["vendors"]} & r2_vids
        assert found == r2_vids

    def test_r2_rotation_across_12_tenders(self, default_data):
        r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
        r2_tids = {_tid(n) for n in range(1, R2_ROTATION_TENDER_COUNT + 1)}

        winning_tenders: set[str] = set()
        for bid in default_data["bids"]:
            if bid["tender_id"] in r2_tids and bid["won"] == 1:
                if bid["vendor_id"] in r2_vids:
                    winning_tenders.add(bid["tender_id"])

        assert len(winning_tenders) == R2_ROTATION_TENDER_COUNT, (
            f"R-2 wins found in {len(winning_tenders)} tenders, "
            f"expected {R2_ROTATION_TENDER_COUNT}"
        )

    def test_all_r2_members_win_at_least_once(self, default_data):
        r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
        r2_tids = {_tid(n) for n in range(1, R2_ROTATION_TENDER_COUNT + 1)}

        winners: set[str] = set()
        for bid in default_data["bids"]:
            if bid["tender_id"] in r2_tids and bid["won"] == 1:
                if bid["vendor_id"] in r2_vids:
                    winners.add(bid["vendor_id"])

        assert winners == r2_vids, (
            f"Not all R-2 members won. Missing: {r2_vids - winners}"
        )

    def test_r2_all_members_bid_on_all_rotation_tenders(self, default_data):
        r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
        r2_tids = {_tid(n) for n in range(1, R2_ROTATION_TENDER_COUNT + 1)}

        bid_pairs = {
            (b["tender_id"], b["vendor_id"]) for b in default_data["bids"]
        }
        for tid in r2_tids:
            for rv in r2_vids:
                assert (tid, rv) in bid_pairs, (
                    f"R-2 member {rv} has no bid on {tid}"
                )

    def test_r2_in_labels(self, default_data):
        labels = default_data["labels"]
        ring_ids = {r["ring_id"] for r in labels["rings"]}
        assert "R-2" in ring_ids

    def test_r2_planted_type(self, default_data):
        labels = default_data["labels"]
        for vn in R2_VENDOR_IDS:
            vid = _vid(vn)
            assert labels["planted_type"].get(vid) == "rotation"


# ---------------------------------------------------------------------------
# 9. R-3 planted scenario
# ---------------------------------------------------------------------------

class TestR3Scenario:
    def _r3_tids(self) -> set[str]:
        """T-003..T-012: the R-2 tenders that carry R-3 cover bids."""
        return {_tid(n) for n in range(R3_OVERLAP_FIRST, R3_OVERLAP_LAST + 1)}

    def test_r3_tenders_have_cover_bids(self, default_data):
        r3_tids = self._r3_tids()
        r1_vids = {_vid(n) for n in R1_VENDOR_IDS}
        r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
        reserved = r1_vids | r2_vids

        cover_tender_count = 0
        for tid in r3_tids:
            tender_bids = [b for b in default_data["bids"] if b["tender_id"] == tid]
            winner = next((b for b in tender_bids if b["won"] == 1), None)
            if winner is None:
                continue
            win_amount = winner["bid_amount_cr"]

            cover_bids = [
                b for b in tender_bids
                if b["vendor_id"] not in reserved
                and b["vendor_id"] != winner["vendor_id"]
                and 1.01 <= (b["bid_amount_cr"] / win_amount) <= 1.03
            ]
            if len(cover_bids) >= 2:
                cover_tender_count += 1

        assert cover_tender_count == R3_TENDER_COUNT, (
            f"Expected {R3_TENDER_COUNT} R-3 tenders with >= 2 cover bids, "
            f"got {cover_tender_count}"
        )

    def test_r3_cover_bids_upper_bound(self, default_data):
        """
        For each R-3 tender, every planted cover bid must be strictly above the
        winner and within 3% of the winning amount.

        Cover bids are identified by vendor_id from _cover_metadata (returned by
        generate_all alongside the bid data) — NOT by the ratio window that is
        being asserted. This makes both assertions fully non-tautological.
        """
        r3_tids = self._r3_tids()
        cover_meta = default_data["_cover_metadata"]   # {tender_id: [cover_vid, ...]}

        for tid in r3_tids:
            tender_bids = [b for b in default_data["bids"] if b["tender_id"] == tid]
            winner = next((b for b in tender_bids if b["won"] == 1), None)
            if winner is None:
                pytest.fail(f"R-3 tender {tid} has no winner")
            win_amount = winner["bid_amount_cr"]

            # Identify planted cover bids by vendor ID, not by ratio.
            planted_vids = set(cover_meta.get(tid, []))
            assert planted_vids, f"_cover_metadata has no entry for R-3 tender {tid}"

            planted_bids = [
                b for b in tender_bids
                if b["vendor_id"] in planted_vids
                and b["vendor_id"] != winner["vendor_id"]
            ]

            assert len(planted_bids) >= 2, (
                f"R-3 tender {tid}: expected >= 2 planted cover bids, "
                f"found {len(planted_bids)} (planted_vids={planted_vids})"
            )

            for b in planted_bids:
                ratio = b["bid_amount_cr"] / win_amount
                # Both bounds are non-tautological: identification was by vendor ID.
                # Approved requirement: 1.01 <= ratio <= 1.03 (both inclusive).
                assert ratio >= 1.01, (
                    f"Planted cover bid {b['vendor_id']} in {tid}: "
                    f"ratio {ratio:.6f} is below the 1% floor"
                )
                assert ratio <= 1.03, (
                    f"Planted cover bid {b['vendor_id']} in {tid}: "
                    f"ratio {ratio:.6f} exceeds the 3% cap"
                )

    def test_r3_ring_absent_below_r3_start(self):
        """
        When generate_all is called with fewer than R3_OVERLAP_FIRST (=3) tenders,
        no R-3 overlay can be planted and labels must NOT include an R-3 ring.
        (Only reachable by calling generate_all directly below MIN_TENDERS; the
        CLI rejects such configs.)
        """
        data_2 = generate_all(num_vendors=103, num_tenders=2, seed=42)
        ring_ids = {r["ring_id"] for r in data_2["labels"]["rings"]}
        assert "R-3" not in ring_ids, (
            f"R-3 ring should be absent for a 2-tender run, but found: {ring_ids}"
        )

    def test_r3_ring_present_when_r3_tenders_exist(self, default_data):
        """With 300 tenders, all 10 R-3 tenders (T-003..T-012) exist; R-3 ring must be present."""
        ring_ids = {r["ring_id"] for r in default_data["labels"]["rings"]}
        assert "R-3" in ring_ids

    def test_r3_ring_present_in_min_config(self, min_data):
        """
        At MIN_TENDERS=12 the R-3 overlay covers all 10 R-3 tenders (T-003..T-012).
        All three rings must be present in labels.json at the minimum configuration.
        """
        ring_ids = {r["ring_id"] for r in min_data["labels"]["rings"]}
        assert "R-3" in ring_ids, (
            f"R-3 ring must be present at MIN_TENDERS=12, found rings: {ring_ids}"
        )
        # Confirm all three required rings are present together
        assert {"R-1", "R-2", "R-3"}.issubset(ring_ids), (
            f"Expected R-1, R-2, R-3 at minimum config; found: {ring_ids}"
        )


# ---------------------------------------------------------------------------
# 9a. R-3 ratio boundary tests (direct validate_r3 calls)
# ---------------------------------------------------------------------------

class TestR3RatioBoundary:
    """
    Unit tests for validate_r3 at exact boundary values.

    Bids are constructed directly — no full generation needed — to isolate
    the validator from the generator.  The winner amount is chosen to be a
    round number (100.00) so bid amounts at exact ratio boundaries are
    representable in 2 dp without rounding error.

    Approved requirement: 1.01 <= cover_amount / winner_amount <= 1.03
    """

    _WINNER = 100.00   # clean 2-dp value: no rounding ambiguity at boundaries

    def _make_bids(self, cover_amounts: list[float]) -> list[dict]:
        """Build a minimal valid bids list for T-003 with given cover amounts."""
        # Winner: V-100 (R-2 member, excluded from cover identification)
        # Cover bidders: V-200, V-201, ... (general pool, not reserved)
        bids = [
            {
                "tender_id": _tid(3),   # T-003 is an R-3 tender
                "vendor_id": _vid(100),  # R-2 member — designated winner
                "bid_amount_cr": self._WINNER,
                "bid_ratio": round(self._WINNER / 50.0, 4),
                "rank": 1,
                "won": 1,
                "submitted_at": "2024-01-17T09:00:00",
            }
        ]
        for i, amt in enumerate(cover_amounts):
            bids.append({
                "tender_id": _tid(3),
                "vendor_id": f"V-{200 + i:03d}",   # not R-1, not R-2
                "bid_amount_cr": round(amt, 2),
                "bid_ratio": round(amt / 50.0, 4),
                "rank": i + 2,
                "won": 0,
                "submitted_at": "2024-01-17T09:00:00",
            })
        return bids

    def test_lower_boundary_1_01_accepted(self):
        """ratio = 1.01 exactly: must be accepted (lower bound is inclusive)."""
        from synth.verify import validate_r3
        bids = self._make_bids([101.00, 102.00])   # ratios: 1.01, 1.02
        errors: list[str] = []
        validate_r3(errors, bids, num_tenders=3)   # only T-003 checked
        assert not errors, f"1.01 ratio should be accepted; errors: {errors}"

    def test_upper_boundary_1_03_accepted(self):
        """ratio = 1.03 exactly: must be accepted (upper bound is inclusive)."""
        from synth.verify import validate_r3
        bids = self._make_bids([101.50, 103.00])   # ratios: 1.015, 1.03
        errors: list[str] = []
        validate_r3(errors, bids, num_tenders=3)   # only T-003 checked
        assert not errors, f"1.03 ratio should be accepted; errors: {errors}"

    def test_below_lower_boundary_1_0099_rejected(self):
        """
        ratio = 1.0099 (i.e. cover_amount = 100.99 / winner = 100.00 = 0.9999
        — use 100.99 which gives ratio 1.0099): must not count as a cover bid.
        With only one valid cover bid, the tender should fail the >= 2 check.
        """
        from synth.verify import validate_r3
        # 100.99 / 100.00 = 1.0099  → below 1.01 → should NOT qualify
        # 102.00 / 100.00 = 1.02    → qualifies
        # Only 1 qualifying bid → error expected
        bids = self._make_bids([100.99, 102.00])   # ratios: 1.0099, 1.02
        errors: list[str] = []
        validate_r3(errors, bids, num_tenders=3)   # only T-003 checked
        assert errors, (
            "ratio 1.0099 should be rejected; expected a validation error"
        )
        assert any("T-003" in e and "cover bids" in e for e in errors), (
            f"Expected cover-bid count error for T-003; got: {errors}"
        )

    def test_above_upper_boundary_1_0301_rejected(self):
        """
        ratio = 1.0301 (cover_amount = 103.01): must not count as a cover bid.
        With only one valid cover bid, the tender should fail the >= 2 check.
        """
        from synth.verify import validate_r3
        # 103.01 / 100.00 = 1.0301  → above 1.03 → should NOT qualify
        # 101.50 / 100.00 = 1.015   → qualifies
        # Only 1 qualifying bid → error expected
        bids = self._make_bids([103.01, 101.50])   # ratios: 1.0301, 1.015
        errors: list[str] = []
        validate_r3(errors, bids, num_tenders=3)   # only T-003 checked
        assert errors, (
            "ratio 1.0301 should be rejected; expected a validation error"
        )
        assert any("T-003" in e and "cover bids" in e for e in errors), (
            f"Expected cover-bid count error for T-003; got: {errors}"
        )

    def test_both_boundaries_together(self):
        """1.01 and 1.03 together: both count, tender passes."""
        from synth.verify import validate_r3
        bids = self._make_bids([101.00, 103.00])   # exact boundaries
        errors: list[str] = []
        validate_r3(errors, bids, num_tenders=3)   # only T-003 checked
        assert not errors, (
            f"1.01 and 1.03 together should be accepted; errors: {errors}"
        )


# ---------------------------------------------------------------------------
# 9b. Configuration scenarios: 12, 13, and 22 tenders
# ---------------------------------------------------------------------------

class TestConfigurationScenarios:
    """
    Explicitly validates all-three-rings presence and verification pass
    at three boundary tender counts:

    - 12 tenders: exact minimum.  R-2 (T-001..T-012) + R-3 overlay (T-003..T-012).
    - 13 tenders: one tender beyond minimum.  T-013 is a plain noise tender.
    - 22 tenders: old minimum before overlap design. All three rings still present.
    """

    def _all_rings(self, data: dict) -> set[str]:
        return {r["ring_id"] for r in data["labels"]["rings"]}

    # --- 12-tender configuration ---

    def test_12t_all_three_rings_present(self):
        d = generate_all(num_vendors=103, num_tenders=12, seed=42)
        assert {"R-1", "R-2", "R-3"}.issubset(self._all_rings(d)), (
            f"Expected R-1, R-2, R-3 at 12 tenders; got {self._all_rings(d)}"
        )

    def test_12t_r3_cover_metadata_has_10_entries(self):
        d = generate_all(num_vendors=103, num_tenders=12, seed=42)
        assert len(d["_cover_metadata"]) == R3_TENDER_COUNT, (
            f"Expected 10 cover_metadata entries at 12 tenders; "
            f"got {len(d['_cover_metadata'])}"
        )

    def test_12t_r3_cover_metadata_keys_are_t003_to_t012(self):
        d = generate_all(num_vendors=103, num_tenders=12, seed=42)
        expected = {_tid(n) for n in range(R3_OVERLAP_FIRST, R3_OVERLAP_LAST + 1)}
        assert set(d["_cover_metadata"].keys()) == expected, (
            f"cover_metadata keys mismatch: {set(d['_cover_metadata'].keys())} "
            f"!= {expected}"
        )

    def test_12t_cover_bidders_not_r2_members(self):
        """Cover bidders must never be R-2 rotation members."""
        d = generate_all(num_vendors=103, num_tenders=12, seed=42)
        r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
        for tid, cvids in d["_cover_metadata"].items():
            overlap = set(cvids) & r2_vids
            assert not overlap, (
                f"R-3 tender {tid}: cover bidders {overlap} are R-2 members"
            )

    def test_12t_cover_bidders_not_r1_members(self):
        """Cover bidders must never be R-1 shell-ring members."""
        d = generate_all(num_vendors=103, num_tenders=12, seed=42)
        r1_vids = {_vid(n) for n in R1_VENDOR_IDS}
        for tid, cvids in d["_cover_metadata"].items():
            overlap = set(cvids) & r1_vids
            assert not overlap, (
                f"R-3 tender {tid}: cover bidders {overlap} are R-1 members"
            )

    def test_12t_r2_winner_rotation_preserved(self):
        """
        R-2 winner rotation must be unaffected by the R-3 overlay.
        Each R-2 tender must still have exactly one R-2 member as winner.
        """
        d = generate_all(num_vendors=103, num_tenders=12, seed=42)
        r2_vids = {_vid(n) for n in R2_VENDOR_IDS}
        r2_tids = {_tid(n) for n in range(1, R2_ROTATION_TENDER_COUNT + 1)}
        for tid in r2_tids:
            winner = next(
                (b for b in d["bids"] if b["tender_id"] == tid and b["won"] == 1),
                None,
            )
            assert winner is not None, f"No winner for R-2 tender {tid}"
            assert winner["vendor_id"] in r2_vids, (
                f"R-2 tender {tid} winner is {winner['vendor_id']}, not an R-2 member"
            )

    def test_12t_verification_passes(self):
        d = generate_all(num_vendors=103, num_tenders=12, seed=42)
        verify_all(d, num_vendors=103, num_tenders=12)  # must not raise

    # --- 13-tender configuration ---

    def test_13t_all_three_rings_present(self):
        d = generate_all(num_vendors=103, num_tenders=13, seed=42)
        assert {"R-1", "R-2", "R-3"}.issubset(self._all_rings(d)), (
            f"Expected R-1, R-2, R-3 at 13 tenders; got {self._all_rings(d)}"
        )

    def test_13t_t013_is_noise_only(self):
        """T-013 is the extra tender; it must not appear in cover_metadata."""
        d = generate_all(num_vendors=103, num_tenders=13, seed=42)
        assert _tid(13) not in d["_cover_metadata"], (
            "T-013 should be a plain noise tender with no cover_metadata entry"
        )

    def test_13t_verification_passes(self):
        d = generate_all(num_vendors=103, num_tenders=13, seed=42)
        verify_all(d, num_vendors=103, num_tenders=13)  # must not raise

    # --- 22-tender configuration ---

    def test_22t_all_three_rings_present(self):
        d = generate_all(num_vendors=103, num_tenders=22, seed=42)
        assert {"R-1", "R-2", "R-3"}.issubset(self._all_rings(d)), (
            f"Expected R-1, R-2, R-3 at 22 tenders; got {self._all_rings(d)}"
        )

    def test_22t_cover_metadata_still_t003_to_t012(self):
        """
        At 22 tenders the R-3 signal is still only on T-003..T-012.
        T-013..T-022 are plain noise tenders.
        """
        d = generate_all(num_vendors=103, num_tenders=22, seed=42)
        expected = {_tid(n) for n in range(R3_OVERLAP_FIRST, R3_OVERLAP_LAST + 1)}
        assert set(d["_cover_metadata"].keys()) == expected, (
            f"At 22 tenders, cover_metadata should only cover T-003..T-012; "
            f"got {sorted(d['_cover_metadata'].keys())}"
        )

    def test_22t_verification_passes(self):
        d = generate_all(num_vendors=103, num_tenders=22, seed=42)
        verify_all(d, num_vendors=103, num_tenders=22)  # must not raise


# ---------------------------------------------------------------------------
# 10. Schema / column validation
# ---------------------------------------------------------------------------

class TestSchema:
    VENDORS_COLS = {
        "vendor_id", "name", "turnover_cr", "years_experience",
        "registration_class", "address_id", "contact_id",
    }
    DIRECTORS_COLS = {"person_id", "name"}
    VENDOR_DIRECTORS_COLS = {"vendor_id", "person_id"}
    TENDERS_COLS = {
        "tender_id", "buyer_id", "title", "estimated_value_cr",
        "bid_days", "open_date",
    }
    BIDS_COLS = {
        "tender_id", "vendor_id", "bid_amount_cr", "bid_ratio",
        "rank", "won", "submitted_at",
    }

    def _check_cols(self, rows, expected, label):
        assert rows, f"{label} is empty"
        actual = set(rows[0].keys())
        assert actual == expected, (
            f"{label} columns mismatch. Extra: {actual-expected}, "
            f"Missing: {expected-actual}"
        )

    def test_vendors_columns(self, default_data):
        self._check_cols(default_data["vendors"], self.VENDORS_COLS, "vendors")

    def test_directors_columns(self, default_data):
        self._check_cols(default_data["directors"], self.DIRECTORS_COLS, "directors")

    def test_vendor_directors_columns(self, default_data):
        self._check_cols(default_data["vendor_directors"], self.VENDOR_DIRECTORS_COLS, "vendor_directors")

    def test_tenders_columns(self, default_data):
        self._check_cols(default_data["tenders"], self.TENDERS_COLS, "tenders")

    def test_bids_columns(self, default_data):
        self._check_cols(default_data["bids"], self.BIDS_COLS, "bids")

    def test_labels_top_level_keys(self, default_data):
        labels = default_data["labels"]
        assert set(labels.keys()) == {"rings", "vendor_labels", "planted_type"}

    def test_ring_keys(self, default_data):
        for ring in default_data["labels"]["rings"]:
            assert set(ring.keys()) >= {"ring_id", "vendor_ids", "type"}


# ---------------------------------------------------------------------------
# 11. Unique IDs
# ---------------------------------------------------------------------------

class TestUniqueIds:
    def test_vendor_ids_unique(self, default_data):
        ids = [v["vendor_id"] for v in default_data["vendors"]]
        assert len(ids) == len(set(ids))

    def test_director_ids_unique(self, default_data):
        ids = [d["person_id"] for d in default_data["directors"]]
        assert len(ids) == len(set(ids))

    def test_tender_ids_unique(self, default_data):
        ids = [t["tender_id"] for t in default_data["tenders"]]
        assert len(ids) == len(set(ids))

    def test_vendor_director_pairs_unique(self, default_data):
        pairs = [
            (r["vendor_id"], r["person_id"])
            for r in default_data["vendor_directors"]
        ]
        assert len(pairs) == len(set(pairs))


# ---------------------------------------------------------------------------
# 12. Foreign key references
# ---------------------------------------------------------------------------

class TestForeignKeys:
    def test_all_bid_vendor_ids_exist(self, default_data):
        vendor_ids = {v["vendor_id"] for v in default_data["vendors"]}
        for bid in default_data["bids"]:
            assert bid["vendor_id"] in vendor_ids, (
                f"Bid references unknown vendor_id '{bid['vendor_id']}'"
            )

    def test_all_bid_tender_ids_exist(self, default_data):
        tender_ids = {t["tender_id"] for t in default_data["tenders"]}
        for bid in default_data["bids"]:
            assert bid["tender_id"] in tender_ids, (
                f"Bid references unknown tender_id '{bid['tender_id']}'"
            )

    def test_all_vendor_director_vendor_ids_exist(self, default_data):
        vendor_ids = {v["vendor_id"] for v in default_data["vendors"]}
        for row in default_data["vendor_directors"]:
            assert row["vendor_id"] in vendor_ids

    def test_all_vendor_director_person_ids_exist(self, default_data):
        person_ids = {d["person_id"] for d in default_data["directors"]}
        for row in default_data["vendor_directors"]:
            assert row["person_id"] in person_ids


# ---------------------------------------------------------------------------
# 13. Label isolation
# ---------------------------------------------------------------------------

class TestLabelIsolation:
    PROHIBITED = {"label", "flagged", "planted_type", "ring_id", "ring_member"}

    def test_no_label_fields_in_vendors(self, default_data):
        if default_data["vendors"]:
            cols = set(default_data["vendors"][0].keys())
            overlap = cols & self.PROHIBITED
            assert not overlap, f"Prohibited fields in vendors: {overlap}"

    def test_no_label_fields_in_bids(self, default_data):
        if default_data["bids"]:
            cols = set(default_data["bids"][0].keys())
            overlap = cols & self.PROHIBITED
            assert not overlap, f"Prohibited fields in bids: {overlap}"

    def test_no_label_fields_in_tenders(self, default_data):
        if default_data["tenders"]:
            cols = set(default_data["tenders"][0].keys())
            overlap = cols & self.PROHIBITED
            assert not overlap, f"Prohibited fields in tenders: {overlap}"


# ---------------------------------------------------------------------------
# 14. Output preservation on verification failure
# ---------------------------------------------------------------------------

class TestOutputPreservation:
    def test_no_files_written_if_verification_fails(self, tmp_path):
        """
        If verification fails, no output files should be created or modified.
        We achieve this by patching verify_all to always raise VerificationError.
        """
        sentinel = tmp_path / "vendors.csv"
        sentinel.write_text("original", encoding="utf-8")

        with mock.patch(
            "synth.generator.verify_all",
            side_effect=VerificationError(["injected error"]),
        ):
            with pytest.raises(VerificationError):
                run(num_vendors=200, num_tenders=300, output_dir=tmp_path)

        # The original file should be unchanged
        assert sentinel.read_text(encoding="utf-8") == "original"


# ---------------------------------------------------------------------------
# 15. Safe-write integration
# ---------------------------------------------------------------------------

class TestSafeWrite:
    def test_files_written_correctly(self, tmp_path):
        """run() writes all six files with correct content."""
        data = run(num_vendors=200, num_tenders=300, seed=42, output_dir=tmp_path)

        expected_files = {
            "vendors.csv", "directors.csv", "vendor_directors.csv",
            "tenders.csv", "bids.csv", "labels.json",
        }
        written = {f.name for f in tmp_path.iterdir() if not f.name.endswith(".tmp")}
        assert expected_files.issubset(written), (
            f"Missing files: {expected_files - written}"
        )

    def test_vendors_csv_parseable(self, tmp_path):
        run(num_vendors=200, num_tenders=300, seed=42, output_dir=tmp_path)
        content = (tmp_path / "vendors.csv").read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 200

    def test_labels_json_parseable(self, tmp_path):
        run(num_vendors=200, num_tenders=300, seed=42, output_dir=tmp_path)
        content = (tmp_path / "labels.json").read_text(encoding="utf-8")
        labels = json.loads(content)
        assert "rings" in labels

    def test_no_extra_files_written(self, tmp_path):
        """Only the six authorised files should be written."""
        run(num_vendors=200, num_tenders=300, seed=42, output_dir=tmp_path)
        written = {f.name for f in tmp_path.iterdir()}
        expected = {
            "vendors.csv", "directors.csv", "vendor_directors.csv",
            "tenders.csv", "bids.csv", "labels.json",
        }
        extra = written - expected
        assert not extra, f"Unexpected files written: {extra}"

    def test_tmp_files_cleaned_up(self, tmp_path):
        """No .tmp files should remain after a successful write."""
        run(num_vendors=200, num_tenders=300, seed=42, output_dir=tmp_path)
        tmps = list(tmp_path.glob("*.tmp"))
        assert tmps == [], f"Leftover .tmp files: {tmps}"


# ---------------------------------------------------------------------------
# 16. I/O rollback on rename failure  (D5)
# ---------------------------------------------------------------------------

class TestRollbackOnRenameFailure:
    def test_previously_renamed_files_restored(self, tmp_path):
        """
        When a tmp->final rename fails partway through _safe_write, every file
        that had already been renamed to its final name must be rolled back to
        its pre-write content (restored from .bak).  Additionally, the file
        whose backup was created but whose rename then failed must also be
        restored (D4 regression).
        """
        from synth.generator import _safe_write

        # Pre-populate three files so backups are created for them.
        (tmp_path / "vendors.csv").write_text("old_vendors", encoding="utf-8")
        (tmp_path / "directors.csv").write_text("old_directors", encoding="utf-8")
        (tmp_path / "bids.csv").write_text("old_bids", encoding="utf-8")

        file_contents = {
            "vendors.csv":           "new_vendors",
            "directors.csv":         "new_directors",
            "vendor_directors.csv":  "new_vd",
            "tenders.csv":           "new_tenders",
            "bids.csv":              "new_bids",
            "labels.json":           "{}",
        }

        _original_replace = Path.replace

        def _patched_replace(self_path: Path, target) -> Path:
            # Intercept only the tmp->final rename for bids.csv (not the backup rename).
            if self_path.name == "bids.csv.tmp" and Path(target).name == "bids.csv":
                raise OSError("Simulated bids.csv rename failure")
            return _original_replace(self_path, target)

        with mock.patch.object(Path, "replace", _patched_replace):
            with pytest.raises(RuntimeError, match="Simulated bids.csv rename failure"):
                _safe_write(tmp_path, file_contents)

        # vendors.csv and directors.csv were renamed before bids.csv failed;
        # they must be rolled back to their original content.
        assert (tmp_path / "vendors.csv").read_text(encoding="utf-8") == "old_vendors"
        assert (tmp_path / "directors.csv").read_text(encoding="utf-8") == "old_directors"

        # bids.csv had its original moved to .bak, then its rename failed;
        # D4 fix must restore it from .bak so the file is not left missing.
        assert (tmp_path / "bids.csv").exists(), "bids.csv was left missing after rollback"
        assert (tmp_path / "bids.csv").read_text(encoding="utf-8") == "old_bids"

        # No orphaned tmp or bak files.
        assert not list(tmp_path.glob("*.tmp")), "Leftover .tmp files after rollback"
        assert not list(tmp_path.glob("*.bak")), "Leftover .bak files after rollback"

    def test_newly_created_files_removed_on_rollback(self, tmp_path):
        """
        On a first-time run, if a rename fails mid-way, any files that were
        successfully created from nothing (no pre-existing version) must be
        unlinked during rollback so the output directory is left empty (D13).
        """
        from synth.generator import _safe_write

        # Only vendors.csv and directors.csv pre-exist (e.g. partial previous run).
        (tmp_path / "vendors.csv").write_text("old_vendors", encoding="utf-8")
        (tmp_path / "directors.csv").write_text("old_directors", encoding="utf-8")
        # vendor_directors.csv, tenders.csv, bids.csv, labels.json are NEW

        file_contents = {
            "vendors.csv":           "new_vendors",
            "directors.csv":         "new_directors",
            "vendor_directors.csv":  "new_vd",
            "tenders.csv":           "new_tenders",
            "bids.csv":              "new_bids",
            "labels.json":           "{}",
        }

        _original_replace = Path.replace

        def _patched_replace(self_path: Path, target) -> Path:
            # Fail on the rename of labels.json (last file, by which point
            # vendor_directors.csv and tenders.csv have been created from nothing).
            if self_path.name == "labels.json.tmp" and Path(target).name == "labels.json":
                raise OSError("Simulated labels.json rename failure")
            return _original_replace(self_path, target)

        with mock.patch.object(Path, "replace", _patched_replace):
            with pytest.raises(RuntimeError, match="Simulated labels.json rename failure"):
                _safe_write(tmp_path, file_contents)

        # Pre-existing files must be restored.
        assert (tmp_path / "vendors.csv").read_text(encoding="utf-8") == "old_vendors"
        assert (tmp_path / "directors.csv").read_text(encoding="utf-8") == "old_directors"

        # Newly-created files (vendor_directors, tenders, bids) must be unlinked (D13).
        assert not (tmp_path / "vendor_directors.csv").exists(), (
            "vendor_directors.csv should have been removed by rollback"
        )
        assert not (tmp_path / "tenders.csv").exists(), (
            "tenders.csv should have been removed by rollback"
        )
        assert not (tmp_path / "bids.csv").exists(), (
            "bids.csv should have been removed by rollback"
        )

        # No orphaned tmp or bak files.
        assert not list(tmp_path.glob("*.tmp")), "Leftover .tmp files after rollback"
        assert not list(tmp_path.glob("*.bak")), "Leftover .bak files after rollback"

    def test_rollback_at_position_1_all_preexisting(self, tmp_path):
        """
        Failure at the very first rename (vendors.csv.tmp -> vendors.csv).
        At that point: renamed=[], created=[].
        Rollback must: remove all .tmp files, restore vendors.csv from .bak.
        All other files must be unchanged.
        """
        from synth.generator import _safe_write

        # All six files pre-exist.
        for fn, content in [
            ("vendors.csv", "old_vendors"),
            ("directors.csv", "old_directors"),
            ("vendor_directors.csv", "old_vd"),
            ("tenders.csv", "old_tenders"),
            ("bids.csv", "old_bids"),
            ("labels.json", "old_labels"),
        ]:
            (tmp_path / fn).write_text(content, encoding="utf-8")

        file_contents = {
            "vendors.csv":           "new_vendors",
            "directors.csv":         "new_directors",
            "vendor_directors.csv":  "new_vd",
            "tenders.csv":           "new_tenders",
            "bids.csv":              "new_bids",
            "labels.json":           "{}",
        }

        _original_replace = Path.replace

        def _patched_replace(self_path: Path, target) -> Path:
            if self_path.name == "vendors.csv.tmp" and Path(target).name == "vendors.csv":
                raise OSError("Simulated vendors.csv rename failure")
            return _original_replace(self_path, target)

        with mock.patch.object(Path, "replace", _patched_replace):
            with pytest.raises(RuntimeError, match="Simulated vendors.csv rename failure"):
                _safe_write(tmp_path, file_contents)

        # vendors.csv was backed up then rename failed; must be restored from .bak.
        assert (tmp_path / "vendors.csv").read_text(encoding="utf-8") == "old_vendors"
        # All other pre-existing files must be untouched (rename never reached them).
        assert (tmp_path / "directors.csv").read_text(encoding="utf-8") == "old_directors"
        assert (tmp_path / "vendor_directors.csv").read_text(encoding="utf-8") == "old_vd"
        assert (tmp_path / "tenders.csv").read_text(encoding="utf-8") == "old_tenders"
        assert (tmp_path / "bids.csv").read_text(encoding="utf-8") == "old_bids"
        assert (tmp_path / "labels.json").read_text(encoding="utf-8") == "old_labels"

        assert not list(tmp_path.glob("*.tmp")), "Leftover .tmp files after rollback"
        assert not list(tmp_path.glob("*.bak")), "Leftover .bak files after rollback"

    def test_rollback_at_position_3_mixed_preexisting(self, tmp_path):
        """
        Failure at position 3 (vendor_directors.csv.tmp -> vendor_directories.csv).
        Pre-existing: vendors.csv, directors.csv (have .bak); vendor_directors.csv is NEW.
        State at failure: renamed=[(vendors,bak),(directors,bak)], created=[vendor_dirs].
        Rollback must: restore vendors and directors from .bak; unlink vendor_directories.csv.
        """
        from synth.generator import _safe_write

        (tmp_path / "vendors.csv").write_text("old_vendors", encoding="utf-8")
        (tmp_path / "directors.csv").write_text("old_directors", encoding="utf-8")
        # vendor_directors.csv, tenders.csv, bids.csv, labels.json are NEW

        file_contents = {
            "vendors.csv":           "new_vendors",
            "directors.csv":         "new_directors",
            "vendor_directors.csv":  "new_vd",
            "tenders.csv":           "new_tenders",
            "bids.csv":              "new_bids",
            "labels.json":           "{}",
        }

        _original_replace = Path.replace

        def _patched_replace(self_path: Path, target) -> Path:
            if (self_path.name == "vendor_directors.csv.tmp"
                    and Path(target).name == "vendor_directors.csv"):
                raise OSError("Simulated vendor_directors.csv rename failure")
            return _original_replace(self_path, target)

        with mock.patch.object(Path, "replace", _patched_replace):
            with pytest.raises(RuntimeError, match="Simulated vendor_directors.csv rename failure"):
                _safe_write(tmp_path, file_contents)

        # Pre-existing files must be restored.
        assert (tmp_path / "vendors.csv").read_text(encoding="utf-8") == "old_vendors"
        assert (tmp_path / "directors.csv").read_text(encoding="utf-8") == "old_directors"

        # vendor_directories.csv was created from nothing; rollback must unlink it (D13).
        assert not (tmp_path / "vendor_directors.csv").exists(), (
            "vendor_directors.csv (newly created) should have been unlinked by rollback"
        )

        assert not list(tmp_path.glob("*.tmp")), "Leftover .tmp files after rollback"
        assert not list(tmp_path.glob("*.bak")), "Leftover .bak files after rollback"

    def test_rollback_when_backup_step_fails(self, tmp_path):
        """
        If the backup step itself fails (final.replace(backup) raises), rollback must:
        - Remove all .tmp files
        - Restore any files already renamed
        - Unlink any files already created from nothing
        - NOT leave any .bak orphans (backup that raised never completed)
        """
        from synth.generator import _safe_write

        # vendors.csv and directors.csv pre-exist; vendor_directors is new.
        (tmp_path / "vendors.csv").write_text("old_vendors", encoding="utf-8")
        (tmp_path / "directors.csv").write_text("old_directors", encoding="utf-8")

        file_contents = {
            "vendors.csv":           "new_vendors",
            "directors.csv":         "new_directors",
            "vendor_directors.csv":  "new_vd",
            "tenders.csv":           "new_tenders",
            "bids.csv":              "new_bids",
            "labels.json":           "{}",
        }

        _original_replace = Path.replace

        def _patched_replace(self_path: Path, target) -> Path:
            # Fail on the BACKUP step for directors.csv (not the tmp->final rename).
            if self_path.name == "directors.csv" and Path(target).name == "directors.csv.bak":
                raise OSError("Simulated directors.csv backup failure")
            return _original_replace(self_path, target)

        with mock.patch.object(Path, "replace", _patched_replace):
            with pytest.raises(RuntimeError, match="Failed to backup"):
                _safe_write(tmp_path, file_contents)

        # vendors.csv was already renamed before directors.csv backup failed.
        # It must be restored from its .bak.
        assert (tmp_path / "vendors.csv").read_text(encoding="utf-8") == "old_vendors"

        # directors.csv backup failed → its original content was never touched;
        # the file must still contain its original content.
        assert (tmp_path / "directors.csv").read_text(encoding="utf-8") == "old_directors"

        assert not list(tmp_path.glob("*.tmp")), "Leftover .tmp files after rollback"
        assert not list(tmp_path.glob("*.bak")), "Leftover .bak files after rollback"
