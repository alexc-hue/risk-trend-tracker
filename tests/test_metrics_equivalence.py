"""per_risk_trajectory and mitigation_effectiveness were rewritten in 1.2.0 to
avoid per-risk pandas work. Their output has to be exactly what the previous
versions produced, which are kept in tests/_reference_metrics.py.
"""

from __future__ import annotations

import random

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src import metrics
from tests import _reference_metrics as reference

DATES = pd.to_datetime(["2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01"])


def _snapshots(n_risks: int, seed: int, with_status: bool = True, edge_cases: bool = False) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for i in range(n_risks):
        first, last = rng.choice([0, 0, 1, 2]), rng.choice([5, 5, 4, 3])
        due = rng.choice([pd.NaT, *DATES]) if edge_cases else DATES[min(5, first + rng.randint(1, 3))]
        for s in range(first, last + 1):
            p, im = rng.randint(1, 5), rng.randint(1, 5)
            row = {
                "snapshot_date": DATES[s], "risk_id": f"R{i:03d}", "description": f"risk {i}",
                "category": rng.choice(["A", "B"]), "probability": p, "impact": im,
                "status": rng.choice(["Open", "Mitigating", "Closed", " resolved ", None]),
                "mitigation_due_date": due if rng.random() > 0.2 or not edge_cases else pd.NaT,
            }
            if not with_status:
                del row["status"]
            rows.append(row)
    df = pd.DataFrame(rows)
    df["exposure"] = df["probability"] * df["impact"]
    if edge_cases:
        df.loc[df.sample(frac=0.1, random_state=seed).index, "exposure"] = np.nan
    return df.sort_values(["risk_id", "snapshot_date"]).reset_index(drop=True)


CASES = [(40, 1, True, False), (300, 2, True, False), (300, 3, False, False), (300, 4, True, True),
         (300, 5, False, True)]


@pytest.mark.parametrize(("n", "seed", "with_status", "edge_cases"), CASES)
def test_per_risk_trajectory_matches_reference(n, seed, with_status, edge_cases):
    snaps = _snapshots(n, seed, with_status, edge_cases)
    latest = snaps["snapshot_date"].max()
    assert_frame_equal(metrics.per_risk_trajectory(snaps, latest),
                       reference.per_risk_trajectory(snaps, latest), check_exact=True)


@pytest.mark.parametrize(("n", "seed", "with_status", "edge_cases"), CASES)
def test_mitigation_effectiveness_matches_reference(n, seed, with_status, edge_cases):
    snaps = _snapshots(n, seed, with_status, edge_cases)
    assert_frame_equal(metrics.mitigation_effectiveness(snaps),
                       reference.mitigation_effectiveness(snaps), check_exact=True)
