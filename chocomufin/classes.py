import csv
import dataclasses
import unicodedata
from typing import Optional, Union, Callable, Dict, Any, List, Set, Iterable

import regex as re


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

    def char_repr(self) -> str:
        if self.regex:
            return "<regex>"+self.char
        return self.char

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

        if "char" not in self.record:
            record["char"] = self.char

        if "replacement" not in self.record:
            record["replacement"] = self.replacement

        if "regex" not in self.record:
            record["regex"] = "true" if self.regex else ""

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
        >>> Replacement(r"(\S)([\.;:])(\S)", r"\g<1>\g<2> \g<3>", regex=True).replaces("Fin de phrase.pas d'espace")
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
                    line["char"] = char
                    regex = True
                    if replacement[:3] == "#r#":
                        replacement = replacement[3:]
                        line["replacement"] = replacement

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


_SUB_MUFI_SUPPORT_CHAR = re.compile("◌")
