# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers
follow [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-09-28

Performance at larger sizes. Output is unchanged: the console report and report.md are byte-identical to the previous release on the sample data and on generated inputs, and every chart renders pixel-identical on the sample data, so no committed image changed. The only visible difference is on inputs larger than a chart's cap, where the chart now shows a subset and says so in its title.

### Added

- `benchmarks/size_test.py`, a hand-run size test: generates bigger inputs, runs the tool end to end
  and prints run time and peak memory. Not part of CI or the test suite.
- Measured size-test numbers in the README's Limitations section.
- Tests for the chart caps and for the rewritten metrics against the previous implementations.

### Changed

- per_risk_trajectory and mitigation_effectiveness no longer do pandas work per risk. Same frames,
  row for row; tests compare them exactly against the previous versions.
- The trajectory and mitigation charts show at most 30 risks (largest moves, highest pre-mitigation
  exposure). 10,000 risks went from about 3.5 minutes to about 6 seconds.

## [1.1.0] - 2026-09-28

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

[1.2.0]: https://github.com/alexc-hue/risk-trend-tracker/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/alexc-hue/risk-trend-tracker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/alexc-hue/risk-trend-tracker/releases/tag/v1.0.0
