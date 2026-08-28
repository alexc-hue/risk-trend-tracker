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

from src import metrics

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

TREND_COLORS = {"Worsening": "#C44E52", "Improving": "#55A868",
                 "Stable": "#8C8C8C", "Closed/Resolved": "#4C72B0"}
VERDICT_COLORS = {"Effective": "#55A868", "Ineffective": "#C44E52", "Too early to assess": "#8C8C8C"}


def print_report(exposure_trend, trajectory, effectiveness, score: dict) -> None:
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
        before = f"{row['avg_exposure_before']:.1f}" if row["avg_exposure_before"] == row["avg_exposure_before"] else "n/a"
        after = f"{row['avg_exposure_after']:.1f}" if row["avg_exposure_after"] == row["avg_exposure_after"] else "n/a"
        print(f"  {row['risk_id']:<5} [{row['verdict']:<18}] "
              f"avg before {before}  avg after {after}  {row['description']}")


def chart_exposure_trend(exposure_trend) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(exposure_trend["snapshot_date"].to_numpy(), exposure_trend["total_exposure"].to_numpy(),
            color="#4C72B0", linewidth=2, marker="o")
    ax.set_ylabel("Total portfolio exposure (sum of probability x impact)")
    ax.set_title("Portfolio Risk Exposure Over Time")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "exposure_trend.png"), dpi=140)
    plt.close(fig)


def chart_trajectory(trajectory) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    label_offsets = {}
    for value, idx in trajectory.groupby("last_exposure").groups.items():
        idx = list(idx)
        span = 0.6
        for j, i in enumerate(idx):
            label_offsets[i] = (j - (len(idx) - 1) / 2) * span if len(idx) > 1 else 0

    for i, row in trajectory.iterrows():
        color = TREND_COLORS[row["trend"]]
        ax.plot([0, 1], [row["first_exposure"], row["last_exposure"]], color=color,
                linewidth=2, marker="o")
        ax.annotate(row["risk_id"], (1.02, row["last_exposure"] + label_offsets[i]), fontsize=8, va="center")
    ax.set_xlim(-0.15, 1.3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["First snapshot", "Latest snapshot"])
    ax.set_ylabel("Exposure (probability x impact)")
    ax.set_title("Per-Risk Trajectory: First vs Latest Exposure")
    handles = [plt.Line2D([0], [0], color=c, linewidth=2, label=k) for k, c in TREND_COLORS.items()]
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "trajectory.png"), dpi=140)
    plt.close(fig)


def chart_effectiveness(effectiveness) -> None:
    ranked = effectiveness.sort_values("risk_id")
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(ranked))
    width = 0.35
    ax.bar([i - width / 2 for i in x], ranked["avg_exposure_before"], width,
           label="Avg exposure before due date", color="#8C8C8C")
    colors = [VERDICT_COLORS[v] for v in ranked["verdict"]]
    ax.bar([i + width / 2 for i in x], ranked["avg_exposure_after"], width,
           label="Avg exposure after due date", color=colors)
    ax.set_xticks(list(x))
    ax.set_xticklabels(ranked["risk_id"])
    ax.set_ylabel("Average exposure")
    ax.set_title("Mitigation Effectiveness (color = verdict on the 'after' bar)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "mitigation_effectiveness.png"), dpi=140)
    plt.close(fig)


def write_report_markdown(exposure_trend, trajectory, effectiveness, score: dict) -> None:
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
            f"| {row['last_exposure']} | {row['category']} | {row['description']} |"
        )

    lines += ["", "## Mitigation Effectiveness", "",
              "| Risk | Verdict | Avg Before | Avg After | Description |",
              "|---|---|---|---|---|"]
    for _, row in effectiveness.iterrows():
        before = f"{row['avg_exposure_before']:.1f}" if row["avg_exposure_before"] == row["avg_exposure_before"] else "n/a"
        after = f"{row['avg_exposure_after']:.1f}" if row["avg_exposure_after"] == row["avg_exposure_after"] else "n/a"
        lines.append(
            f"| {row['risk_id']} | {row['verdict']} | {before} | {after} | {row['description']} |"
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
    score = metrics.risk_trajectory_score(exposure_trend, effectiveness)

    print_report(exposure_trend, trajectory, effectiveness, score)

    chart_exposure_trend(exposure_trend)
    chart_trajectory(trajectory)
    chart_effectiveness(effectiveness)
    write_report_markdown(exposure_trend, trajectory, effectiveness, score)

    print()
    print("-" * 64)
    print(f"Charts and report.md saved to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
