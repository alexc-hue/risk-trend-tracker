"""Regression tests for the NaN-check bug fixed in commit 6107925.

The report used to test for a missing average with row["x"] == row["x"],
which only works for a float NaN. A None or pd.NA (what pandas produces for
a missing value in a nullable column) raised a TypeError instead of
printing "n/a". The None and pd.NA cases were confirmed to fail with the
fix temporarily reverted (the float NaN case passes either way and is kept
as a baseline).
"""

from __future__ import annotations

import pandas as pd
import pytest

from risk_tracker import _fmt_avg


@pytest.mark.parametrize("missing", [float("nan"), None, pd.NA])
def test_missing_average_prints_n_a(missing):
    assert _fmt_avg(missing) == "n/a"


def test_real_average_prints_one_decimal():
    assert _fmt_avg(12.345) == "12.3"
