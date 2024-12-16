import csv
import logging
import os.path
import json
import unicodedata
from typing import Set, Dict, ClassVar, Optional, Iterable, List, Tuple

import tabulate
import tqdm
import click
import mufidecode

from chocomufin.classes import get_hex, Replacement, Translator
from chocomufin.parsers import Parser, Alto

with open(os.path.join(os.path.dirname(__file__), "mufi.json")) as mufi_file_io:
    MUFI = json.load(mufi_file_io)


def check_file(
        file: str,
        translator: Translator,
        normalization: Optional[str] = None,
        parser: ClassVar[Parser] = Alto
):
    """ Check a file for missing chars in the translation table

    :param file: File to parse to check compatibility of characters
    :param translator: Translation table
    :param normalization: Method to use on the file content for matching
    :param parser: System to use to parse the XML

    >>> check_file("tests/test_data/alto/alto1.xml", Translator([])) == {'₰', '⸗'}
    True
    >>> check_file("tests/test_data/alto/alto1.xml", Translator([Replacement('₰', "")])) == {'⸗'}
    True
    """
    unmatched_chars = set()

    instance = parser(file)
    logging.info(f"Parsing {file}")
    for line in instance.get_lines():
        unmatched_chars = unmatched_chars.union(
            translator.get_unknown_chars(str(line), normalization=normalization)
        )

    return unmatched_chars


def _test_helper(parser: Parser, index: int) -> str:
    """ Read line at index X
    
    Only for tests purposes
    """
    for cur_id, line in enumerate(parser.get_lines()):
        if cur_id == index:
            return str(line)
    raise ValueError("Unreached ID")


def convert_file(
        file: str,
        translator: Translator,
        normalization: Optional[str] = None,
        parser: ClassVar[Parser] = Alto
) -> Parser:
    """ Check a file for missing chars in the translation table

    :param file: File to parse to check compatibility of characters
    :param translator: Translation table object
    :param normalization: Method to use on the file content for matching
    :param parser: System to use to parse the XML

    >>> translator = Translator([Replacement("⸗", "=")])
    >>> converted = convert_file("tests/test_data/alto/alto1.xml", translator, "NFD")
    >>> _test_helper(converted, 1) == "₰"
    True
    >>> _test_helper(converted, 0) == "="
    True
    """
    logging.info(f"Parsing {file}")

    instance = parser(file)

    def wrapper(line: str) -> str:
        new = translator.translate(str(line), normalization=normalization)
        instance.add_log(line, new)
        return new

    for _ in instance.get_lines(set_callback=wrapper):
        continue

    return instance


class CharacterUnknown(ValueError):
    """ Exception raised when a character as no name"""


def get_character_name(character: str, raise_exception: bool = True) -> str:
    name = unicodedata.name(character, None)
    if name:
        return name
    name = MUFI.get(get_hex(character))
    if name:
        return name["description"]
    if raise_exception:
        raise CharacterUnknown
    return "[[[UNKNOWN NAME]]]"


def get_files_unknown_and_known(
        instance: Parser,
        translator: Translator,
        normalization: Optional[str] = None
) -> Tuple[Set[str], Set[Replacement]]:
    """ Retrieves unknown and known characters from an instance

    """
    unknown = set()
    used = set()

    for line in instance.get_lines():
        unknown = unknown.union(
            translator.get_unknown_chars(
                str(line),
                normalization=normalization
            )
        )
        used = used.union(
            translator.get_known_chars(
                str(line),
                normalization=normalization
            )
        )
    return unknown, used


