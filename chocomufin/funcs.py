import csv
import logging
import re
import unicodedata
from typing import Pattern, Union, Set, Dict, ClassVar

from .parsers import Parser, Alto

IGNORE = re.compile(r"[\s']+")


def ignore(line: str, regex: Pattern = IGNORE) -> str:
    """ Replaces characters that needs to be ignored
    """
    return regex.sub("", line)


def parse_table(table_file: str = "table.csv", as_dict: bool = False,
                normalization: str = "NFC") -> Union[Set[str], Dict[str, str]]:
    """ Parse a character translation table
    """
    if as_dict:
        chars = {}
        with open(table_file) as f:
            r = csv.DictReader(f)
            for line in r:
                line = {key: unicodedata.normalize(normalization, val) for key, val in line.items()}
                if line["char"] != line["normalized"]:
                    chars[line["char"]] = line["normalized"]
        return chars

    # if not as_dict, returns a set
    chars = set()
    with open(table_file) as f:
        r = csv.DictReader(f)
        for line in r:
            line = {key: unicodedata.normalize(normalization, val) for key, val in line.items()}
            chars.add(line["char"])
    return chars


def check_file(file, table, normalization: str = "NFC", parser: ClassVar[Parser] = Alto):
    """ Check a file for missing chars in the translation table
    """
    text = set()

    instance = Parser(file)
    logging.info(f"Parsing {file}")
    for line in instance.get_lines():
        text = text.union(set(ignore(unicodedata.normalize(normalization, str(line)))))

    return text - table


def get_hex(char: str) -> str:
    return str(hex(ord(char))).replace("0x", "").rjust(4, "0").upper().strip()


def convert_file(file: str, control_table: Dict[str, str], normalization: str = "NFC",
                 parser: ClassVar[Parser] = Alto) -> Parser:
    logging.info(f"Parsing {file}")
    def _normalize(line_text: str) -> str:
        return "".join([
            control_table.get(char, char)
            for char in unicodedata.normalize(normalization, str(line_text))
        ])

    instance = parser(file)

    for _ in instance.get_lines(set_callback=_normalize):
        continue

    return instance