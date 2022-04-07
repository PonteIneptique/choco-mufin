from typing import Optional, Dict, List, Iterable
import unicodedata
import csv
import os
import re
import tqdm
import io
import mufidecode
import logging

from .parsers import Alto
from .funcs import get_hex


TableType = Dict[str, Dict[str, str]]


def read_table(file_or_content: str, is_filepath: bool = True, unicode_normalization: str = "NFC") -> TableType:
    table = file_or_content
    if not is_filepath:
        table = io.FileIO(file_or_content)

    parsed = {}

    with open(table) as f:
        r = csv.DictReader(f)
        for char_from_table in r:
            char_from_table = {
                key: unicodedata.normalize(unicode_normalization, val) if key == "char" else val
                for key, val in char_from_table.items()
            }
            parsed[char_from_table["char"]] = char_from_table
    return parsed


def generate(
        files: Iterable[str],
        table: Optional[TableType] = None,
        mode: str = "add",
        parser: str = "alto",
        use_tqdm: bool = True,
        unicode_normalization: str = "NFC"
):
    prior = {}
    if parser == "alto":
        parser = Alto

    if table and mode != "reset":
        prior = table
        #click.echo(click.style(f"Loading previous table at path `{table}`", fg="yellow"))
        #click.echo(click.style(f"`{len(prior)} characters found in the original table`", fg="green"))

    text = set()
    decoration = tqdm.tqdm
    if not use_tqdm:
        decoration = list

    for file in decoration(files):
        instance = parser(file)
        text = text.union(set(
            unicodedata.normalize(
                unicode_normalization,
                " ".join(instance.get_lines())
            )
        ))

    all_chars = sorted([char for char in text if char.strip()])
    content = []

    for char_from_xmls in all_chars:
        if not re.match(r"\s", char_from_xmls):
            try:
                mufi_char = mufidecode.mufidecode(char_from_xmls)
            except:
                logging.warning(f"Error parsing MUFI value for `{char_from_xmls}`"
                                f" (Unicode Hex Code Point: {get_hex(char_from_xmls)})")
                mufi_char = "[UNKNOWN]"
            cdict = {
                "char": char_from_xmls,
                "mufidecode": mufi_char,
                "codepoint": get_hex(char_from_xmls)
            }
            try:
                cdict["name"] = unicodedata.name(char_from_xmls)
            except ValueError:
                logging.warning(f"Character `{char_from_xmls}` has an unknown name"
                                f" (Unicode Hex Code Point: {get_hex(char_from_xmls)})")
                cdict["name"] = "[UNKNOWN-NAME]"

            if char_from_xmls in prior:
                cdict = {
                    key: cdict.get(key, "").strip() or value
                    for key, value in prior[char_from_xmls].items()
                }
                prior.pop(char_from_xmls)
            content.append(cdict)

    # ToDo: if a character is not in the XML set but in the table.csv, should we keep it in the table.csv ?
    if prior:
        if mode == "keep":
            for character in prior:
                content.append(prior[character])
            #click.echo(click.style(f"Characters kept with keep mode: `{', '.join(prior.keys())}`", fg="yellow"))
        elif mode == "cleanup":
            #click.echo(click.style(f"Characters dropped with clean-up mode: `{', '.join(prior.keys())}`", fg="yellow"))


    with open(table, "w") as f:
        w = csv.DictWriter(f, fieldnames=["char", "name", "normalized", "codepoint", "mufidecode"])
        w.writeheader()
        w.writerows(content)
    return content