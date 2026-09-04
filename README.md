# SUMMA Test Cases

A testing framework for SUMMA and SUMMA-Actors. It runs a set of small,
fast-running test cases through one or more SUMMA executables and compares the
output, so you can check that a code change (or the actors vs non-actors build)
does not change the results. It expands on
<https://github.com/CH-Earth/laughTests>.

Everything is driven by `summa_test_cases.py` together with the `settings.json`
configuration file.

## Directory structure

```
summa_test_cases
├── summa_test_cases.py     driver: run / clean
├── settings.json           user configuration (see below)
├── test_inventory.json     the list of available test cases
├── test_cases
│   ├── input_data          forcing data for each test (single + double precision)
│   ├── settings            per-test settings + file-manager templates
│   └── output              created by `run`; holds run output and logs (gitignored)
├── post_scripts
│   ├── verify_output.py    quantify output / time / memory changes along one axis
│   └── timing_info.py      gather every run's time + memory into timing_info.csv
├── tools
│   └── convert_to_float.py regenerate the single-precision forcing files
├── summa_actors_config.json  config passed to the "actors" executable
└── reference               SUMMA modelDecisions templates (v3 and v4)
```

## Installing

```bash
git clone https://github.com/CH-Earth/summa_test_cases.git
```

You also need a compiled SUMMA and/or SUMMA-Actors executable. See
<https://summa.readthedocs.io/en/latest/SUMMA_documentation/> and the
SUMMA-Actors framework.

## Configuration (`settings.json`)

| Key | Meaning |
| --- | --- |
| `Test_List` | List of tests to run. Use any `name` from `test_inventory.json`, or a group: `"syntheticTestCases"`, `"wrrPaperTestCases"`, `"multiGruTestCases"`, or `"all"`. The multiGru tests take much longer than the rest. |
| `Solver` | `homegrown`, `ida`, or `kinsol` for SUMMA v4, or `v3` for older builds. Selects which `summa_zDecisions_<Solver>.txt` the file manager points at. |
| `Precision` | `single` or `double`. Selects which forcing file list (and therefore which forcing `.nc`) the file manager points at. |
| `Version` | `non-actors` or `actors`. Picks the executable from `Executables`; `actors` also gets `-c summa_actors_config.json`. |
| `Executables` | Map of `Version` → executable path. List both to compare, or just the one you use. |
| `Tag` | Optional free-form string added to the output name. Bump it to keep an otherwise-identical rerun (e.g. after a rebuild) from overwriting the previous one. |

`Version`, `Solver` and `Precision` are the three axes you can vary and compare.
Any of them can be set in `settings.json` or overridden per run on the command
line (`run actors ida double`).
Every output file is stamped with all three (plus `Tag` if set):

```
<outFilePrefix>_<Version>_<Solver>_<Precision>[_<Tag>]_G<a>-<b>_timestep.nc
```

so runs that differ in any of them sit side by side in `test_cases/output`.

Example (`settings.json`):

```json
{
    "Test_List": ["syntheticTestCases", "wrrPaperTestCases", "northamerica2005"],
    "Solver": "homegrown",
    "Precision": "single",
    "Version": "non-actors",
    "Executables": {
        "non-actors": "/path/to/summa/bin/summa_sundials.exe",
        "actors": "/path/to/summa-actors/bin/summa_actors.exe"
    }
}
```

The driver runs, per test:

```
non-actors:  <exe> -m <fileManager> -s <suffix> -g 1 <nGRU>
actors:      <exe> -m <fileManager> -s <suffix> -c summa_actors_config.json -g 1 <nGRU>
```

where `<suffix>` is `<Version>_<Solver>_<Precision>[_<Tag>]`.

`-m` always overrides the `file_manager_path` inside `summa_actors_config.json`,
so the generated file managers are what actually get run.

## Running

```bash
python3 summa_test_cases.py run              # run Test_List with settings.json Version/Solver/Precision
python3 summa_test_cases.py run actors       # override an axis for this run (any of Version/Solver/Precision)
python3 summa_test_cases.py run ida
python3 summa_test_cases.py run actors ida double
python3 summa_test_cases.py clean            # delete generated output and file managers
```

