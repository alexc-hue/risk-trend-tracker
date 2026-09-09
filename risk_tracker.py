"""
Risk Trend & Mitigation Tracker
---------------------------------
Reads a project's risk register as a panel of monthly snapshots (not a
single point-in-time list) and answers what a single snapshot can't: is
total risk exposure rising or falling, which individual risks are getting
worse despite being "mitigated," and did each mitigation actually work.

Run:
    pip install -r requirements.txt
    python risk_tracker.py
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

from src import chart_style, metrics

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Worsening/Stable/Improving is a severity trend, so it takes the status scale.
# "Closed/Resolved" isn't a severity level (a resolved risk isn't "critical" or
# "good", it's simply no longer active) so it keeps its own categorical color,
# same role the old ad-hoc blue played here. "Dropped (Unconfirmed)" is a risk
# that stopped being reported without the register's status field ever saying
# it was closed/resolved -- neither a severity reading nor a confirmed closure,
# so it shares the neutral/needs-attention amber used for "Stable".
TREND_COLORS = {"Worsening": chart_style.STATUS_CRITICAL, "Improving": chart_style.STATUS_GOOD,
                 "Stable": chart_style.STATUS_WARNING, "Closed/Resolved": chart_style.SERIES_1,
                 "Dropped (Unconfirmed)": chart_style.STATUS_WARNING}
# "Held Steady" is the neutral outcome for exposure that neither improved nor
# worsened -- it shares "Too early to assess"'s amber rather than being forced
# into "Ineffective".
VERDICT_COLORS = {"Effective": chart_style.STATUS_GOOD, "Ineffective": chart_style.STATUS_CRITICAL,
                   "Too early to assess": chart_style.STATUS_WARNING, "Held Steady": chart_style.STATUS_WARNING}


def _fmt_avg(value: float) -> str:
    """Format an average-exposure figure, or 'n/a' if it's NaN (no before/after window to average)."""
    return f"{value:.1f}" if pd.notna(value) else "n/a"


def print_report(trajectory, effectiveness, score: dict) -> None:
    print("=" * 64)
    print("RISK TREND REPORT")
    print("=" * 64)
    print(f"Risk Trajectory Score: {score['total_score']} / 100")
    print(f"  - Portfolio exposure trend: {score['trend_score']} / 50")
    print(f"  - Mitigation effectiveness: {score['mitigation_score']} / 50")
    print()
    print(f"Total exposure, first snapshot: {score['first_total_exposure']}")
    print(f"Total exposure, latest snapshot: {score['last_total_exposure']} "
          f"({score['exposure_pct_change']:+.1f}%)")
    print(f"  of which, shared risks only (churn-controlled, {score['shared_risk_count']} risks "
          f"tracked in both periods): {score['shared_first_exposure']} -> {score['shared_last_exposure']} "
          f"({score['shared_exposure_pct_change']:+.1f}%) -- this is what the trend score above is based on")
    print(f"Mitigations assessable: {score['assessable_mitigations']}  "
          f"Effective: {score['effective_mitigations']}")

    print()
    print("-" * 64)
    print("PER-RISK TRAJECTORY (first snapshot -> latest)")
    print("-" * 64)
    for _, row in trajectory.iterrows():
        print(f"  {row['risk_id']:<5} [{row['trend']:<15}] "
              f"{row['first_exposure']:>2} -> {row['last_exposure']:>2}  "
              f"({row['category']})  {row['description']}")

    print()
    print("-" * 64)
    print("MITIGATION EFFECTIVENESS")
    print("-" * 64)
    for _, row in effectiveness.iterrows():
        before = _fmt_avg(row["avg_exposure_before"])
        after = _fmt_avg(row["avg_exposure_after"])
        print(f"  {row['risk_id']:<5} [{row['verdict']:<18}] "
              f"avg before {before}  avg after {after}  {row['description']}")


def chart_exposure_trend(exposure_trend) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(exposure_trend["snapshot_date"].to_numpy(), exposure_trend["total_exposure"].to_numpy(),
            color=chart_style.SERIES_1, linewidth=2, marker="o")
    ax.set_ylabel("Total portfolio exposure (sum of probability x impact)")
    ax.set_title("Portfolio Risk Exposure Over Time")
    ax.grid(color=chart_style.GRID, linewidth=0.6)
    chart_style.apply_chrome(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "exposure_trend.png"), dpi=140, facecolor=chart_style.CHART_BG)
    plt.close(fig)


def chart_trajectory(trajectory) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    span = 0.6
    # Keyed by risk_id (the actual business key) rather than positional/index
    # label, so this doesn't silently depend on per_risk_trajectory happening
    # to end with reset_index(drop=True) upstream.
    label_offsets = {}
    for _, group in trajectory.groupby("last_exposure"):
        risk_ids = list(group["risk_id"])
        for j, risk_id in enumerate(risk_ids):
            label_offsets[risk_id] = (j - (len(risk_ids) - 1) / 2) * span

    for row in trajectory.itertuples():
        color = TREND_COLORS[row.trend]
        ax.plot([0, 1], [row.first_exposure, row.last_exposure], color=color,
                linewidth=2, marker="o")
        ax.annotate(row.risk_id, (1.02, row.last_exposure + label_offsets[row.risk_id]), fontsize=8, va="center")
    ax.set_xlim(-0.15, 1.3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["First snapshot", "Latest snapshot"])
    ax.set_ylabel("Exposure (probability x impact)")
    ax.set_title("Per-Risk Trajectory: First vs Latest Exposure")
    handles = [plt.Line2D([0], [0], color=c, linewidth=2, label=k) for k, c in TREND_COLORS.items()]
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.grid(color=chart_style.GRID, linewidth=0.6, axis="y")
    chart_style.apply_chrome(fig, ax)
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "trajectory.png"), dpi=140, facecolor=chart_style.CHART_BG)
    plt.close(fig)


