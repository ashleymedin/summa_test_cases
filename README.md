# Summa Test Cases
This repository serves as a testing framework for SUMMA and Summa-Actors, designed to validate the integrity of the test cases and facilitate the comparison of different SUMMA versions, expanding on https://github.com/CH-Earth/laughTests.
The framework operates via a `summa_test_cases.py` script, which, in conjunction with the `settings.json` configuration file, orchestrates the testing procedures.


## Installing the Summa Test Cases
To install the testing framework, execute the following command:
```bash
git clone https://github.com/CH-Earth/summa_test_cases/summa_test_cases.git 
```

## Directory Structure
The directory structure of the summa_test_cases repository is as follows:
```bash
|-- summa_test_cases
   | -- post_scripts
   | -- run_scripts
   | -- test_cases
      | -- input_data
      | -- settings
      | -- output
   | -- utils
   | -- .gitignore
   | -- summa_test_cases.py
   | -- README.md
   | -- settings.json
   | -- test_inventory.json
```

The `test_cases` directory will contain all the data for each of the available 
tests. Within the `test_cases` directory, the `input_data` directory will contain the forcing data for each test, the `settings` directory will contain the file manager files for each test, and the `output` directory will be created when the tests are run.

## Running the Summa Test Cases
To run the test cases first you must install and compile SUMMA. This can be done with the documentation found here https://summa.readthedocs.io/en/latest/SUMMA_documentation/.

Once you have installed summa you can now set up the test cases. The test cases are configured through the `test_settings.json` file included in the summa_test_cases repository. This file will need to be modified to work in your environment and to run the specific tests you desire. The settings are configured by the user by modifying the value of the key-value pairs in the `test_settings.json` file. Detailed explanations of the key-value pairs are provided below:

 - Test_List: This is a the list of test you wish to run. The directories and file manager files will automatically be set up by running the `summa_test_cases.py` file which instructions can be found in the `summa_test_cases.py` section below. For the test list, you can choose any test in test_inventory.json by name, or "all", "multiGruTestCases", "syntheticTestCases", or "wrrPaperTestCases". Note, the multiGru tests take significantly longer than the other tests.
    - Example: "Test_List": ["celia1990", "colbeck1976", "miller1998", "mizoguchi1990", "vanderborght2005", "wigmosta1999", "reynolds_canopySrad_windPrfile_stomResist", "reynolds_groundwatr", "senator_alb_method", "umpqua_snowIncept"]

 - Precision: Either use "single" or "double". This specifies what precision of forcing data to use for the test cases.
    - Example: "Precision": "single",

 - Solver: Either use "homegrown", "ida", "kinsol" for V4 and "v3" for older implementations of SUMMA. This specifies what solver to use for the solution to summa. The file manager file will automatically be set up from your selection here.
    - Example: "Solver": "homegrown",

 - Summa_exe: Provide a full path to the summa or summa_sundials executable that you compiled.
    - "Summa_Exe": "/absolute/path/to/summa.exe"

 - Version: actors or non-actors versions of the programs, they have some differences in setting up
    - "Version": "non-actors"

### Using `summa_test_cases.py`
Once you have set up the `test_settings.json` file. You then have to configure your setup with the `summa_test_cases.py` file. You run it with the following `python3 summa_test_cases.py [options]`. Below are a list of options:
- init
- run
- reset
- clean

The first command to use is `python3 summa_test_cases.py init`. This will set up all of the output directories and the file managers. After running init the next command to run is `python3 summa_test_cases.py run`. This will run all of the tests that you specified in the Test_List key in the `test_settings.json` file.

If you plan to run more tests with multiple configurations use the `reset` option followed by `init` again. If you wish to delete everything including your generated output use `clean`.

### EXAMPLE TEST_SETTINGS.json
```json
{
    "Test_List": ["all"],
        
    "Solver": "ida",

    "Precision": "double",
    
    "Version": "non-actors",
    
    "Executables": ["/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials.exe"]
}

```

### Note on Parameters
We have left the v4 parameters out of the `summa_zLocalParamInfo.txt` files, so that the V3 Summa will run. If you would like to change these parameters, the lines to add to the files to use these parameters at default are the following (and change as you desire). The be_steps parameter applies to all V4 choices of solver, whereas the rel* and abs* parameters only apply to choice "ida". Note, these below are the recommended values for decision nrgConserv=closedForm. If nrgConserv=enthalpyForm or enthalpyFormLU, the absTolTemp* values should be 1.0e2 instead of 1.0e-3. These values are the hard-coded default (with 1.0e-3 or 1.0e2 depending on your nrgConserv choice).
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


