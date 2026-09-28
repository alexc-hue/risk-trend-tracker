"""Size test for risk-trend-tracker: run by hand, not part of CI or the test suite.

Builds a generated register tracked over six monthly snapshots, with some risks added late and some dropped early at each size, runs `risk_tracker.py` end to end on it in a fresh
Python process, and prints the wall time and peak memory. Everything runs in
a temporary copy of the repo, so assets/ and data/ here are never touched.
Inputs are generated with fixed seeds: the same size always gives the same
files.

    python benchmarks/size_test.py
    python benchmarks/size_test.py --sizes 100 1000

Peak memory needs psutil (pip install psutil) on Windows; without it only
time is shown there. Timings depend on the machine. The measured numbers in
the README's Limitations section say which machine they came from.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIZES = [100, 1000, 5000, 10000]
UNIT = "risks"

CATEGORIES = ["Client Request", "Design", "Environmental", "Logistics", "Procurement", "Engineering"]
SNAPSHOTS = ["2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01"]

def _write(df: pd.DataFrame, data_dir: str, name: str) -> None:
    df.to_csv(os.path.join(data_dir, name), index=False)

def risk_snapshots(n_risks: int, seed: int = 4, keep: pd.DataFrame | None = None) -> pd.DataFrame:
    """n_risks risks over the six monthly snapshots, with churn: some risks
    appear late, some drop out early."""
    rng = random.Random(seed)
    rows = [] if keep is None else keep.to_dict("records")
    kept = 0 if keep is None else keep["risk_id"].nunique()
    for i in range(kept, n_risks):
        first = rng.choice([0, 0, 0, 1, 2])
        last = rng.choice([5, 5, 5, 4, 3])
        p, im = rng.randint(1, 5), rng.randint(1, 5)
        due = SNAPSHOTS[min(5, first + rng.randint(1, 3))]
        for s in range(first, last + 1):
            p = min(5, max(1, p + rng.choice([-1, 0, 0, 1])))
            rows.append({
                "snapshot_date": SNAPSHOTS[s], "risk_id": f"R{i:05d}",
                "description": f"Synthetic risk {i}", "category": rng.choice(CATEGORIES),
                "probability": p, "impact": im,
                "status": "Mitigating" if s > first else "Open", "mitigation_due_date": due,
            })
    return pd.DataFrame(rows)

def generate(n, data_dir, sample_dir):
    _write(risk_snapshots(n), data_dir, "risk_snapshots.csv")

CHILD = r"""
import contextlib, io, json, os, sys, time
os.environ["MPLBACKEND"] = "Agg"
sys.path.insert(0, __ROOT__); os.chdir(__ROOT__)
mod = __import__("risk_tracker")
t0 = time.perf_counter()
with contextlib.redirect_stdout(io.StringIO()):
    mod.main()
seconds = time.perf_counter() - t0
peak_mb = None
try:
    import resource
    kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = kb / 1024 / (1024 if sys.platform == "darwin" else 1)
except ImportError:
    try:
        import psutil
        info = psutil.Process().memory_info()
        peak_mb = getattr(info, "peak_wset", info.rss) / 2**20
    except ImportError:
        pass
print("RESULT" + json.dumps({"seconds": seconds, "peak_mb": peak_mb}))
"""


def run_once(n: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="size-test-"))
    try:
        root = tmp / ROOT.name
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.png"))
        generate(n, str(root / "data"), str(ROOT / "data"))
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run([sys.executable, "-c", CHILD.replace("__ROOT__", repr(str(root)))],
                              capture_output=True, text=True, encoding="utf-8", env=env)
        line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT")), None)
        if line is None:
            return {"error": (proc.stderr.strip().splitlines() or ["no output"])[-1]}
        return json.loads(line[len("RESULT"):])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES, help=f"sizes in {UNIT}")
    args = parser.parse_args()
    print(f"{UNIT:>24}  {'seconds':>9}  {'peak MB':>8}")
    for n in args.sizes:
        result = run_once(n)
        if "error" in result:
            print(f"{n:>24,}  failed: {result['error']}")
            continue
        peak = f"{result['peak_mb']:8.0f}" if result["peak_mb"] is not None else "     n/a"
        print(f"{n:>24,}  {result['seconds']:9.2f}  {peak}", flush=True)


if __name__ == "__main__":
    main()