def update_table(
        files: Iterable[str],
        table_file: Optional[str] = None,
        mode: str = "add",
        parser: ClassVar[Parser] = Alto,
        echo: bool = False,
        normalization: Optional[str] = None,
        dest: Optional[str] = None
):
    prior: Dict[Replacement, None] = {}
    translator = Translator([])
    if parser == "alto":
        parser = Alto

    keys = {"char", "replacement", "regex", "allow"}

    if table_file and os.path.exists(table_file) and mode != "reset":
        translator = Translator.parse(table_file, normalization=normalization)
        prior = {repl: None for repl in translator.control_table}
        if echo:
            click.echo(click.style(f"Loading previous table at path `{table_file}`", fg="yellow"))
            click.echo(click.style(f"{len(translator)} characters found in the original table", fg="green"))

        keys = keys.union(set([
            key
            for c in prior
            for key in c.record.keys()
        ]))

    # Mainly decorative stuff
    decoration = tqdm.tqdm
    if not echo:
        def decoration(iterable):
            return iterable

        def warning(message):
            logging.warning(message)
    else:
        def warning(message: str):
            click.echo(click.style(message, fg="red"))

    unknown = set()
    used = set()
    for file in decoration(files):
        instance = parser(file)
        inst_unknown, inst_known = get_files_unknown_and_known(instance, translator, normalization)
        unknown = unknown.union(inst_unknown)
        used = used.union(inst_known)

    content: List[Replacement] = []
    print(unknown)
    for unknown_char in unknown:
        # If we get an UNKNOWN_CHAR, we check if this can be normalized with uni/mufidecode
        try:
            mufi_char = mufidecode.mufidecode(unknown_char)
        except:
            warning(f"Error parsing MUFI value for `{unknown_char}`"
                    f" (Unicode Hex Code Point: {get_hex(unknown_char)})")
            mufi_char = "[UNKNOWN]"

        try:
            name = get_character_name(unknown_char)
        except CharacterUnknown:
            warning(f"Character `{unknown_char}` has an unknown name"
                    f" (Unicode Hex Code Point: {get_hex(unknown_char)})")
            name = "[UNKNOWN-NAME]"

        unknown_repl = Replacement(unknown_char, "", _allow=True, regex=False,
                                   record={
                                       key: value for key, value in {
                                           "mufidecode": mufi_char,
                                           "codepoint": get_hex(unknown_char),
                                           "name": name
                                       }.items()
                                       if key in keys
                                   })

        if unknown_repl not in prior:
            content.append(unknown_repl)

    # ToDo: if a character is not in the XML set but in the table.csv, should we keep it in the table.csv ?
    # ToDo: rework from here
    if prior:
        content = sorted(content, key=lambda x: x.char)
        if mode == "keep":
            new = [] + content
            content = list(prior.keys()) + new
            if echo:
                click.echo(click.style(
                    f"Characters kept with keep mode and found"
                    f": `{', '.join(sorted([r.char_repr() for r in used]))}`",
                    fg="yellow"
                ))
                click.echo(click.style(
                    f"New characters found"
                    f": `{', '.join(sorted([r.char_repr() for r in new]))}`",
                    fg="yellow"
                ))
        elif mode == "cleanup":
            removed: List[Replacement] = []
            clean_up_content: List[Replacement] = []
            for character in prior:
                if character in used:
                    clean_up_content.append(character)
                else:
                    removed.append(character)
            if echo:
                if prior:
                    click.echo(click.style(
                        "Characters kept because they were used: {}".format(
                            ', '.join([f"`{k.char_repr()}`" for k in used])
                        ),
                        fg="yellow"
                    ))
                if removed:
                    click.echo(click.style("Replacement removed because they were not used", fg="red"))
                    click.echo(tabulate.tabulate(
                        [k.as_dict() for k in removed], showindex=True, headers="keys", tablefmt="pipe"
                    ))
            content = clean_up_content + content

    prior_order = list(prior.keys())
    fieldnames = list(keys)
    new_field_names = set([
        key
        for c in content
        for key in c.record.keys()
    ])
    fieldnames = fieldnames + list(sorted(new_field_names))

    out_file = table_file
    if dest:
        out_file = dest
    with open(out_file, "w") as out_file:
        w = csv.DictWriter(
            out_file,
            fieldnames=fieldnames
        )
        w.writeheader()
        w.writerows([c.as_dict() for c in sorted(
            content,
            key=lambda x: str(prior_order.index(x)).zfill(10) if x in prior else "1"+ x.char
        )])
    return content
