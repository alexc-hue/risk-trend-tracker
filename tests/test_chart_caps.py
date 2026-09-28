"""The charts cap themselves at CHART_TOP_N risks; the reports don't."""

from __future__ import annotations

import pandas as pd

import risk_tracker


def test_trajectory_chart_keeps_the_largest_moves_in_order():
    trajectory = pd.DataFrame({"risk_id": [f"R{i}" for i in range(100)],
                               "delta": [(-1) ** i * i for i in range(100)]})
    shown = risk_tracker._largest_moves(trajectory)
    assert len(shown) == risk_tracker.CHART_TOP_N
    assert set(shown["delta"].abs()) == set(range(70, 100))
    assert list(shown.index) == sorted(shown.index)


def test_effectiveness_chart_keeps_the_highest_pre_mitigation_exposure():
    eff = pd.DataFrame({"risk_id": [f"R{i}" for i in range(50)],
                        "avg_exposure_before": [float(i) if i % 5 else float("nan") for i in range(50)]})
    shown = risk_tracker._highest_before(eff)
    assert len(shown) == risk_tracker.CHART_TOP_N
    assert shown["avg_exposure_before"].notna().all()


def test_small_registers_are_charted_in_full():
    small = pd.DataFrame({"risk_id": ["R1", "R2"], "delta": [1, -3], "avg_exposure_before": [1.0, 2.0]})
    assert risk_tracker._largest_moves(small).equals(small)
    assert risk_tracker._highest_before(small).equals(small)