def chart_effectiveness(effectiveness) -> None:
    ranked = effectiveness.sort_values("risk_id")
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(ranked))
    width = 0.35
    ax.bar([i - width / 2 for i in x], ranked["avg_exposure_before"], width, color=chart_style.BASELINE)
    colors = [VERDICT_COLORS[v] for v in ranked["verdict"]]
    ax.bar([i + width / 2 for i in x], ranked["avg_exposure_after"], width, color=colors)
    ax.set_xticks(list(x))
    ax.set_xticklabels(ranked["risk_id"])
    ax.set_ylabel("Average exposure")
    ax.set_title("Mitigation Effectiveness (color = verdict on the 'after' bar)")
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax * 1.3)  # headroom so the legend doesn't sit on top of the tallest bar
    handles = [plt.Rectangle((0, 0), 1, 1, color=chart_style.BASELINE, label="Avg exposure before due date")]
    handles += [plt.Rectangle((0, 0), 1, 1, color=c, label=k) for k, c in VERDICT_COLORS.items()]
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.grid(color=chart_style.GRID, linewidth=0.6, axis="y")
    chart_style.apply_chrome(fig, ax)
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "mitigation_effectiveness.png"), dpi=140, facecolor=chart_style.CHART_BG)
    plt.close(fig)


def _escape_md_cell(value) -> str:
    """Escape/normalize a free-text value so it can't corrupt a markdown table.

    A raw `|` splits into extra columns, a backslash can escape the delimiter
    that follows it, and embedded newlines break the row onto multiple lines.
    """
    if value is None or value != value:  # covers None and NaN (NaN != NaN)
        return ""
    text = str(value)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    return text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def write_report_markdown(trajectory, effectiveness, score: dict) -> None:
    lines = [
        "# Risk Trend Report",
        "",
        f"**Risk Trajectory Score: {score['total_score']} / 100**",
        "",
        "| Component | Score |",
        "|---|---|",
        f"| Portfolio exposure trend | {score['trend_score']} / 50 |",
        f"| Mitigation effectiveness | {score['mitigation_score']} / 50 |",
        "",
        f"**Total exposure, first snapshot:** {score['first_total_exposure']}  ",
        f"**Total exposure, latest snapshot:** {score['last_total_exposure']} "
        f"({score['exposure_pct_change']:+.1f}%)  ",
        f"**Shared risks only (churn-controlled, {score['shared_risk_count']} risks tracked in both "
        f"periods):** {score['shared_first_exposure']} -> {score['shared_last_exposure']} "
        f"({score['shared_exposure_pct_change']:+.1f}%) -- basis for the trend score above  ",
        f"**Mitigations assessable:** {score['assessable_mitigations']}   "
        f"**Effective:** {score['effective_mitigations']}",
        "",
        "## Per-Risk Trajectory",
        "",
        "| Risk | Trend | First | Latest | Category | Description |",
        "|---|---|---|---|---|---|",
    ]
    for _, row in trajectory.iterrows():
        lines.append(
            f"| {row['risk_id']} | {row['trend']} | {row['first_exposure']} "
            f"| {row['last_exposure']} | {_escape_md_cell(row['category'])} "
            f"| {_escape_md_cell(row['description'])} |"
        )

    lines += ["", "## Mitigation Effectiveness", "",
              "| Risk | Verdict | Avg Before | Avg After | Description |",
              "|---|---|---|---|---|"]
    for _, row in effectiveness.iterrows():
        before = _fmt_avg(row["avg_exposure_before"])
        after = _fmt_avg(row["avg_exposure_after"])
        lines.append(
            f"| {row['risk_id']} | {row['verdict']} | {before} | {after} "
            f"| {_escape_md_cell(row['description'])} |"
        )
    lines.append("")

    with open(os.path.join(ASSETS_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)

    snapshots = metrics.load_snapshots(os.path.join(DATA_DIR, "risk_snapshots.csv"))
    exposure_trend = metrics.portfolio_exposure_trend(snapshots)
    latest_snapshot = snapshots["snapshot_date"].max()
    trajectory = metrics.per_risk_trajectory(snapshots, latest_snapshot)
    effectiveness = metrics.mitigation_effectiveness(snapshots)
    score = metrics.risk_trajectory_score(effectiveness, snapshots)

    print_report(trajectory, effectiveness, score)

    chart_exposure_trend(exposure_trend)
    chart_trajectory(trajectory)
    chart_effectiveness(effectiveness)
    write_report_markdown(trajectory, effectiveness, score)

    print()
    print("-" * 64)
    print(f"Charts and report.md saved to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
