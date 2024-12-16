<img src="./img/chocomufin.png" width="250" align="right">

# Choco-Mufin

*\[CHaracter Ocr COordination for MUFI iN texts\]*

Tools for normalizing the use of some characters and checking file consistencies. Mainly target at dealing with
overly diverse ways to transcribe medieval data (allographetic and graphematic for example) while keeping information
such as abbreviation, hence MUFI.

## Install

`pip install chocomufin`

## Commands

The workflow is generally the following: you generate a conversion table (`chocomufin generate table.csv your-files.xml`), then
use this table to either control (`chocomufin control table.csv your-files.xml`) or convert them (`chocomufin convert table.csv your-files.xml`).
Conversion will automatically add a suffix which you can define with `--suffix`.

## Table of conversion

### Syntax

A conversion table MUST contain at least a `char` and a `replacement` column, SHOULD 
contain a `regex` and `allow` column (with either `true` or empty values), and MAY contain any additional column.

The columns have the following effect:

- `char` is used to match a value in the XML or the text.
- `replacement` is used to replace what was found in char. 
- `regex`, if `true`, means `char` and `replacement` should be parsed as regex.
- `allow`, if `true`, will indicate that replacement should be ignored, and that the value(s) in `char` are valid.

Any other column should be seen as a comment.

### Example

In the following table:

```csv
lineno,char,replacement,regex,allow
1,V,U,,
2,[a-ik-uw-zA-IK-UW-Z],,true,true
3,(\S)(\.)(\S),\g<0>\g<1> \g<2>,true,
4,_,,,true
```

- Line no. 1 will replace any V into a U;
- Line no. 2 will allow any character in the range defined: those characters won't be replaced and will be accepted as is.
- Line no. 3 will replace any dot without spaces around it with a regex replacement groups used in the regex.
- Line no. 4 will allow `_` in the text, and not replace it with anything.

As table:

| lineno | char                 | replacement      | regex | allow |
|--------|----------------------|------------------|-------|-------|
| 1      | V                    | U                |       |       |
| 2      | [a-ik-uw-zA-IK-UW-Z] |                  | true  | true  |
| 3      | (\S)(\.)(\S)         | \g<1>\g<2> \g<3> | true  |       |
| 4      | _                    |                  |       | true  |

In this context, `lineno` is not used at all by chocomufin, but serves as a documentation tool. It would 
not break chocomufin.

## Github Action Template 

Just replace the path to `table.csv` and the file that needs to be tested, then save this file on your repository in
`.github/workflows/chocomufin.yml`:

```yaml
# This workflow will install Python dependencies, run tests and lint with a single version of Python
# For more information see: https://help.github.com/actions/language-and-framework-guides/using-python-with-github-actions

name: ChocoMufin

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python 3.8
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install chocomufin
    - name: Run ChocoMufin
      run: |
        chocomufin control table.csv **/*.xml
```


---

Logo by [Alix Chagué](https://alix-tz.github.io).

The file `original_mufi_json`'s content is under `CC BY-SA 4.0` and comes from https://mufi.info/m.php?p=mufiexport 
