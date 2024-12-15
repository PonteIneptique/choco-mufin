import csv
import dataclasses
import logging
import os.path
import regex as re
import json
import unicodedata
from typing import Set, Dict, ClassVar, Optional, Iterable, List, Tuple, Union, Callable, Any

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


@dataclasses.dataclass(frozen=True)
class Replacement:
    char: str
    replacement: Union[str, Callable[[str], str]]
    regex: bool = False
    record: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __repr__(self):
        return f"<repl {' '.join([key+'='+value for key, value in self.record.items()])} />"

    def as_dict(self) -> Dict[str, str]:
        return self.record

    def is_in(self, string: str) -> bool:
        """ Check whether a string matches a specific replacement

        >>> Replacement("a", "b", record={"name": "Letter A"}).is_in("abba")
        True
        >>> Replacement("a", "b", record={"name": "Letter A"}).is_in("a")
        True
        >>> Replacement("a", "b", record={"name": "Letter A"}).is_in("cdef")
        False
        """
        return re.match(".*" + self._escape(self.char) + ".*", string) is not None

    def findall(self, string: str) -> List[str]:
        """
        >>> Replacement("a", "a").findall("abba")
        ['a', 'a']
        """
        return re.findall(self._escape(self.char), string)

    def removes(self, string: str) -> str:
        """

        >>> Replacement("a", "b").removes("abba")
        'bb'
        >>> Replacement("[ab]", r"\1", regex=True).removes("abba")
        ''
        """
        return re.sub(self._escape(self.char), '', string)

    def replaces(self, string: str) -> str:
        """

        >>> Replacement("a", "b").replaces("abba")
        'bbbb'
        """
        return re.sub(self._escape(self.char), self.replacement, string)

    def _escape(self, string: str) -> str:
        if not self.regex:
            return re.escape(string)
        return string

    @staticmethod
    def normalized(string: str, normalization: Optional[str]) -> str:
        return normalize(
            _SUB_MUFI_SUPPORT_CHAR.sub("", normalize(string, "NFD")),
            method=normalization
        )


