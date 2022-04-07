import csv
import logging
import os.path
import re
import json
import unicodedata
from typing import Set, Dict, ClassVar, Optional, Iterable, List, Tuple, Union

import tabulate
import tqdm
import click
import mufidecode

from chocomufin.parsers import Parser, Alto


with open(os.path.join(os.path.dirname(__file__), "mufi.json")) as mufi_file_io:
    MUFI = json.load(mufi_file_io)


_SUB_MUFI_SUPPORT_CHAR = re.compile("◌")


def normalize(string, method: Optional[str] = None):
    """ Apply or not unicode normalization to `string`

    >>> normalize("ãbé") == "ãbé"
    True
    >>> normalize("ãbé", "NFKC") != "ãbé"
    False
    """
    if method:
        return unicodedata.normalize(method, string)
    return string


def get_hex(char: str) -> str:
    """ Get the 4-digits code of a character

    >>> get_hex("a") == "0061"
    True
    """
    return str(hex(ord(char))).replace("0x", "").rjust(4, "0").upper().strip()


class Translator:

    def __init__(self, control_table: Dict[str, str], known_chars: Optional[Union[Set[str], List[str]]] = None):
        """ Apply a normalization dict to a string

        :param control_table: Dictionary of string-to-string replacement
        """
        self._control_table: Dict[str, str] = control_table
        self._replace_table: Dict[str, str] = {
            self._replace_regexp(match): repl
            for match, repl in control_table.items()
        }
        self._control_table_re = re.compile("(" + "|".join([Translator._escape(key) for key in control_table]) + ")")

        self._known_chars: Set[str] = set()
        self._known_chars_lists: List[str] = []

        if not known_chars:
            self._known_chars = set(self._control_table.keys())
            self._known_chars_lists = list(self._control_table.keys())
        elif isinstance(known_chars, list):
            self._known_chars_lists = known_chars
            self._known_chars = set(known_chars).union(set(self._control_table.keys()))
        else:
            self._known_chars = known_chars.union(set(self._control_table.keys()))

            def get_order(char):
                chars = list(self._control_table.keys())
                if char in chars:
                    return chars.index(char)
                return len(chars)+1

            self._known_chars_lists = sorted(list(self._known_chars), key=get_order)

        self._known_chars_re = re.compile(
            "(" + "|".join([
                Translator._escape(key)
                for key in self._known_chars_lists + [r"#r#\s"]
            ]) + ")"
        )

    @staticmethod
    def _remove_character_support(string: str, normalization_method: Optional[str]) -> str:
        """ Remove the support character for combining characters

        No support for this function in case of no normalization as we normalize both way

        >>> Translator._remove_character_support("◌ͤ", "NFC") == chr(0x364)
        True
        >>> Translator._remove_character_support("◌ͤ", "NFKD") == chr(0x364)
        True
        >>> Translator._remove_character_support("◌ͤ", None) == "◌ͤ"
        True
        """

        if not normalization_method:
            return string
        else:
            return normalize(
                _SUB_MUFI_SUPPORT_CHAR.sub("", normalize(string, "NFD")),
                method=normalization_method
            )

    def __len__(self):
        return len(self._known_chars)

    def __eq__(self, other):
        return isinstance(other, Translator) and \
               other.known_chars == self.known_chars \
               and other.control_table == self.control_table

    @staticmethod
    def _escape(string: str):
        """ Escapes or not a string that is present in the control table. Strings starting with #r# are not escaped

        >>> Translator._escape("#r#(a|b)")
        '(a|b)'
        >>> Translator._escape("(a|b)") == r'\(a\|b\)'
        True

        """
        if string.startswith("#r#"):
            return string[3:]
        return re.escape(string)

    @property
    def control_table(self):
        return self._control_table

    @property
    def known_chars(self):
        return self._known_chars

    def _sub(self, group: re.Match) -> str:
        return self._replace_table[group.group(0)]

    def translate(
            self,
            line_text: str,
            normalization_method: Optional[str] = None
    ) -> str:
        """ Apply a normalization dict to a string

        :param line_text: A string which you want to normalize according to a conversion table
        :param normalization_method: Unicode normalization to apply before applying the control_table

        Simple cases
        >>> (Translator({"é": "ẽ"})).translate("ábé")
        'ábẽ'
        >>> (Translator({"é": "ẽ"})).translate("ábé", normalization_method="NFD") # This one is normalized
        'ábé'
        >>> (Translator({'́': '̃'})).translate("ábé", normalization_method="NFD")
        'ãbẽ'
        >>> (Translator({'é': 'ẽ'})).translate("ábé", normalization_method="NFD")
        'ábẽ'

        "Advanced" cases
        >>> (Translator({'bé': 'dé', 'é': 'ẽ'})).translate("ábé", normalization_method="NFD")
        'ádé'

        """
        return self._control_table_re.sub(
            self._sub,
            normalize(line_text, normalization_method)
        )

    def set(self):
        """ Get the set of control table keys

        >>> (Translator({"a": "b", "c": "d"})).set() == {"a", "c"}
        True
        """
        return set(self._control_table.keys())

    def get_unknown_chars(self, line: str, normalization_method: Optional[str] = None) -> Set:
        """ Checks a line to see

        Simple cases
        >>> (Translator({"é": "ẽ"})).get_unknown_chars("ábé") == set("áb")
        True
        >>> (Translator({"é": "ẽ"})).get_unknown_chars("ábé", normalization_method="NFD") == set("abé")
        True
        >>> (Translator({'́': '̃'})).get_unknown_chars("ábé", normalization_method="NFD") == set("abe")
        True
        >>> (Translator({'é': 'ẽ'})).get_unknown_chars("ábé", normalization_method="NFD") == set("áb")
        True

        "Advanced" cases
        >>> (Translator({'bé': 'dé', 'é': 'ẽ'})).get_unknown_chars("ábé", normalization_method="NFD") == set("á")
        True
        >>> (Translator({'f': 'f'}, {"a", "b", '́'})).get_unknown_chars("ábé", normalization_method="NFD") == set("e")
        True
        >>> (Translator({'e': 'e'}, {"a", "b", '́'})).get_unknown_chars("ábé", normalization_method="NFD") == set()
        True
        >>> (Translator({'e': 'e'}, {"#r#[a-z]"})).get_unknown_chars("abcdef", normalization_method="NFD") == set()
        True
        >>> (Translator({'#r#[a-z]': 'e'}, {"1"})).get_unknown_chars("abcdef1", normalization_method="NFD") == set()
        True
        """
        return set(
            self._known_chars_re.sub(
                "",
                normalize(line, method=normalization_method)
            )
        )

    def get_known_chars(
            self,
            line: str,
            normalization_method: Optional[str] = None,
            ignore: Set[str] = None) -> Set[str]:
        """ Checks a line to see all characters or input that are known

        ToDo: Find a more efficient way to do this ?

        Simple cases
        >>> (Translator({"é": "ẽ"})).get_known_chars("ábé") == {"é"}
        True

        Input dictionary is not normalized a Translator initialization but it is at parsing
           resulting in 0 known chars
        >>> (Translator({"é": "ẽ"})).get_known_chars("ábé", normalization_method="NFD") == set()
        True
        >>> (Translator({'́': '̃'})).get_known_chars("ábé", normalization_method="NFD") == {'́'}
        True
        >>> (Translator({'é': 'ẽ'})).get_known_chars("ábé", normalization_method="NFD") == {'é'}
        True

        "Advanced" cases
        >>> (Translator({'bé': 'dé', 'é': 'ẽ'})).get_known_chars("ábé", normalization_method="NFD") == {'bé', 'é'}
        True
        >>> (Translator({'f': 'f'}, {"a", "b", '́'})).get_known_chars(
        ...      "ábé", normalization_method="NFD") == {"a", "b", '́'}
        True
        >>> (Translator({'e': 'e'}, {"a", "b", '́'})).get_known_chars(
        ...      "ábé", normalization_method="NFD") == {"a", "b", "e", '́'}
        True
        >>> (Translator({'e': 'e'}, {"#r#[a-z]"})).get_known_chars(
        ...      "abcdef", normalization_method="NFD") == {"#r#[a-z]", "e"}
        True
        >>> (Translator({'#r#[a-z]': 'e'}, {"1"})).get_known_chars(
        ...     "abcdef1", normalization_method="NFD") == {"#r#[a-z]", "1"}
        True
        >>> (Translator({'#r#[a-z]': 'e'}, {"1"})).get_known_chars(
        ...     "abcdef1", normalization_method="NFD", ignore={"#r#[a-z]"}) == {"1"}
        True
        """
        if not ignore:
            ignore = set()
        line = normalize(line, method=normalization_method)
        transform = set([
            matcher
            for matcher in self.control_table.keys()
            if matcher not in ignore and re.search(self._escape(matcher), line)
        ])
        ignore = ignore.union(transform)
        known_chars = set([
            matcher
            for matcher in self.known_chars
            if matcher not in ignore and re.search(self._escape(matcher), line)
        ])
        return transform.union(known_chars)

    @classmethod
    def parse(
        cls,
        table_file: str,
        normalization_method: Optional[str] = None
    ) -> "Translator":
        """ Parse a character translation table

        >>> Translator.parse("tests/test_controltable/simple.csv") == Translator({}, set("012"))
        True
        >>> Translator.parse(
        ... "tests/test_controltable/simple.csv", normalization_method="NFD") == Translator({}, set("012"))
        True
        >>> Translator.parse(
        ... "tests/test_controltable/nfd.csv", normalization_method="NFD").control_table
        {'᷒᷒': 'ꝰ', 'ẻ': 'e̾'}
        >>> Translator.parse(
        ... "tests/test_controltable/nfd.csv", normalization_method="NFD") == Translator(
        ... {'᷒᷒': 'ꝰ', 'ẻ': 'e̾'}, {'᷒᷒', 'ꝯ', 'ẻ', 'ꝰ'})
        True
        """
        chars = {}
        known_chars = []

        for line in cls.get_csv(table_file):
            line = {
                cls._remove_character_support(key, normalization_method): cls._remove_character_support(
                    val, normalization_method)
                for key, val in line.items()
            }
            # Append to the dict only differences between char and normalized
            if line["char"] != line["replacement"]:
                chars[line["char"]] = line["replacement"]
            known_chars.append(line["char"])
        return Translator(chars, known_chars=known_chars)

    @staticmethod
    def get_csv(table_file: str):
        """ Get a list of row as dict

        """
        with open(table_file) as f:
            yield from csv.DictReader(f)

    @staticmethod
    def _replace_regexp(string: str) -> str:
        """ Replace regexp for the group finder

        >>> Translator._replace_regexp("#r#l'")
        "l'"
        >>> Translator._replace_regexp("#r#\u0035")
        '5'
        >>> Translator._replace_regexp("ab")
        'ab'
        """
        if string.startswith("#r#"):
            if len(string) > 3:
                string = string[3:]
                if string.startswith("\\u"):
                    return str(chr(int(string.replace("\\u", ""), 16)))
                return string
            return ""
        return string

