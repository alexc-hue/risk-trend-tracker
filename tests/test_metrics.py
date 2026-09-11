"""Tests for src/metrics.py: per-risk trajectory, mitigation effectiveness,
and the churn-controlled risk trajectory score.

Small hand-built snapshot panels, not the repo's sample CSV.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.metrics import (
    _shared_cohort_exposure,
    mitigation_effectiveness,
    per_risk_trajectory,
    risk_trajectory_score,
)


def _row(risk_id, date, exposure, status=None, description="desc", category="Technical",
         mitigation_due_date=None):
    return {
        "risk_id": risk_id, "snapshot_date": pd.Timestamp(date), "exposure": exposure,
        "status": status, "description": description, "category": category,
        "mitigation_due_date": pd.Timestamp(mitigation_due_date) if mitigation_due_date else pd.NaT,
    }


# --- per_risk_trajectory ----------------------------------------------------

def test_per_risk_trajectory_classifies_worsening_improving_stable():
    snapshots = pd.DataFrame([
        _row("R1", "2026-01-01", 5, status="Open"),
        _row("R1", "2026-02-01", 7, status="Open"),   # delta +2 -> Worsening
        _row("R2", "2026-01-01", 6, status="Open"),
        _row("R2", "2026-02-01", 3, status="Open"),   # delta -3 -> Improving
        _row("R3", "2026-01-01", 5, status="Open"),
        _row("R3", "2026-02-01", 5.5, status="Open"),  # delta +0.5 -> Stable
    ])
    out = per_risk_trajectory(snapshots, latest_snapshot=pd.Timestamp("2026-02-01")).set_index("risk_id")

    assert out.loc["R1", "trend"] == "Worsening"
    assert out.loc["R2", "trend"] == "Improving"
    assert out.loc["R3", "trend"] == "Stable"
    assert out.loc["R1", "delta"] == pytest.approx(2)


def test_per_risk_trajectory_dropped_and_closed():
    snapshots = pd.DataFrame([
        # Establishes the panel's latest date via another risk.
        _row("R1", "2026-01-01", 5, status="Open"),
        _row("R1", "2026-02-01", 5, status="Open"),
        # Missing from the latest snapshot, status never says Closed/Resolved.
        _row("R4", "2026-01-01", 4, status="Open"),
        # Missing from the latest snapshot, but its own last status is Closed.
        _row("R5", "2026-01-01", 9, status="Closed"),
    ])
    out = per_risk_trajectory(snapshots, latest_snapshot=pd.Timestamp("2026-02-01")).set_index("risk_id")

    assert out.loc["R4", "trend"] == "Dropped (Unconfirmed)"
    assert out.loc["R5", "trend"] == "Closed/Resolved"


def test_per_risk_trajectory_no_status_column_falls_back_to_closed():
    """With no status data at all, a risk absent from the latest snapshot
    falls back to the old absence-based inference instead of "Dropped"."""
    snapshots = pd.DataFrame([
        {"risk_id": "R1", "snapshot_date": pd.Timestamp("2026-01-01"), "exposure": 5,
         "description": "d", "category": "Technical"},
        {"risk_id": "R1", "snapshot_date": pd.Timestamp("2026-02-01"), "exposure": 5,
         "description": "d", "category": "Technical"},
        {"risk_id": "R6", "snapshot_date": pd.Timestamp("2026-01-01"), "exposure": 3,
         "description": "d", "category": "Technical"},
    ])
    out = per_risk_trajectory(snapshots, latest_snapshot=pd.Timestamp("2026-02-01")).set_index("risk_id")
    assert out.loc["R6", "trend"] == "Closed/Resolved"


# --- mitigation_effectiveness ------------------------------------------------

def test_mitigation_effectiveness_verdicts():
    snapshots = pd.DataFrame([
        # Effective: exposure drops after the mitigation due date.
        _row("R1", "2026-01-01", 10, mitigation_due_date="2026-01-15"),
        _row("R1", "2026-01-20", 4, mitigation_due_date="2026-01-15"),
        # Ineffective: exposure rises after the mitigation due date.
        _row("R2", "2026-01-01", 4, mitigation_due_date="2026-01-15"),
        _row("R2", "2026-01-20", 9, mitigation_due_date="2026-01-15"),
        # Held Steady: exposure unchanged.
        _row("R3", "2026-01-01", 5, mitigation_due_date="2026-01-15"),
        _row("R3", "2026-01-20", 5, mitigation_due_date="2026-01-15"),
        # Too early to assess: no snapshot after the due date yet.
        _row("R4", "2026-01-01", 6, mitigation_due_date="2026-01-15"),
        # Skipped entirely: no mitigation due date recorded at all.
        _row("R5", "2026-01-01", 8),
    ])
    out = mitigation_effectiveness(snapshots).set_index("risk_id")

    assert out.loc["R1", "verdict"] == "Effective"
    assert out.loc["R2", "verdict"] == "Ineffective"
    assert out.loc["R3", "verdict"] == "Held Steady"
    assert out.loc["R4", "verdict"] == "Too early to assess"
    assert "R5" not in out.index


def test_mitigation_effectiveness_uses_most_recent_due_date():
    """A later reschedule of the mitigation deadline must be honored, not the
    earliest recorded due date."""
    snapshots = pd.DataFrame([
        # First reported due date 2026-01-10; rescheduled to 2026-02-10.
        _row("R1", "2026-01-05", 10, mitigation_due_date="2026-01-10"),
        # A snapshot between the two due dates: must count as "before" once
        # the due date is correctly read as the later, rescheduled one.
        _row("R1", "2026-01-20", 10, mitigation_due_date="2026-02-10"),
        _row("R1", "2026-02-15", 3, mitigation_due_date="2026-02-10"),
    ])
    out = mitigation_effectiveness(snapshots).set_index("risk_id")
    assert out.loc["R1", "mitigation_due_date"] == pd.Timestamp("2026-02-10")
    assert out.loc["R1", "avg_exposure_before"] == pytest.approx(10)
    assert out.loc["R1", "verdict"] == "Effective"


# --- _shared_cohort_exposure / risk_trajectory_score ------------------------

def _churn_snapshots():
    """Date1: A(10), B(5). Date2: A(8), C(20) -- B drops out, C is new.
    Raw totals move a lot on register churn alone; the shared cohort (A only)
    is what should drive the score."""
    return pd.DataFrame([
        _row("A", "2026-01-01", 10),
        _row("B", "2026-01-01", 5),
        _row("A", "2026-02-01", 8),
        _row("C", "2026-02-01", 20),
    ])


def test_shared_cohort_exposure_separates_raw_from_churn_controlled():
    cohort = _shared_cohort_exposure(_churn_snapshots())

    assert cohort.first_total == pytest.approx(15)
    assert cohort.last_total == pytest.approx(28)
    assert cohort.pct_change == pytest.approx((28 - 15) / 15 * 100)
    assert cohort.shared_ids == {"A"}
    assert cohort.shared_first_total == pytest.approx(10)
    assert cohort.shared_last_total == pytest.approx(8)
    assert cohort.shared_pct_change == pytest.approx(-20.0)


def test_risk_trajectory_score_uses_shared_exposure_not_raw():
    effectiveness = pd.DataFrame([{"risk_id": "A", "verdict": "Effective"}])
    score = risk_trajectory_score(effectiveness, _churn_snapshots())

    # shared_exposure_pct_change is -20% (improving); the raw figure (+86.7%,
    # inflated by register churn) must NOT be what drives trend_score.
    assert score["exposure_pct_change"] == pytest.approx(86.7, abs=0.1)
    assert score["shared_exposure_pct_change"] == pytest.approx(-20.0)
    assert score["trend_score"] == pytest.approx(50.0)  # improving -> no penalty
    assert score["mitigation_score"] == pytest.approx(50.0)  # 1/1 effective
    assert score["total_score"] == pytest.approx(100.0)


def test_risk_trajectory_score_neutral_mitigation_when_none_assessable():
    stable_snapshots = pd.DataFrame([
        _row("A", "2026-01-01", 10),
        _row("A", "2026-02-01", 10),
    ])
    effectiveness = pd.DataFrame([{"risk_id": "A", "verdict": "Too early to assess"}])
    score = risk_trajectory_score(effectiveness, stable_snapshots)

    assert score["mitigation_score"] == pytest.approx(25.0)  # neutral, none assessable
    assert score["trend_score"] == pytest.approx(50.0)  # 0% change
    assert score["total_score"] == pytest.approx(75.0)