class Translator:
    def __init__(self, control_table: List[Replacement], normalization: Optional[str] = None):
        """ Apply a normalization dict to a string

        :param control_table: Dictionary of string-to-string replacement
        """
        self._control_table: List[Replacement] = control_table
        self._normalization: Optional[str] = normalization

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
        elif string == "◌":
            return string
        else:
            return normalize(
                _SUB_MUFI_SUPPORT_CHAR.sub("", normalize(string, "NFD")),
                method=normalization_method
            )

    def __eq__(self, other):
        return isinstance(other, Translator) and other.control_table == self.control_table and \
            other._normalization == self._normalization

    @property
    def control_table(self) -> List[Replacement]:
        return self._control_table

    def translate(
            self,
            line_text: str,
            normalization: Optional[str] = None
    ) -> str:
        """ Apply a normalization dict to a string

        :param line_text: A string which you want to normalize according to a conversion table
        :param normalization: Unicode normalization to apply before applying the control_table

        Simple cases
        >>> Translator([Replacement(char="é",  replacement="ẽ")]).translate("ábé")
        'ábẽ'
        >>> Translator([Replacement(char="é",  replacement='ẽ')]).translate("ábé", normalization="NFD")
        'ábẽ'
        >>> Translator([Replacement(char='́', replacement='̃')]).translate("ábé", normalization="NFD")
        'ãbẽ'
        >>> Translator([Replacement(char='é', replacement='ẽ')]).translate("ábé", normalization="NFD")
        'ábẽ'

        "Advanced" cases
        This is a change in behaviour where everything is applied
        >>> Translator([
        ...     Replacement(char='bé', replacement='dé'),
        ...     Replacement(char='é', replacement='ẽ')
        ... ]).translate("ábé", normalization="NFD")
        'ádẽ'

        """
        if normalization:
            line_text = unicodedata.normalize(normalization, line_text)
        for repl in self.control_table:
            line_text = repl.replaces(line_text)
        return line_text

    def set(self):
        """ Get the set of control table keys

        >>> (Translator({"a": "b", "c": "d"})).set() == {"a", "c"}
        True
        """
        return set(self._control_table.keys())

    def get_unknown_chars(self, line: str, normalization: Optional[str] = None) -> Set:
        """ Checks a line to see

        Simple cases
        >>> Translator([Replacement(char="é", replacement="ẽ")]).get_unknown_chars("ábé") == {'á', 'b'}
        True
        >>> Translator([
        ... Replacement(char="é", replacement="ẽ")
        ... ]).get_unknown_chars("ábé", normalization="NFD") == {'a', 'b', 'e', '́'}
        True
        >>> Translator([Replacement(char='́', replacement='̃')]
        ... ).get_unknown_chars("ábé", normalization="NFD") == set("abe")
        True
        >>> Translator([
        ... Replacement(char='é', replacement='ẽ')]).get_unknown_chars("ábé", normalization="NFD") == set("áb")
        True

        "Advanced" cases
        >>> Translator([
        ... Replacement(char='bé', replacement='dé'), Replacement(char='é', replacement='ẽ')
        ... ]).get_unknown_chars("ábé", normalization="NFD") == set("á")
        True
        >>> Translator([
        ... Replacement(char='f', replacement='f'),
        ... Replacement(char="a", replacement="a"),
        ... Replacement(char="b", replacement="b"),
        ... Replacement(char='́', replacement='́')
        ... ]).get_unknown_chars("ábé", normalization="NFD") == set("e")
        True
        >>> Translator([
        ... Replacement(char='e', replacement='e'),
        ... Replacement(char="a", replacement="a"),
        ... Replacement(char="b", replacement="b"),
        ... Replacement(char='́', replacement='́')
        ... ]).get_unknown_chars("ábé", normalization="NFD") == set()
        True
        >>> Translator([
        ...     Replacement('e', 'e'), Replacement("[a-z]", "\1", regex=True)
        ... ]).get_unknown_chars("abcdef", normalization="NFD") == set()
        True
        >>> Translator([
        ...     Replacement('[a-z]', 'e', regex=True),
        ...     Replacement("1", "1")
        ... ]).get_unknown_chars("abcdef1", normalization="NFD") == set()
        True
        """
        line = normalize(line, method=normalization)
        for repl in self.control_table:
            line = repl.removes(line)
        return set(line)


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
        normalization: Optional[str] = None
    ) -> "Translator":
        """ Parse a character translation table from a CSV

        """
        chars: List[Replacement] = []

        for line in cls.get_csv(table_file):
            try:
                chars.append(
                    Replacement(
                        char=Replacement.normalized(line["char"], normalization=normalization),
                        replacement=Replacement.normalized(line["replacement"], normalization=normalization),
                        regex=(True if line.get("regex", "").lower() == "true" else False),
                        record=line
                    )
                )
            except Exception as E:
                print(f"Following value is incorrect")
                print(line)
                raise E
        return Translator(chars, normalization=normalization)

    @staticmethod
    def get_csv(table_file: str) -> Iterable[Dict[str, str]]:
        """ Get a list of row as dict

        """
        with open(table_file) as f:
            yield from csv.DictReader(f)


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
        new = translator.translate(str(line), normalization_method=normalization_method)
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

    if table_file and os.path.exists(table_file) and mode != "reset":
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
    found = set()

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
            #cdict = {
            #    key: cdict.get(key, "").strip() or value
            #    for key, value in prior[unknown_char].items()
            #}
            found.add(unknown_char)
            continue
        content.append(cdict)

    # ToDo: if a character is not in the XML set but in the table.csv, should we keep it in the table.csv ?
    if prior:
        content = sorted(content, key=lambda x: x.get("char"))
        if mode == "keep":
            content = list(prior.values()) + content
            if echo:
                click.echo(click.style(f"Characters kept with keep mode and found"
                                       f": `{', '.join(sorted(list(set(prior.keys()).intersection(found))))}`",
                                       fg="yellow")
                           )
                click.echo(click.style(f"Characters kept with keep mode but not found"
                                       f": `{', '.join(sorted(list(set(prior.keys()).difference(found))))}`",
                                       fg="yellow")
                           )
        elif mode == "cleanup":
            removed = []
            cleanupcontent = []
            for character in prior:
                if character in used or character in found:
                    cleanupcontent.append(prior[character])
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
            content = cleanupcontent + content
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
        w.writerows(content)
    return content
