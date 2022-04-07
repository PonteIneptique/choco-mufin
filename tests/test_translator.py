import os.path

from unittest import TestCase
from chocomufin.funcs import Translator, convert_file, _test_helper, get_files_unknown_and_known
from chocomufin.parsers import Alto


class TestRegressionTranslator(TestCase):
    def _get_file(self, path):
        return os.path.join(os.path.dirname(__file__), path)

    def test_ydiaresis(self):
        """ Test a weird bug with Y + DOT ABOVE"""
        translator = Translator.parse(
            self._get_file("test_controltable/y_dot_above.csv"),
            "NFD"
        )
        unk, kno = get_files_unknown_and_known(
            Alto(self._get_file("test_data/y_dot_above.xml")),
            translator,
            "NFD"
        )
        self.assertCountEqual(kno, {'ẏ', '#r#[a-zA-Z]'}, "Y+DOT above should be known, even in NFD")
        self.assertCountEqual(unk, set(), "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self._get_file("test_data/y_dot_above.xml"),
            translator=translator,
            normalization_method="NFD"
        )
        self.assertEqual(_test_helper(instance, 0), "son enuers dyagolus le bas", "Conversion works well")

    def test_combining_support_char(self):
        """ Test that when finding something like ◌ͨ ChocoMufin ignores the ◌ char."""
        translator = Translator.parse(
            self._get_file("test_controltable/support_combining_char.csv"),
            "NFD"
        )
        unk, kno = get_files_unknown_and_known(
            Alto(self._get_file("test_data/support_combining_char.xml")),
            translator,
            "NFD"
        )
        self.assertCountEqual(kno, {'#r#[a-zA-Z]', 'ͥ'}, "The original stripped char should be visible")
        self.assertCountEqual(unk, {"ꝑ", ".", "'"}, "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self._get_file("test_data/support_combining_char.xml"),
            translator=translator,
            normalization_method="NFD"
        )
        self.assertEqual(_test_helper(instance, 0), "qͨ les oi ꝑler", "Conversion works well")
