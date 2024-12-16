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
    _allow: bool = False
    record: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __hash__(self):
        return hash(
            (
                self.char, self.replacement, self.regex, self._allow,
                *[
                    f"<record key='{key}'>{value}</record>"
                    for key, value in sorted(self.record.items(), key=lambda x: x[0])
                ]
            )
        )

    @property
    def allow(self):
        return self._allow or self.char == self.replacement

    def __repr__(self):
        return (f"Replacement("
                f"char='{self.char}', "
                f"replacement='{self.replacement}', "
                f"allow={self.allow}, "
                f"regex={self.regex}, "
                f"record={str(self.record)}"
                f")")

    def as_dict(self) -> Dict[str, str]:
        """

        >>> Replacement("[a-z]", "[a-z]", record={"char": "#r#[a-z]", "replacement": "#r#[a-z]"}).as_dict() == {
        ... "char": "[a-z]", "replacement": "", "regex": "true", "allow": "true"}
        True

        """
        record = {**self.record}

        if record["char"].startswith("#r#"):
            record["char"] = self.char
            record["regex"] = "true"
            record["replacement"] = self.replacement

        if self.allow:
            record["allow"] = "true"
            record["replacement"] = ""

        return record

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
        >>> Replacement("a", "a").replaces("abba")
        'abba'
        >>> Replacement("[a-z]", r"\g<0>", regex=True).replaces("abbaZ")
        'abbaZ'
        >>> Replacement("(\S)([\.;:])(\S)", "\g<1>\g<2> \g<3>", regex=True).replaces("Fin de phrase.pas d'espace")
        "Fin de phrase. pas d'espace"
        """
        if self.allow:
            return string
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

    def __len__(self):
        return len(self.control_table)

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

    def get_unknown_chars(self, line: str, normalization: Optional[str] = None) -> Set:
        """ Checks a line to see

        Simple cases
        >>> Translator([Replacement(char="é", replacement="ẽ")]).get_unknown_chars("ábé") == {'á', 'b'}
        True
        >>> Translator([
        ...     Replacement(char="é", replacement="ẽ")
        ... ]).get_unknown_chars("ábé", normalization="NFD") == {'a', 'b', 'e', '́'}
        True
        >>> Translator([
        ...     Replacement(char='́', replacement='̃')
        ... ]).get_unknown_chars("ábé", normalization="NFD") == set("abe")
        True
        >>> Translator([
        ...     Replacement(char='é', replacement='ẽ')
        ... ]).get_unknown_chars("ábé", normalization="NFD") == set("áb")
        True

        "Advanced" cases
        >>> Translator([
        ...     Replacement(char='bé', replacement='dé'), Replacement(char='é', replacement='ẽ')
        ... ]).get_unknown_chars("ábé", normalization="NFD") == set("á")
        True
        >>> Translator([
        ...     Replacement(char='f', replacement='f'),
        ...     Replacement(char="a", replacement="a"),
        ...     Replacement(char="b", replacement="b"),
        ...     Replacement(char='́', replacement='́')
        ... ]).get_unknown_chars("ábé", normalization="NFD") == set("e")
        True
        >>> Translator([
        ...     Replacement(char='e', replacement='e'),
        ...     Replacement(char="a", replacement="a"),
        ...     Replacement(char="b", replacement="b"),
        ...     Replacement(char='́', replacement='́')
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
        # Remove spaces
        for repl in self.control_table:
            line = repl.removes(line)
        line = re.sub(r"\s+", "", line)
        return set(line)

    def get_known_chars(
            self,
            line: str,
            normalization: Optional[str] = None,
            ignore: Set[str] = None) -> Set[Replacement]:
        """ Checks a line to see all characters or input that are known

        Simple cases
        >>> Translator([Replacement("é", "ẽ")]).get_known_chars("ábé") == {Replacement("é", "ẽ")}
        True

        Input dictionary is not normalized a Translator initialization but it is at parsing
           resulting in 0 known chars
        >>> Translator([Replacement("é", "ẽ")]).get_known_chars("ábé", normalization="NFD") == set()
        True
        >>> Translator([Replacement('́', '̃')]).get_known_chars("ábé", normalization="NFD") == {Replacement('́', '̃')}
        True
        >>> Translator([Replacement('é', 'ẽ')]).get_known_chars("ábé", normalization="NFD") == {Replacement('é', 'ẽ')}
        True

        "Advanced" cases
        >>> Translator(
        ...     [Replacement('bé', 'dé'), Replacement('é', 'ẽ')]
        ... ).get_known_chars("ábé", normalization="NFD") == {Replacement('bé', 'dé'), Replacement('é', 'ẽ')}
        True
        >>> Translator([
        ...     Replacement('f', 'f'), Replacement("a", "a"), Replacement("b", "b"), Replacement('́', '́')
        ... ]).get_known_chars("ábé", normalization="NFD") == {
        ...     Replacement("a", "a"), Replacement("b", "b"), Replacement('́', '́')}
        True
        >>> Translator([
        ...     Replacement('e', 'e'), Replacement("a", "a"), Replacement("b", "b"), Replacement('́', '́')
        ... ]).get_known_chars("ábé", normalization="NFD") == {
        ...     Replacement('e', 'e'), Replacement("a", "a"), Replacement("b", "b"), Replacement('́', '́')}
        True
        >>> Translator(
        ...     [Replacement('e', 'e'), Replacement("[a-z]", "[a-z]", regex=True)]
        ... ).get_known_chars("abcdef", normalization="NFD") == {
        ...     Replacement('e', 'e'), Replacement("[a-z]", "[a-z]", regex=True)}
        True
        >>> Translator([Replacement('[a-z]', 'e', regex=True), Replacement("1", "1")]).get_known_chars(
        ...     "abcdef1", normalization="NFD") == {
        ...     Replacement('[a-z]', 'e', regex=True), Replacement("1", "1")}
        True
        >>> Translator([Replacement('[a-z]', 'e'), Replacement("1", "1")]).get_known_chars(
        ...     "abcdef1", normalization="NFD", ignore={"[a-z]"}) == {Replacement("1", "1")}
        True
        """
        if not ignore:
            ignore = set()

        known_chars = set()

        # Issue with Transform
        line = normalize(line, method=normalization)
        for repl in self.control_table:
            if repl.is_in(line) and repl.char not in ignore:
                known_chars.add(repl)

        return known_chars

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
                char = Replacement.normalized(line["char"], normalization=normalization)
                replacement = Replacement.normalized(line["replacement"], normalization=normalization)
                regex = False
                if line.get("regex", "").lower() == "true":
                    regex = True
                allow = False
                if line.get("allow", "").lower() == "true":
                    allow = True
                elif char.startswith("#r#"):
                    char = char[3:]
                    regex = True
                    if replacement[:3] == "#r#":
                        replacement = replacement[3:]
                if char == replacement:
                    allow = True
                    replacement = ""
                    line["replacement"] = ""

                chars.append(Replacement(char=char, replacement=replacement, regex=regex, _allow=allow, record=line))

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
        normalization: Optional[str] = None,
        parser: ClassVar[Parser] = Alto
):
    """ Check a file for missing chars in the translation table

    :param file: File to parse to check compatibility of characters
    :param translator: Translation table
    :param normalization: Method to use on the file content for matching
    :param parser: System to use to parse the XML

    >>> check_file("tests/test_data/alto1.xml", Translator([])) == {'₰', '⸗'}
    True
    >>> check_file("tests/test_data/alto1.xml", Translator([Replacement('₰', "")])) == {'⸗'}
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
    >>> converted = convert_file("tests/test_data/alto1.xml", translator, "NFD")
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
            content = list(prior.keys()) + content
            if echo:
                click.echo(click.style(
                    f"Characters kept with keep mode and found"
                    f": `{', '.join(sorted([r.char for r in used]))}`",
                    fg="yellow")
                )
                click.echo(click.style(
                    f"Characters kept with keep mode and found"
                    f": `{', '.join(sorted([r.char for r in set(prior.keys()).difference(set(content))]))}`",
                    fg="yellow")
                )
        elif mode == "cleanup":
            removed: List[Replacement] = []
            cleanupcontent: List[Replacement] = []
            for character in prior:
                if character in used:
                    cleanupcontent.append(character)
                else:
                    removed.append(character)
            if echo:
                if prior:
                    click.echo(click.style(
                        "Characters kept because they were used: {}".format(
                            ', '.join([f"`{k.char}`" for k in used])
                        ),
                        fg="yellow"
                    ))
                if removed:
                    click.echo(click.style("Replacement removed because they were not used", fg="red"))
                    click.echo(tabulate.tabulate(
                        [k.as_dict() for k in removed], showindex=True, headers="keys", tablefmt="pipe"
                    ))
            content = cleanupcontent + content

    prior_order = list(prior.keys())

    out_file = table_file
    if dest:
        out_file = dest
    with open(out_file, "w") as out_file:
        w = csv.DictWriter(
            out_file,
            fieldnames=list(keys)
        )
        w.writeheader()
        w.writerows(sorted(
            [c.as_dict() for c in content],
            key=lambda x: prior_order.index(x) if x in prior else x.char
        ))
    return content
