"""
Quantify how much the test-case output changes along one axis of a run.

`summa_test_cases.py run` stamps every output file with a tag built from the
three things a run can vary:

    <outFilePrefix>_<version>_<solver>_<precision>[_<Tag>]_G<a>-<b>_timestep.nc
      version   : non-actors | actors
      solver    : homegrown | ida | kinsol | v3
      precision : single | double
      Tag       : optional free-form string from settings.json

Run the same tests twice, changing exactly one of Version / Solver / Precision
between the runs, then:

    python3 post_scripts/verify_output.py Version      # non-actors vs actors
    python3 post_scripts/verify_output.py Solver       # e.g. homegrown vs ida
    python3 post_scripts/verify_output.py Precision     # single vs double
    python3 post_scripts/verify_output.py Solver celia1990 mizoguchi1990
    python3 post_scripts/verify_output.py Version --per-var

For every test it pairs up the output files that differ only along the chosen
axis (holding the other components fixed) and reports two tables:

  * output values - over all output variables: how many values differ, the
    largest absolute difference, the RMS difference, the largest relative diff.
  * wall time and peak memory - from the time_<subtest>_<suffix>.json the driver
    writes next to each run, with the cmp/ref ratio.

Differences are expected for Solver/Precision, so a difference is not a failure -
the exit status is non-zero only when no comparable pair was found.

Requirements: python `numpy` and `netCDF4` on PATH.
"""
import glob
import json
import math
import os
import re
import sys

import numpy as np
from netCDF4 import Dataset

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(REPO_ROOT, "settings.json")
INVENTORY = os.path.join(REPO_ROOT, "test_inventory.json")
SETTINGS_DIR = os.path.join(REPO_ROOT, "test_cases", "settings")
OUTPUT_DIR = os.path.join(REPO_ROOT, "test_cases", "output")

GROUP_TYPES = ("syntheticTestCases", "multiGruTestCases", "wrrPaperTestCases")

# tag component index for each comparison axis
AXES = {"Version": 0, "Solver": 1, "Precision": 2}

TAG_RE = re.compile(r"_G\d+-\d+_timestep\.nc$")


def load_test_list(requested):
    """Expand a list of test names / group names into inventory entries."""
    with open(INVENTORY) as f:
        tests = json.load(f)["tests"]
    if not requested or "all" in requested:
        return tests
    selected = []
    for name in requested:
        if name in GROUP_TYPES:
            selected += [t for t in tests if t["type"] == name and t not in selected]
        else:
            selected += [t for t in tests if t["name"] == name and t not in selected]
    return selected


def parse_file_manager(path):
    entries = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            m = re.match(r"(\w+)\s+'([^']*)'", line)
            if m:
                entries[m.group(1)] = m.group(2)
    return entries


def parse_output_vars(path):
    variables = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            token = re.split(r"[\s|]+", line)[0]
            if token:
                variables.append(token)
    return variables


def split_tag(fname, prefix):
    """
    "<prefix>_<version>_<solver>_<precision>[_<tag>]_G<a>-<b>_timestep.nc"
    -> (version, solver, precision, tag)   or None if it does not match.
    """
    if not fname.startswith(prefix + "_") or not TAG_RE.search(fname):
        return None
    middle = TAG_RE.sub("", fname[len(prefix) + 1:])
    parts = middle.split("_")
    if len(parts) < 3:
        return None
    return parts[0], parts[1], parts[2], "_".join(parts[3:])


def tag_string(comps):
    """Rebuild the driver's -s suffix from split_tag() components."""
    return "_".join(c for c in comps if c)


