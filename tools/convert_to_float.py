"""
Generate the single-precision forcing files used by the test cases.

For every `*_double_precision.nc` forcing file under `test_cases/input_data/`,
this writes a matching `*_single_precision.nc` file with the floating-point
data cast to 32-bit (hruId is forced back to an integer if `cdo` floated it).

This is a one-off data-prep tool: the `*_single_precision.nc` files are already
committed to the repo. You only need to re-run it if you add a new test case or
regenerate the double-precision forcing.

Requirements: `cdo` and NCO (`ncap2`) on PATH, and python `netCDF4`.

Usage (from anywhere):
    python3 tools/convert_to_float.py [test_name ...]

With no arguments every test in `test_inventory.json` is processed.
"""
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(REPO_ROOT, "test_cases", "input_data")
INVENTORY = os.path.join(REPO_ROOT, "test_inventory.json")


def hruid_is_float(path):
    from netCDF4 import Dataset  # imported here so --help works without the dep
    ds = Dataset(path)
    try:
        return "hruId" in ds.variables and ds.variables["hruId"].dtype.kind == "f"
    finally:
        ds.close()


def convert_to_float(test_cases):
    for name in test_cases:
        path = os.path.join(INPUT_DIR, name)
        if not os.path.isdir(path):
            print("Skipping (no input_data dir):", name)
            continue
        for fname in sorted(os.listdir(path)):
            if not fname.endswith("_double_precision.nc"):
                continue
            src = os.path.join(path, fname)
            tmp = os.path.join(path, fname.replace("_double_precision", "_f32tmp"))
            dst = os.path.join(path, fname.replace("_double_precision", "_single_precision"))
            print("Converting", os.path.relpath(src, REPO_ROOT), "->", os.path.basename(dst))
            subprocess.check_call(["cdo", "-b", "f32", "copy", src, tmp])
            if hruid_is_float(tmp):
                subprocess.check_call(["ncap2", "-O", "-s", "hruId=int(hruId)", tmp, dst])
                os.remove(tmp)
            else:
                os.replace(tmp, dst)


def main():
    if len(sys.argv) > 1:
        test_cases = sys.argv[1:]
    else:
        with open(INVENTORY) as f:
            test_cases = [t["name"] for t in json.load(f)["tests"]]
    convert_to_float(test_cases)


if __name__ == "__main__":
    main()