def check_file(
    file: str,
    translator: Translator,
    normalization_method: Optional[str] = None,
    parser: ClassVar[Parser] = Alto
):
    """ Check a file for missing chars in the translation table

    :param file: File to parse to check compatibility of characters
    :param translator: Translation table
    :param normalization_method: Method to use on the file content for matching
    :param parser: System to use to parse the XML

    >>> check_file("tests/test_data/alto1.xml", Translator({})) == {'₰', '⸗'}
    True
    >>> check_file("tests/test_data/alto1.xml", Translator({'₰': ""})) == {'⸗'}
    True
    """
    unmatched_chars = set()

    instance = parser(file)
    logging.info(f"Parsing {file}")
    for line in instance.get_lines():
        unmatched_chars = unmatched_chars.union(
            translator.get_unknown_chars(str(line), normalization_method=normalization_method)
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
    normalization_method: Optional[str] = None,
    parser: ClassVar[Parser] = Alto
) -> Parser:
    """ Check a file for missing chars in the translation table

    :param file: File to parse to check compatibility of characters
    :param translator: Translation table object
    :param normalization_method: Method to use on the file content for matching
    :param parser: System to use to parse the XML

    >>> translator = Translator({"⸗": "="})
    >>> converted = convert_file("tests/test_data/alto1.xml", translator, "NFD")
    >>> _test_helper(converted, 1) == "₰"
    True
    >>> _test_helper(converted, 0) == "="
    True
    """
    logging.info(f"Parsing {file}")

    instance = parser(file)

    def wrapper(line: str) -> str:
        return translator.translate(str(line), normalization_method=normalization_method)

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
    normalization_method: Optional[str] = None
) -> Tuple[Set[str], Set[str]]:
    """ Retrieves unknown and known characters from an instance

    """
    unknown = set()
    used = set()

    for line in instance.get_lines():
        unknown = unknown.union(
            translator.get_unknown_chars(
                str(line),
                normalization_method=normalization_method
            )
        )
        used = used.union(
            translator.get_known_chars(
                str(line),
                normalization_method=normalization_method
            )
        )
    return unknown, used


