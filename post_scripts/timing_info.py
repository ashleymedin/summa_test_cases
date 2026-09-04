"""
Collect the per-run wall time and peak memory into one CSV.

`summa_test_cases.py run` drops a `time_<subtest>_<suffix>.json` next to every
test's output (`test_cases/output/<test>/`). This script gathers them all into
`timing_info.csv` (written to the repo root), newest column layout:

    test, subtest, version, solver, precision, tag, wall_s, max_rss_mb, returncode

Usage (from anywhere):
    python3 post_scripts/timing_info.py [test_name ...]

With no arguments every test is included; names filter to those tests.
"""
import csv
import glob
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(REPO_ROOT, "test_cases", "output")
CSV_PATH = os.path.join(REPO_ROOT, "timing_info.csv")

FIELDS = ["test", "subtest", "version", "solver", "precision", "tag",
          "wall_s", "max_rss_mb", "returncode"]


def main():
    wanted = set(sys.argv[1:])
    rows = []
    for path in sorted(glob.glob(os.path.join(OUTPUT_DIR, "*", "time_*.json"))):
        try:
            with open(path) as f:
                rec = json.load(f)
        except (OSError, ValueError):
            print("skipping unreadable", path)
            continue
        if wanted and rec.get("test") not in wanted:
            continue
        rows.append(rec)

    rows.sort(key=lambda r: (r.get("test", ""), r.get("subtest", ""), r.get("suffix", "")))

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in rows:
            writer.writerow(rec)

    print(f"wrote {len(rows)} rows to {CSV_PATH}")
    if not rows:
        print("(no time_*.json found - run `summa_test_cases.py run` first)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
