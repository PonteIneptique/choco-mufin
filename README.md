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
char,name,normalized,codepoint,mufidecode
ī,LATIN SMALL LETTER I WITH MACRON,ĩ,012B,i
ı,LATIN SMALL LETTER DOTLESS I,i,0131,i
ﬀ,LATIN SMALL LIGATURE FF,ff,FB00,ff
A,LATIN CAPITAL LETTER A,A,0041,A
B,LATIN CAPITAL LETTER B,B,0042,B
C,LATIN CAPITAL LETTER C,C,0043,C
D,LATIN CAPITAL LETTER D,D,0044,D
```

As table:

| char | name                             | normalized | codepoint | mufidecode |
|------|----------------------------------|------------|-----------|------------|
| ī    | LATIN SMALL LETTER I WITH MACRON | ĩ          | 012B      | i          |
| ı    | LATIN SMALL LETTER DOTLESS I     | i          | 0131      | i          |
| ﬀ    | LATIN SMALL LIGATURE FF          | ff         | FB00      | ff         |
| A    | LATIN CAPITAL LETTER A           | A          | 0041      | A          |
| B    | LATIN CAPITAL LETTER B           | B          | 0042      | B          |
| C    | LATIN CAPITAL LETTER C           | C          | 0043      | C          |
| D    | LATIN CAPITAL LETTER D           | D          | 0044      | D          |