def load_run_stats(test_name, sub_test, tag_str):
    """Read the time_<subtest>_<suffix>.json the driver wrote next to the output."""
    path = os.path.join(OUTPUT_DIR, test_name, f"time_{sub_test}_{tag_str}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _as_float(ncvar):
    return np.ma.filled(ncvar[:].astype("float64"), np.nan)


def compare_files(ref_file, cmp_file, variables, per_var):
    """Aggregate |ref - cmp| over all listed variables that both files carry."""
    ref = Dataset(ref_file)
    cmp = Dataset(cmp_file)
    n_total = n_diff = 0
    sum_abs = sumsq = 0.0
    max_abs = max_rel = 0.0
    for var in variables:
        if var not in ref.variables or var not in cmp.variables:
            continue
        a = _as_float(ref.variables[var])
        b = _as_float(cmp.variables[var])
        if a.shape != b.shape:
            print(f"    {var}: SHAPE MISMATCH {a.shape} vs {b.shape}")
            continue
        d = np.abs(a - b)
        d = np.where(np.isnan(d), 0.0, d)
        denom = np.where(np.abs(a) > 0, np.abs(a), np.nan)
        rel = d / denom
        v_max = float(d.max()) if d.size else 0.0
        v_rel = float(np.nanmax(rel)) if np.isfinite(rel).any() else 0.0
        n_total += d.size
        n_diff += int(np.count_nonzero(d))
        sum_abs += float(d.sum())
        sumsq += float((d * d).sum())
        max_abs = max(max_abs, v_max)
        max_rel = max(max_rel, v_rel)
        if per_var and v_max > 0:
            print(f"    {var:<28} ndiff={int(np.count_nonzero(d)):>7}  "
                  f"max|d|={v_max:.3e}  maxrel={v_rel:.3e}")
    ref.close()
    cmp.close()
    mean_abs = sum_abs / n_total if n_total else 0.0
    rms = math.sqrt(sumsq / n_total) if n_total else 0.0
    return dict(n_total=n_total, n_diff=n_diff, max_abs=max_abs,
                mean_abs=mean_abs, rms=rms, max_rel=max_rel)


def main():
    args = [a for a in sys.argv[1:] if a != "--per-var"]
    per_var = "--per-var" in sys.argv[1:]
    if not args or args[0] not in AXES:
        print("usage: verify_output.py <Version|Solver|Precision> [test ...] [--per-var]")
        return 1
    axis = args[0]
    idx = AXES[axis]

    with open(SETTINGS) as f:
        settings = json.load(f)
    requested = args[1:] or settings.get("Test_List", [])
    test_list = load_test_list(requested)

    rows = []
    n_pairs = 0

    for test in test_list:
        test_name, test_type = test["name"], test["type"]
        fm_dir = os.path.join(SETTINGS_DIR, test_type, test_name, "fileManagers")
        if not os.path.isdir(fm_dir):
            continue
        for fm_name in sorted(os.listdir(fm_dir)):
            # read the committed templates, not the generated *_test.txt (which
            # only exist right after a run); outFilePrefix is literal in both
            if (not fm_name.startswith("fileManager_") or not fm_name.endswith(".txt")
                    or fm_name.endswith("_test.txt")):
                continue
            sub_test = re.match(r"fileManager_(.+)\.txt$", fm_name).group(1)
            fm = parse_file_manager(os.path.join(fm_dir, fm_name))
            prefix = fm.get("outFilePrefix")
            oc_rel = fm.get("outputControlFile")
            if not prefix or not oc_rel:
                print(f"WARNING: could not read {fm_name}, skipping")
                continue
            oc_path = os.path.join(SETTINGS_DIR, oc_rel)
            if not os.path.isfile(oc_path):
                print(f"WARNING: output-control file missing for {prefix}: {oc_path}")
                continue
            variables = parse_output_vars(oc_path)

            # group this test's output files by everything except the chosen axis
            groups = {}
            out_glob = os.path.join(OUTPUT_DIR, test_name, prefix + "_*_timestep.nc")
            for path in sorted(glob.glob(out_glob)):
                comps = split_tag(os.path.basename(path), prefix)
                if comps is None:
                    continue
                key = tuple(c for i, c in enumerate(comps) if i != idx)
                groups.setdefault(key, {})[comps[idx]] = path

            for key, by_axis in sorted(groups.items()):
                if len(by_axis) < 2:
                    continue
                held = " ".join(k for k in key if k)
                values = sorted(by_axis)
                ref_val = values[0]
                for cmp_val in values[1:]:
                    n_pairs += 1
                    label = f"{test_name}/{prefix}"
                    if per_var:
                        print(f"\n{label}  [{held}]  {ref_val} vs {cmp_val}")
                    ref_path, cmp_path = by_axis[ref_val], by_axis[cmp_val]
                    stats = compare_files(ref_path, cmp_path, variables, per_var)
                    ref_rs = load_run_stats(test_name, sub_test,
                                            tag_string(split_tag(os.path.basename(ref_path), prefix)))
                    cmp_rs = load_run_stats(test_name, sub_test,
                                            tag_string(split_tag(os.path.basename(cmp_path), prefix)))
                    rows.append((label, held, f"{ref_val} vs {cmp_val}", stats, ref_rs, cmp_rs))

    if not rows:
        print(f"No comparable pairs for axis '{axis}'. Run the tests twice, "
              f"changing only {axis} between runs.")
        return 1

    print(f"\n{axis} comparison  -  output values")
    print(f"{'test / prefix':<40}{'held fixed':<20}{'compared':<24}"
          f"{'ndiff':>10}{'max|d|':>12}{'rms':>12}{'maxrel':>12}")
    print("-" * 130)
    for label, held, comp, s, _r, _c in rows:
        print(f"{label:<40}{held:<20}{comp:<24}"
              f"{s['n_diff']:>10}{s['max_abs']:>12.3e}{s['rms']:>12.3e}{s['max_rel']:>12.3e}")

    print(f"\n{axis} comparison  -  wall time (s) and peak memory (MB)")
    print(f"{'test / prefix':<40}{'held fixed':<20}{'compared':<24}"
          f"{'t.ref':>9}{'t.cmp':>9}{'t.cmp/ref':>11}{'mem.ref':>10}{'mem.cmp':>10}{'mem c/r':>9}")
    print("-" * 142)

    def ratio(a, b):
        return f"{b / a:>.2f}x" if a else "  n/a"

    for label, held, comp, _s, r, c in rows:
        if not r or not c:
            print(f"{label:<40}{held:<20}{comp:<24}  missing time_*.json")
            continue
        print(f"{label:<40}{held:<20}{comp:<24}"
              f"{r['wall_s']:>9.2f}{c['wall_s']:>9.2f}{ratio(r['wall_s'], c['wall_s']):>11}"
              f"{r['max_rss_mb']:>10.1f}{c['max_rss_mb']:>10.1f}{ratio(r['max_rss_mb'], c['max_rss_mb']):>9}")
    print("-" * 142)
    print(f"pairs compared: {n_pairs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
