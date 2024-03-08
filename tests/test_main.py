import os.path
from unittest import TestCase
from click.testing import CliRunner

from chocomufin.funcs import Translator, convert_file, _test_helper, get_files_unknown_and_known
from chocomufin.parsers import Alto, Page


class _DerivedOutput:
    def __init__(self, out):
        self.exit_code = out.exit_code
        self.output = ansi_escape.sub("", out.output)


class AltoTestCase(TestCase):
    FOLDER = "alto"
    SCHEMA_ERROR = "DescriptionW"

    def setUp(self) -> None:
        self._folder = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            type(self).FOLDER
        )
        self._runner = CliRunner()
        self._format = type(self).FOLDER

    def cmd(self, *args):
        out = self._runner.invoke(cmd, ["--format", self._format, *args])
        return _DerivedOutput(out)

    def getFile(self, filename: str):
        return os.path.join(self._folder, filename)

    def getControlTable(self, filename: str):
        # is `return os.path.join("test_controltable", filename)` sufficient?
        return os.path.join(self._folder, "..", "test_controltable", filename)

    # adapted from test_translator.py
    def test_ydiaresis(self):
        """ Test a weird bug with Y + DOT ABOVE"""
        translator = Translator.parse(
            self.getControlTable("y_dot_above.csv"),
            "NFD"
        )
        if self._format == "alto":
            unk, kno = get_files_unknown_and_known(
                Alto(self.getFile("y_dot_above.xml")),
                translator,
                "NFD"
            )
        # I feel like this goes against the idea that this is AltoTestCase... but I don't see how else to minimize the replication of codes...
        elif self._format == "page":
            unk, kno = get_files_unknown_and_known(
                Page(self.getFile("y_dot_above.xml")),
                translator,
                "NFD"
            )
        
        self.assertCountEqual(kno, {'ẏ', '#r#[a-zA-Z]'}, "Y+DOT above should be known, even in NFD")
        self.assertCountEqual(unk, set(), "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self._get_file(self.getFile("y_dot_above.xml")),
            translator=translator,
            normalization_method="NFD"
        )
        self.assertEqual(_test_helper(instance, 0), "son enuers dyagolus le bas", "Conversion works well")

    # adapted from test_translator.py
    def test_combining_support_char(self):
        """ Test that when finding something like ◌ͨ ChocoMufin ignores the ◌ char."""
        translator = Translator.parse(
            self.getControlTable("support_combining_char.csv"),
            "NFD"
        )
        if self._format == "alto":
            unk, kno = get_files_unknown_and_known(
                Alto(self.getFile("support_combining_char.xml")),
                translator,
                "NFD"
            )
        # same same, should this distinction Page/Alto be done somewhere else?
        elif self._format == "page":
            unk, kno = get_files_unknown_and_known(
                Page(self.getFile("support_combining_char.xml")),
                translator,
                "NFD"
            )
        self.assertCountEqual(kno, {'#r#[a-zA-Z]', 'ͥ'}, "The original stripped char should be visible")
        self.assertCountEqual(unk, {"ꝑ", ".", "'"}, "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self.getFile("support_combining_char.xml"),
            translator=translator,
            normalization_method="NFD"
        )
        self.assertEqual(_test_helper(instance, 0), "qͨ les oi ꝑler", "Conversion works well")


class PageTestCase(AltoTestCase):
    FOLDER = "page"