`run` creates the output dirs and regenerates the `fileManager_<subtest>_test.txt`
for its effective `Version` / `Solver` / `Precision` every time, so **just pass
the axis you want** — `run actors`, `run ida`, `run single`, or any combination.
The value sets do not overlap, so the driver knows which axis each token is.

`run` never deletes existing output — only `clean` does — so runs accumulate.
The generated `*_test.txt` files and `test_cases/output` are gitignored.

Each `run` also times each test and records its peak memory, writing a
`time_<subtest>_<suffix>.json` next to the test's output.

## Comparing along an axis

Run the tests twice, changing exactly one of `Version` / `Solver` / `Precision`,
then ask `verify_output.py` about that axis:

```bash
python3 summa_test_cases.py run homegrown
python3 summa_test_cases.py run ida
python3 post_scripts/verify_output.py Solver
```

Every axis works the same way:

```bash
python3 summa_test_cases.py run non-actors && python3 summa_test_cases.py run actors
python3 post_scripts/verify_output.py Version

python3 summa_test_cases.py run single && python3 summa_test_cases.py run double
python3 post_scripts/verify_output.py Precision

python3 post_scripts/verify_output.py Solver celia1990 mizoguchi1990   # only some tests
python3 post_scripts/verify_output.py Version --per-var                # per-variable breakdown
```

For each test, `verify_output.py` pairs the output files that differ only along
the chosen axis (holding the other components fixed) and prints two tables:

* **output values** — over all output variables: number of differing values,
  largest absolute difference, RMS difference, largest relative difference.
* **wall time and peak memory** — from the `time_*.json` files, with the
  `cmp/ref` ratio.

Differences are expected for `Solver` / `Precision`, so a difference is not a
failure — exit status is non-zero only when no comparable pair was found.
Requires python `numpy` and `netCDF4`.

### All timings at once

```bash
python3 post_scripts/timing_info.py           # -> timing_info.csv (repo root)
python3 post_scripts/timing_info.py celia1990  # filter to some tests
```

gathers every `time_*.json` into one CSV: test, subtest, version, solver,
precision, tag, wall_s, max_rss_mb, returncode.

## Regenerating single-precision forcing

The `*_single_precision.nc` forcing files are committed. If you add a test case
or change the double-precision forcing, regenerate them with:

```bash
python3 tools/convert_to_float.py            # all tests in test_inventory.json
python3 tools/convert_to_float.py celia1990  # or specific tests
```

Requires `cdo`, NCO (`ncap2`) and python `netCDF4`.

## Note on parameters

The v4 parameters are left out of the `summa_zLocalParamInfo.txt` files so that
SUMMA v3 will run. To use them, add the following lines (and adjust as desired).
`be_steps` applies to all v4 solver choices; the `rel*` / `abs*` tolerances only
apply to `Solver` = `ida`. The values below are the recommended ones for
`nrgConserv = closedForm`; for `enthalpyForm` the `absTolTemp*` values should be
`1.0e2` instead of `1.0e-3`.

```
be_steps                  |       1.0000 |       1.0000 |     512.0000
relTolTempCas             |       1.0d-5 |       1.0d-10|       1.0d-1
absTolTempCas             |       1.0d-3 |       1.0d-10|       1.0d-1
relTolTempVeg             |       1.0d-5 |       1.0d-10|       1.0d-1
absTolTempVeg             |       1.0d-3 |       1.0d-10|       1.0d-1
relTolWatVeg              |       1.0d-5 |       1.0d-10|       1.0d-1
absTolWatVeg              |       1.0d-5 |       1.0d-10|       1.0d-1
relTolTempSoilSnow        |       1.0d-5 |       1.0d-10|       1.0d-1
absTolTempSoilSnow        |       1.0d-3 |       1.0d-10|       1.0d-1
relTolWatSnow             |       1.0d-5 |       1.0d-10|       1.0d-1
absTolWatSnow             |       1.0d-5 |       1.0d-10|       1.0d-1
relTolMatric              |       1.0d-5 |       1.0d-10|       1.0d-1
absTolMatric              |       1.0d-5 |       1.0d-10|       1.0d-1
relTolAquifr              |       1.0d-5 |       1.0d-10|       1.0d-1
absTolAquifr              |       1.0d-5 |       1.0d-10|       1.0d-1
```
