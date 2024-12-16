import os.path

from unittest import TestCase
from chocomufin.functions import convert_file, _test_helper, get_files_unknown_and_known
from chocomufin.classes import Replacement, Translator
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
            "Y+DOT above should be known, even in NFD"
        )
        self.assertCountEqual(unk, set(), "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self._get_file("test_data/y_dot_above.xml"),
            translator=translator,
            normalization="NFD"
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
            self._get_file("test_data/support_combining_char.xml"),
            translator=translator,
            normalization="NFD"
        )
        self.assertEqual(_test_helper(instance, 0), "qͨ les oi ꝑler", "Conversion works well")

    def test_regex(self):
        """ Test that when finding something like ◌ͨ ChocoMufin ignores the ◌ char."""
        translator = Translator.parse(
            self._get_file("test_controltable/regex.csv"),
            "NFD"
        )
        unk, kno = get_files_unknown_and_known(
            Alto(self._get_file("test_data/support_combining_char.xml")),
            translator,
            "NFD"
        )
        self.assertCountEqual(
            kno,
            {
                Replacement(char='ͥ', replacement='ͨ', _allow=False, regex=False,
                            record={'char': '◌ͥ', 'name': 'COMBINING US ABOVE', 'replacement': '◌ͨ', 'regex': ''}),
                Replacement(char='[a-zA-Z]', replacement='\g<0>', _allow=False, regex=True,
                            record={'char': '[a-zA-Z]', 'name': 'All letters', 'replacement': '\\g<0>',
                                    'regex': 'true'})
            },
            "The original stripped char should be visible"
        )
        self.assertCountEqual(unk, {"ꝑ", ".", "'"}, "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self._get_file("test_data/support_combining_char.xml"),
            translator=translator,
            normalization="NFD"
        )
        self.assertEqual(_test_helper(instance, 0), "qͨ les oi ꝑler", "Conversion works well")

    def test_allow(self):
        """ Test that when finding something like ◌ͨ ChocoMufin ignores the ◌ char."""
        translator = Translator.parse(
            self._get_file("test_controltable/allow.csv"),
            "NFD"
        )
        unk, kno = get_files_unknown_and_known(
            Alto(self._get_file("test_data/support_combining_char.xml")),
            translator,
            "NFD"
        )
        self.assertCountEqual(
            kno,
            {
                Replacement(char='[a-zA-Z]', replacement='', _allow=True, regex=True,
                            record={'char': '[a-zA-Z]', 'name': 'All letters', 'replacement': '', 'regex': 'true',
                                    'allow': 'true'}),
                Replacement(char='ͥ', replacement='ͨ', _allow=False, regex=False,
                            record={'char': '◌ͥ', 'name': 'COMBINING US ABOVE', 'replacement': '◌ͨ', 'regex': '',
                                    'allow': ''})
            },
            "The original stripped char should be visible"
        )
        self.assertCountEqual(unk, {"ꝑ", ".", "'"}, "Y+DOT above should be known, even in NFD")

        instance = convert_file(
            self._get_file("test_data/support_combining_char.xml"),
            translator=translator,
            normalization="NFD"
        )
        self.assertEqual(_test_helper(instance, 0), "qͨ les oi ꝑler", "Conversion works well")
