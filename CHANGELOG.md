# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers
follow [Semantic Versioning](https://semver.org/).

## [1.1.0] - Unreleased

Checks and tests only. The tool's output is unchanged.

### Added

- A test that runs `risk_tracker.py` end to end on the sample data and checks the README's Result block against what it actually prints, so the README can't drift from the code.
- A check that the committed `assets/report.md` is exactly what the script regenerates.
- Regression tests for the missing-value check fixed before 1.0.0: a missing average prints "n/a" for None and pd.NA as well as NaN.
- A test that pins the chart colors and styling shared across all six toolkit repos.
- ruff linting, run locally from `ruff.toml` and as its own CI job.
- CI now tests on Python 3.11 and 3.12, matching the "Python 3.11+" badge.
- `.gitattributes` keeps line endings consistent (LF) on every OS.

## [1.0.0] - 2026-09-13

First tagged release, marking the state of the repo before this changelog started. Risk exposure tracked across snapshots: portfolio trend (churn-controlled), per-risk trajectory and mitigation effectiveness, rolled into a Risk Trajectory Score, with charts and a markdown report. Includes the fixes from code review, a pytest suite and CI.

[1.1.0]: https://github.com/alexc-hue/risk-trend-tracker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/alexc-hue/risk-trend-tracker/releases/tag/v1.0.0
