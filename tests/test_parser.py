from chocomufin.funcs import Replacement, Translator
import unicodedata


def nfd(string: str) -> str:
    return unicodedata.normalize("NFD", string)


def test_parser():
    assert Translator.parse("tests/test_controltable/simple.csv") == Translator([
        Replacement(char='0', replacement='', _allow=True, regex=False,
                    record={'char': '0', 'name': 'DIGIT ZERO', 'replacement': '', 'ontographe': '0'}),
        Replacement(char='1', replacement='', _allow=True, regex=False,
                    record={'char': '1', 'name': 'DIGIT ONE', 'replacement': '', 'ontographe': '1'}),
        Replacement(char='2', replacement='', _allow=True, regex=False,
                    record={'char': '2', 'name': 'DIGIT TWO', 'replacement': '', 'ontographe': '2'})
    ])
    assert Translator.parse("tests/test_controltable/simple.csv", normalization="NFD") == Translator([
        Replacement(char='0', replacement='', _allow=True, regex=False,
                    record={'char': '0', 'name': 'DIGIT ZERO', 'replacement': '', 'ontographe': '0'}),
        Replacement(char='1', replacement='', _allow=True, regex=False,
                    record={'char': '1', 'name': 'DIGIT ONE', 'replacement': '', 'ontographe': '1'}),
        Replacement(char='2', replacement='', _allow=True, regex=False,
                    record={'char': '2', 'name': 'DIGIT TWO', 'replacement': '', 'ontographe': '2'})
    ], normalization="NFD")

    assert Translator.parse(
        "tests/test_controltable/nfd.csv",
        normalization="NFD"
    ) == Translator([
        Replacement(char='᷒᷒', replacement='ꝰ', _allow=False, regex=False,
                    record={'char': '᷒᷒', 'name': 'COMBINING US ABOVE', 'replacement': 'ꝰ'}),
        Replacement(char='ꝯ', replacement='', _allow=True, regex=False,
                    record={'char': 'ꝯ', 'name': 'LATIN SMALL LETTER CON', 'replacement': ''}),
        Replacement(char='ꝰ', replacement='', _allow=True, regex=False,
                    record={'char': 'ꝰ', 'name': 'MODIFIER LETTER US', 'replacement': ''}),
        Replacement(char='ẻ', replacement='e̾', _allow=False, regex=False,
                    record={'char': 'ẻ', 'name': 'LATIN SMALL LETTER E WITH HOOK ABOVE', 'replacement': 'e̾'})
    ], normalization="NFD")