def update_table(
    files: Iterable[str],
    table_file: Optional[str] = None,
    mode: str = "add",
    parser: ClassVar[Parser] = Alto,
    echo: bool = False,
    normalization_method: Optional[str] = None,
    dest: Optional[str] = None
):
    prior: Dict[str, Dict[str, str]] = {}
    translator = Translator({})
    if parser == "alto":
        parser = Alto

    if table_file and mode != "reset":
        prior = {row["char"]: row for row in (Translator.get_csv(table_file))}
        translator = Translator.parse(table_file, normalization_method=normalization_method)
        if echo:
            click.echo(click.style(f"Loading previous table at path `{table_file}`", fg="yellow"))
            click.echo(click.style(f"{len(translator)} characters found in the original table", fg="green"))

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
        inst_unknown, used_unknown = get_files_unknown_and_known(instance, translator, normalization_method)
        unknown = unknown.union(inst_unknown)
        used = used.union(used_unknown)

    # Content is a list of
    #    with at least char, mufidecode, codepoint and name as keys
    content: List[Dict[str, str]] = []

    for unknown_char in unknown:
        # If we get an UNKNOWN_CHAR, we check if this can be normalized with uni/mufidecode
        try:
            mufi_char = mufidecode.mufidecode(unknown_char)
        except:
            warning(f"Error parsing MUFI value for `{unknown_char}`"
                    f" (Unicode Hex Code Point: {get_hex(unknown_char)})")
            mufi_char = "[UNKNOWN]"

        cdict = {
            "char": unknown_char,
            "mufidecode": mufi_char,
            "codepoint": get_hex(unknown_char)
        }

        try:
            cdict["name"] = get_character_name(unknown_char)
        except CharacterUnknown:
            warning(f"Character `{unknown_char}` has an unknown name"
                    f" (Unicode Hex Code Point: {get_hex(unknown_char)})")
            cdict["name"] = "[UNKNOWN-NAME]"

        if unknown_char in prior:
            cdict = {
                key: cdict.get(key, "").strip() or value
                for key, value in prior[unknown_char].items()
            }
            prior.pop(unknown_char)
        content.append(cdict)

    # ToDo: if a character is not in the XML set but in the table.csv, should we keep it in the table.csv ?
    if prior:
        if mode == "keep":
            for character in prior:
                content.append(prior[character])
            if echo:
                click.echo(click.style(f"Characters kept with keep mode and found"
                                       f": `{', '.join([char for char in prior.keys() if char in used])}`", fg="yellow")
                           )
                click.echo(click.style(f"Characters kept with keep mode but not found"
                                       f": `{', '.join([char for char in prior.keys() if char not in used])}`", fg="yellow")
                           )
        elif mode == "cleanup":
            removed = []
            for character in prior:
                if character in used:
                    content.append(prior[character])
                else:
                    removed.append(prior[character])
            if echo:
                if prior:
                    click.echo(click.style("Characters kept because they were used: {}".format(
                        ', '.join([f"`{k}`" for k in sorted(list(used))])
                    ), fg="yellow"))
                if removed:
                    click.echo(click.style("Replacement removed because they were not used", fg="red"))
                    click.echo(tabulate.tabulate(removed, showindex=True, headers="keys", tablefmt="pipe"))

    base_field_names = ["char", "name", "replacement", "codepoint", "mufidecode"]
    previous_field_names = set([
        key
        for row in content
        for key in row.keys()
    ]).difference(set(base_field_names))
    out_file = table_file
    if dest:
        out_file = dest
    with open(out_file, "w") as out_file:
        w = csv.DictWriter(
            out_file,
            fieldnames=["char", "name", "replacement", "codepoint", "mufidecode"]+sorted(list(previous_field_names))
        )
        w.writeheader()
        w.writerows(sorted(content, key=lambda x: x.get("char")))
    return content
