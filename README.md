# Choco-Mufin

*\[CHaracter Ocr COordination for MUFI iN texts\]*

Tools for normalizing the use of some characters and checking file consistencies. Mainly target at dealing with
overly diverse ways to transcribe medieval data (allographetic and graphematic for example) while keeping information
such as abbreviation, hence MUFI.

## Install

`pip install choco-mufin`

## Commands

The workflow is generally the following: you generate a conversion table (`choco-mufin generate table.csv your-files.xml`), then
use this table to either control (`choco-mufin control table.csv your-files.xml`) or convert them (`choco-mufin convert table.csv your-files.xml`).
Conversion will automatically add a suffix which you can define with `--suffix`.