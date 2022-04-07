<img src="./img/chocomufin.png" width="250" align="right">

# Choco-Mufin

*\[CHaracter Ocr COordination for MUFI iN texts\]*

Tools for normalizing the use of some characters and checking file consistencies. Mainly target at dealing with
overly diverse ways to transcribe medieval data (allographetic and graphematic for example) while keeping information
such as abbreviation, hence MUFI.

## Install

`pip install chocomufin`

## Commands

The workflow is generally the following: you generate a conversion table (`choco-mufin generate table.csv your-files.xml`), then
use this table to either control (`choco-mufin control table.csv your-files.xml`) or convert them (`choco-mufin convert table.csv your-files.xml`).
Conversion will automatically add a suffix which you can define with `--suffix`.

## Example table of conversion


```csv
char,name,replacement,codepoint,mufidecode
ī,LATIN SMALL LETTER I WITH MACRON,ĩ,012B,i
ı,LATIN SMALL LETTER DOTLESS I,i,0131,i
ﬀ,LATIN SMALL LIGATURE FF,ff,FB00,ff
A,LATIN CAPITAL LETTER A,A,0041,A
B,LATIN CAPITAL LETTER B,B,0042,B
C,LATIN CAPITAL LETTER C,C,0043,C
D,LATIN CAPITAL LETTER D,D,0044,D
```

As table:

| char | name                             | replacement | codepoint | mufidecode |
|------|----------------------------------|-------------|-----------|------------|
| ī    | LATIN SMALL LETTER I WITH MACRON | ĩ           | 012B      | i          |
| ı    | LATIN SMALL LETTER DOTLESS I     | i           | 0131      | i          |
| ﬀ    | LATIN SMALL LIGATURE FF          | ff          | FB00      | ff         |
| A    | LATIN CAPITAL LETTER A           | A           | 0041      | A          |
| B    | LATIN CAPITAL LETTER B           | B           | 0042      | B          |
| C    | LATIN CAPITAL LETTER C           | C           | 0043      | C          |
| D    | LATIN CAPITAL LETTER D           | D           | 0044      | D          |


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
