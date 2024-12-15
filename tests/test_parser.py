from chocomufin.funcs import Replacement, Translator
import unicodedata


def nfd(string: str) -> str:
    return unicodedata.normalize("NFD", string)


def test_parser():
    assert Translator.parse("tests/test_controltable/simple.csv") == Translator([
        Replacement("0", "0", regex=False, record={
            "char": "0",
            "replacement": "0",
            "ontographe": "0",
            "name": "DIGIT ZERO"
        }),
        Replacement("1", "1", regex=False, record={
            "char": "1",
            "replacement": "1",
            "ontographe": "1",
            "name": "DIGIT ONE"
        }),
        Replacement("2", "2", regex=False, record={
            "char": "2",
            "replacement": "2",
            "ontographe": "2",
            "name": "DIGIT TWO"
        })
    ])
    assert Translator.parse("tests/test_controltable/simple.csv", normalization="NFD") == Translator([
        Replacement("0", "0", regex=False, record={
            "char": "0",
            "replacement": "0",
            "ontographe": "0",
            "name": "DIGIT ZERO"
        }),
        Replacement("1", "1", regex=False, record={
            "char": "1",
            "replacement": "1",
            "ontographe": "1",
            "name": "DIGIT ONE"
        }),
        Replacement("2", "2", regex=False, record={
            "char": "2",
            "replacement": "2",
            "ontographe": "2",
            "name": "DIGIT TWO"
        })
    ], normalization="NFD")
    assert Translator.parse(
        "tests/test_controltable/nfd.csv",
        normalization="NFD"
    ) == Translator([
        Replacement('᷒᷒', 'ꝰ', regex=False, record={
            "char": '᷒᷒',
            "name": "COMBINING US ABOVE",
            "replacement": 'ꝰ'
        }),
        Replacement('ꝯ', 'ꝯ', regex=False, record={
            "char": 'ꝯ',
            "name": "LATIN SMALL LETTER CON",
            "replacement": 'ꝯ'
        }),
        Replacement('ꝰ', 'ꝰ', regex=False, record={
            "char": 'ꝰ',
            "name": "MODIFIER LETTER US",
            "replacement": 'ꝰ'
        }),
        Replacement(nfd('ẻ'), nfd('e̾'), regex=False, record={
            "char": 'ẻ',
            "name": "LATIN SMALL LETTER E WITH HOOK ABOVE",
            "replacement": 'e̾'
        })
    ], normalization="NFD")
