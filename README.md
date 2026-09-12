# Risk Trend & Mitigation Tracker

![CI](https://github.com/alexc-hue/risk-trend-tracker/actions/workflows/tests.yml/badge.svg) [![codecov](https://codecov.io/gh/alexc-hue/risk-trend-tracker/graph/badge.svg)](https://codecov.io/gh/alexc-hue/risk-trend-tracker) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) ![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)

Operationalizes risk management as a tracked trend, not a static register.
Reads a project's risk log as a series of monthly snapshots and answers what
a single point-in-time view can't: is overall exposure rising or falling,
which specific risks are getting worse despite being "in mitigation," and
did each mitigation actually work once its due date passed.

Part of a small project-controls toolkit:
[project-controls-dashboard](https://github.com/alexc-hue/project-controls-dashboard),
[schedule-health-analyzer](https://github.com/alexc-hue/schedule-health-analyzer),
[change-control-register](https://github.com/alexc-hue/change-control-register),
**risk-trend-tracker** (this repo),
[project-controls-reporting-engine](https://github.com/alexc-hue/project-controls-reporting-engine).

![Exposure trend](assets/exposure_trend.png)

## Problem

A risk matrix at a single point in time tells you how bad things look right
now. It doesn't tell you whether that's an improvement or a slide, and it
can't catch the case that matters most in practice: a risk marked
"Mitigating" whose exposure kept climbing anyway. That only shows up when
you track the same risk across multiple reporting periods and actually
compare before-and-after.

## Approach

- Model the risk register as a panel: one row per (risk, snapshot date),
  so the same risk can appear across several monthly reports with different
  probability/impact/status as it evolves, and drop out of later snapshots.
  Probability × impact scoring and mitigation ownership follow standard
  project risk management practice, not a formal ISO 31000 process
  implementation.
- Compute total portfolio exposure at each snapshot date two ways: the raw
  total, and a churn-controlled figure restricted to risks present in both
  the first and latest snapshot, since a portfolio-level total that's really
  just newly-added risks would misstate whether existing risk is actually
  getting better or worse.
- For each risk, compare its first and latest recorded exposure and
  classify it as Worsening, Improving, Stable, or Dropped (Unconfirmed), a
  risk missing from later snapshots is flagged as dropped, not assumed
  resolved, the data doesn't say which.
- For risks with a stated mitigation due date, compare average exposure in
  the snapshots before that date against the snapshots after it, and call
  the mitigation Effective, Ineffective, or Too early to assess if there's
  no snapshot yet past the due date.
- Roll the portfolio trend and mitigation effectiveness into one Risk
  Trajectory Score (unlike the change register tool, exposure trending up
  is unambiguously worse, so a single score is defensible here).

The sample data is eight fictional risks tracked across six monthly
snapshots on an infrastructure project, deliberately mixed: some genuinely
improve, one gets marked "Mitigating" while its exposure keeps rising, and
one is never assigned a mitigation at all and just gets worse.

## Implementation

Built in Python so risk trend tracking is a rerunnable calculation instead
of a manually updated register: pandas for the panel/groupby logic,
matplotlib for the charts.

## Result

```
RISK TREND REPORT
================================================================
Risk Trajectory Score: 35.0 / 100
  - Portfolio exposure trend: 35.0 / 50
  - Mitigation effectiveness: 0.0 / 50

Total exposure, first snapshot: 52
Total exposure, latest snapshot: 75 (+44.2%)
  of which, shared risks only (churn-controlled, 4 risks tracked in both periods): 40 -> 44 (+10.0%) -- this is what the trend score above is based on
Mitigations assessable: 3  Effective: 0
```

A saved copy of this report, including every risk's full trajectory and
mitigation verdict, is generated alongside the charts: see
[assets/report.md](assets/report.md).

## Screenshots

**Portfolio exposure over time** — total risk exposure by snapshot.

![Exposure trend](assets/exposure_trend.png)

**Per-risk trajectory** — first vs. latest exposure per risk, colored by
trend.

![Trajectory](assets/trajectory.png)

**Mitigation effectiveness** — average exposure before vs. after each
risk's mitigation due date.

![Mitigation effectiveness](assets/mitigation_effectiveness.png)

## What I learned

The genuinely useful finding here wasn't the headline exposure number, it
was catching R01: a risk marked "Mitigating" for three straight reporting
periods whose exposure went up anyway. A single-snapshot risk matrix would
have shown "Mitigating" and moved on; only comparing snapshots exposes that
the mitigation didn't work. That's the actual case for tracking a risk
register as a time series instead of a recurring point-in-time exercise.

## Limitations

- "Effective vs. ineffective" is a before/after average comparison, not a
  causal claim, a risk could improve or worsen for reasons unrelated to the
  stated mitigation. Useful as a flag to investigate, not a verdict on its
  own.
- No risk correlation or portfolio-level concentration analysis (whether
  several worsening risks share a common root cause).
- Probability and impact scores come from the PMO's own risk assessment
  process at each snapshot, the tool doesn't generate or validate those
  scores, only tracks how they move. Meant to sit alongside an existing
  RAID log or risk register as the trend layer, not replace it as the
  system of record.

## Run it

```bash
pip install -r requirements.txt
python risk_tracker.py
```

Swap in your own `data/risk_snapshots.csv` (same columns, one row per risk
per reporting period) to point it at a real risk register.
