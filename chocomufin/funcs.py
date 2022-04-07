import csv
import logging
import re
import unicodedata
from typing import Set, Dict, ClassVar, Optional

from chocomufin.parsers import Parser, Alto


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
    def __init__(self, control_table: Dict[str, str], known_chars: Optional[Set[str]] = None):
        """ Apply a normalization dict to a string

        :param control_table: Dictionary of string-to-string replacement
        """
        self._control_table = control_table
        self._control_table_re = re.compile("(" + "|".join([Translator._escape(key) for key in control_table]) + ")")
        self._known_chars = known_chars or set(self._control_table.keys())
        self._known_chars_re = re.compile(
            "(" + "|".join([
                Translator._escape(key)
                for key in self._known_chars.union({r"#r#\s"}).union(set(self._control_table.keys()))
            ]) + ")"
        )

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
        return self._control_table[group.group(0)]

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
        return set(self._known_chars_re.sub("", normalize(line, method=normalization_method)))

    @classmethod
    def parse(
        cls,
        table_file: str,
        normalization_method: Optional[str] = None
    ) -> "Translator":
        """ Parse a character translation table

        >>> Translator.parse("../tests/test_controltable/simple.csv") == Translator({}, set("012"))
        True
        >>> Translator.parse(
        ... "../tests/test_controltable/simple.csv", normalization_method="NFD") == Translator({}, set("012"))
        True
        >>> Translator.parse(
        ... "../tests/test_controltable/nfd.csv", normalization_method="NFD").control_table
        {'᷒᷒': 'ꝰ', 'ẻ': 'e̾'}
        >>> Translator.parse(
        ... "../tests/test_controltable/nfd.csv", normalization_method="NFD") == Translator(
        ... {'᷒᷒': 'ꝰ', 'ẻ': 'e̾'}, {'᷒᷒', 'ꝯ', 'ẻ', 'ꝰ'})
        True
        """
        chars = {}
        known_chars = set()
        with open(table_file) as f:
            r = csv.DictReader(f)
            for line in r:
                line = {
                    normalize(key, normalization_method): normalize(val, normalization_method)
                    for key, val in line.items()
                }
                # Append to the dict only differences between char and normalized
                if line["char"] != line["normalized"]:
                    chars[line["char"]] = line["normalized"]
                known_chars.add(line["char"])
        return Translator(chars, known_chars=known_chars)


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

    >>> check_file("../tests/test_data/alto1.xml", Translator({})) == {'₰', '⸗'}
    True
    >>> check_file("../tests/test_data/alto1.xml", Translator({'₰': ""})) == {'⸗'}
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
    >>> converted = convert_file("../tests/test_data/alto1.xml", translator, "NFD")
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
