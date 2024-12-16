import os.path
from unittest import TestCase
from click.testing import CliRunner

from chocomufin.classes import Translator, Replacement
from chocomufin.functions import convert_file, _test_helper, get_files_unknown_and_known
from chocomufin.parsers import Alto, Page


class _DerivedOutput:
    def __init__(self, out):
        self.exit_code = out.exit_code
        self.output = ansi_escape.sub("", out.output)


class AltoTestCase(TestCase):
    FOLDER = "alto"
    SCHEMA_ERROR = "DescriptionW"
    PARSER = {"alto": Alto, "page": Page}

    def setUp(self) -> None:
        self._folder = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            type(self).FOLDER
        )
        self._runner = CliRunner()
        self._format = type(self).FOLDER
        self._parser = type(self).PARSER.get(type(self).FOLDER, Alto)

    def cmd(self, *args):
        out = self._runner.invoke(cmd, ["--format", self._format, *args])
        return _DerivedOutput(out)

    def getFile(self, filename: str):
        return os.path.join(self._folder, filename)

    def getControlTable(self, filename: str):
        # is `return os.path.join("test_controltable", filename)` sufficient?
        return os.path.join(self._folder, "..", "..", "test_controltable", filename)

    # adapted from test_translator.py
    def test_ydiaresis(self):
        """ Test a weird bug with Y + DOT ABOVE"""
        translator = Translator.parse(
            self.getControlTable("y_dot_above.csv"),
            "NFD"
        )
        unk, kno = get_files_unknown_and_known(
            self._parser(self.getFile("y_dot_above.xml")),
            translator,
            "NFD"
        )
        
        self.assertCountEqual(
            kno,
            {
                Replacement(char='ẏ', replacement='y', _allow=False, regex=False,
                            record={'char': 'ẏ', 'name': 'LATIN SMALL LETTER Y WITH DIAERESIS', 'replacement': 'y',
                                    'ontographe': 'y', 'regex': ''}),
                Replacement(char='[a-zA-Z]', replacement='', _allow=True, regex=True,
                            record={'char': '[a-zA-Z]', 'name': 'All letters', 'replacement': '', 'regex': 'true',
                                    'ontographe': ''})
            },
            "Y+DOT above should be known, even in NFD")
        self.assertCountEqual(unk, set(), "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self.getFile("y_dot_above.xml"),
            translator=translator,
            normalization="NFD",
            parser=self._parser
        )
        self.assertEqual(_test_helper(instance, 0), "son enuers dyagolus le bas", "Conversion works well")

    # adapted from test_translator.py
    def test_combining_support_char(self):
        """ Test that when finding something like ◌ͨ ChocoMufin ignores the ◌ char."""
        translator = Translator.parse(
            self.getControlTable("support_combining_char.csv"),
            "NFD"
        )
        unk, kno = get_files_unknown_and_known(
            self._parser(self.getFile("support_combining_char.xml")),
            translator,
            "NFD"
        )
        self.assertCountEqual(
            kno,
            {
                Replacement(char='[a-zA-Z]', replacement='', _allow=True, regex=True,
                            record={'char': '[a-zA-Z]', 'name': 'All letters', 'replacement': '', 'ontographe': '',
                                    'regex': 'true', '': None}),
                Replacement(char='ͥ', replacement='ͨ', _allow=False, regex=False,
                            record={'char': '◌ͥ', 'name': 'COMBINING US ABOVE', 'replacement': '◌ͨ',
                                    'ontographe': 'con', 'regex': '', '': None})
            },
            "The original stripped char should be visible"
        )
        self.assertCountEqual(unk, {"ꝑ", ".", "'"}, "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self.getFile("support_combining_char.xml"),
            translator=translator,
            normalization="NFD",
            parser=self._parser
        )
        self.assertEqual(_test_helper(instance, 0), "qͨ les oi ꝑler", "Conversion works well")


class PageTestCase(AltoTestCase):
    FOLDER = "page"
