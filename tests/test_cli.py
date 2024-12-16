import csv
import glob
import lxml.etree as et

import pytest
import shutil
from pathlib import Path
from click.testing import CliRunner
from chocomufin import cli  # Assuming your Click app is in chocomufin.py


@pytest.fixture
def temp_dir_with_fixtures(tmp_path):
    """
    Copy the full fixtures directory (including subdirectories and files) into a temporary directory.
    """
    # Define the path to the directory containing your fixture files
    fixture_dir = Path(__file__).parent / "test_repository"

    # Copy the entire directory tree to the temporary directory
    destination = tmp_path / "fixtures"
    shutil.copytree(fixture_dir, destination)

    return destination


def test_chocomufin_generate_keep(temp_dir_with_fixtures):
    """
    Test the 'chocomufin generate' command to ensure it creates 'table.csv'.
    """
    runner = CliRunner()
    output_file = temp_dir_with_fixtures / "table.csv"
    xml_files_pattern = temp_dir_with_fixtures / "data/fisher-01125/*.xml"
    # Run the Click command
    result = runner.invoke(
        cli.main,
        ["-n", "NFD", "--debug", "generate", str(output_file), *glob.glob(str(xml_files_pattern)), "--parser", "alto"],
        obj={"cwd": temp_dir_with_fixtures}
    )

    # Check that the command ran successfully
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Check that the output file was created
    assert output_file.exists(), "The output file 'table.csv' was not created."

    # Check the content of the file
    with output_file.open("r") as f:
        content = f.read()
        assert content.strip(), "The output file 'table.csv' is empty."
        # Add specific content checks here if necessary
        f.seek(0)
        rows = list(csv.DictReader(f))

        assert rows[0] == {'char': 'l’', 'replacement': 'ł', 'name': 'LATIN SMALL LETTER L WITH STROKE',
                           'order': '0', 'regex': 'true', 'allow': ''}, \
            "First row should be the old same row"

        assert rows[-3:] == [
            {'char': ';', 'name': 'SEMICOLON', 'replacement': '', 'regex': '', 'order': '', 'allow': 'true'},
            {'char': '̃', 'name': 'COMBINING TILDE', 'replacement': '',  'regex': '', 'order': '', 'allow': 'true'},
            {'char': '̾', 'name': 'COMBINING VERTICAL TILDE', 'replacement': '',  'regex': '', 'order': '', 'allow': 'true'}
        ]


def test_chocomufin_generate_cleanup(temp_dir_with_fixtures):
    """
    Test the 'chocomufin generate' command to ensure it creates 'table.csv'.
    """
    runner = CliRunner()
    output_file = temp_dir_with_fixtures / "table.csv"
    xml_files_pattern = temp_dir_with_fixtures / "data/fisher-01125/*.xml"
    # Run the Click command
    result = runner.invoke(
        cli.main,
        ["-n", "NFD", "--debug", "generate", str(output_file), *glob.glob(str(xml_files_pattern)), "--parser",
         "alto", "--mode", "cleanup"],
        obj={"cwd": temp_dir_with_fixtures}
    )

    # Check that the command ran successfully
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Check that the output file was created
    assert output_file.exists(), "The output file 'table.csv' was not created."

    # Check the content of the file
    with output_file.open("r") as f:
        content = f.read()
        assert content.strip(), "The output file 'table.csv' is empty."
        # Add specific content checks here if necessary
        f.seek(0)
        rows = list(csv.DictReader(f))
        assert [(row["char"], row["regex"], row["allow"], row["replacement"]) for row in rows] == [
            ('V', "", "", "U"),
            ('[a-ik-uw-zA-IK-UW-Z]', "true", "true", ""),
            ('[\\u0363-\\u036D\\u036F\\u1DDA\\u1DDC\\u1DDD\\u1DE0\\u1DE4\\u1DE6\\u1DE8\\u1DEB\\u1DEE\\u1DF1\\uF02B\\uF030\\uF033]', "true", "true", ""),
            ('[ᵃᵇᶜᵈᵉᶠᵍʰⁱᵏˡᵐⁿᵒᵖ\U000107a5ʳˢᵗᵘʷˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹]', "true", "true", ""),
            ('[\uf1acꝭꝵ᷑ꝰ̶̧̇ꝯ÷⁊ħłꝈØꝓꝒꝑꝐꝙꝘꝗẜđ&♡℥𐆒]', 'true', 'true', ''),
            ('[./:⟦⟧‸\\-]', "true", "true", ""),
            (';', "", "true", ""),
            ('̃', "", "true", ""),
            ('̾', "", "true", "")
        ], "Characters should be reset"


def test_chocomufin_generate_reset(temp_dir_with_fixtures):
    """
    Test the 'chocomufin generate' command to ensure it creates 'table.csv'.
    """
    runner = CliRunner()
    output_file = temp_dir_with_fixtures / "table.csv"
    xml_files_pattern = temp_dir_with_fixtures / "data/fisher-01125/*.xml"
    # Run the Click command
    result = runner.invoke(
        cli.main,
        ["-n", "NFD", "generate", str(output_file), *glob.glob(str(xml_files_pattern)), "--parser",
         "alto", "--mode", "reset"],
        obj={"cwd": temp_dir_with_fixtures}
    )

    # Check that the command ran successfully
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Check that the output file was created
    assert output_file.exists(), "The output file 'table.csv' was not created."

    # Check the content of the file
    with output_file.open("r") as f:
        content = f.read()
        assert content.strip(), "The output file 'table.csv' is empty."
        # Add specific content checks here if necessary
        f.seek(0)
        rows = list(csv.DictReader(f))
        assert sorted([row["char"] for row in rows]) == sorted([
            'q', 'b', 'ꝯ', 'h', 'ͣ', ';', 'c', 'V', 'ᷝ', 'ꝵ', 'i', 'r', 't', 'ꝭ', 'y', 'e', 'ͥ', 'ꝓ', 'm', 'ͦ', 'a',
            'ᷤ', 'ꝑ', 'ꝰ', 'l', 'D', 'I', 'u', 'z', 'd', 's', 'o', '\uf1ac', ':', '⁊', 'x', 'f', 'g', 'ᷠ', '-', '̾',
            'ˢ',
            'ͤ', '̃', 'n', 'ł', 'H', 'p', '.'
        ]), "Characters should be reset"


def test_chocomufin_control_fail(temp_dir_with_fixtures):
    """
    Test the 'chocomufin control' command to ensure it succeeds
    """
    runner = CliRunner()
    output_file = temp_dir_with_fixtures / "table.csv"
    xml_files_pattern = temp_dir_with_fixtures / "data/fisher-01125/*.xml"
    # Run the Click command
    result = runner.invoke(
        cli.main,
        ["-n", "NFD", "control", str(output_file), *glob.glob(str(xml_files_pattern)), "--parser", "alto"],
        obj={"cwd": temp_dir_with_fixtures}
    )

    # Check that the command ran successfully
    assert result.exit_code == 1, f"Command failed: {result.output}"

    # Check that the output file was created
    assert "3 characters found that were not in the conversion table" in result.output, \
        f"No new character founds"


def test_chocomufin_control_succeed(temp_dir_with_fixtures):
    """
    Test the 'chocomufin control' command to ensure it succeeds
    """
    runner = CliRunner()
    output_file = temp_dir_with_fixtures / "table_correct.csv"
    xml_files_pattern = temp_dir_with_fixtures / "data/fisher-01125/*.xml"
    # Run the Click command
    result = runner.invoke(
        cli.main,
        ["-n", "NFD", "control", str(output_file), *glob.glob(str(xml_files_pattern)), "--parser", "alto"],
        obj={"cwd": temp_dir_with_fixtures}
    )

    # Check that the command ran successfully
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Check that the output file was created
    assert "No new characters found" in result.output, \
        f"New character found: {result.output}"


def test_chocomufin_convert(temp_dir_with_fixtures):
    """
    Test the 'chocomufin control' command to ensure it succeeds
    """
    runner = CliRunner()
    output_file = temp_dir_with_fixtures / "table_correct.csv"
    xml_files_pattern = temp_dir_with_fixtures / "data/fisher-01125/*.xml"
    # Run the Click command
    result = runner.invoke(
        cli.main,
        [
            "-n", "NFD",
            "convert", str(output_file), *glob.glob(str(xml_files_pattern)),
            "--parser", "alto", "--suffix", ".chocomufin.xml"
        ],
        obj={"cwd": temp_dir_with_fixtures}
    )

    # Check that the command ran successfully
    assert result.exit_code == 0, f"Command failed: {result.output}"

    for file in glob.glob(str(temp_dir_with_fixtures / "data/fisher-01125/*.chocomufin.xml")):
        xml = et.parse(file)
        z = [x for x in xml.xpath(
                "//a:String/@CONTENT",
                namespaces={"a": "http://www.loc.gov/standards/alto/ns-v4#"}
            ) if x]
        assert sorted(z) == sorted([
            'Incipit.', 'prologꝰ.', 'upientes', 'aliquid de', 'penuria ac teᷤnͥuᷠ', 'U',
            'itate nr̃a cũ pau-', 'ꝑcula in gazop', 'hilaciũ dñi mitt̾e',
            'ardua scandere opus ultra uͥres',
            'nr̃as aggrẽm p̾sumpsimꝰ ꝯsum-',
            'matõis fiduciã. laboris m̾cedẽ in sa-',
            'maritano statuentes. qui ꝓlatiˢ',
            'in curõem semiuiui duob\uf1ac dena',
            'riis suꝑeroganti cuncta reddere',
            'professus ẽ. Delectat nos u̾ritas-',
            'pollicentis. s\uf1ac t̾ret ĩ inm̃sitas labo-',
            'ris. Desideriũ ꝓ hortatur ꝓficiẽdi.',
            's\uf1ac dehortatur infirmitas deficien-',
            'di. qͣm uincit zelus domꝰ dei. quo',
            'in ardescentes fidem nr̃am adu̾-',
            'sus errores carnaliũ. atq\uf1ac aĩaliũ',
            'hoĩm. dauitice turris clipeis mu-',
            'nire. uł pociꝰ munitã ostend̾e. ac',
            'theologicaꝵ inquisitionũ abdita',
            'aperire necñ ⁊ sacͣmentoꝵ eccͣsti-',
            'coꝵ pro modico intelligentie n',
            'nr̃e noticiã tradere studuimus.',
            'ñ ualentes studiosoꝵ fr̃m uotis',
            'iure resistere. eoꝵ in xp̃o lauda-',
            'bilib\uf1ac studiis lingua ac studio nos',
            'seruire flagitantiũ quas bigas in',
            'nobis agit xp̃i caritas. qͣmuis nõ',
            'ambigamꝰ om̃em hũani eloquii',
            'sermonẽ calũpnie. atq\uf1ac cͣcdc̃oni e',
            'muloꝵ semꝑ fuisse obnoxiũ. qz dis-',
            'sentientib\uf1ac uoluntatũ motib\uf1ac. Dis',
            'sentiens qͦ\uf1ac fit aĩoꝵ sensus ut cũ õe',
            'dc̃m u̾i rõe ꝑfc̃m sit: tñ dum aliud',
            'aliis. aut uidetur. aut ꝯplacet u̾ita',
            'ti. uł ñ intᷝeᷝcͤte. uł offendenti impie-',
            'tatis erroꝵ obnitatur. ac uoluntatis',
            'inuidia resultet qͣm deus huiꝰ scl̃i',
            'operatur. in illis diffidentie filiis',
            'qui ñ rõni uoluntatẽ subiciunt.',
            'nec doctͥne studiũ impendũt. s\uf1ac his',
            'que sõpniar̃t sapĩe u̾ba coaptare',
            'nituntur: ñ u̾i. s\uf1ac placiti rõem sec',
            'tantes. quos iniqua uoluntas. nõ',
            'ad intelligentiã u̾itatiˢ. s\uf1ac ad defen-',
            'sionẽ placentiũ incitat nõ desidan-',
            'tes doceri u̾itatẽ. s\uf1ac ab ea ad fabulas',
            'ꝯu̾tentes auditum. quoꝵ professi',
            'o est magis placita qͣm docenda cõ',
            'quirere. nec docenda desidͤare. s\uf1ac desi',
            'deratis doctͥnam coaptare hñt rõ-',
            'nẽ sapĩe in suꝑstitõe. qz fidei defet-',
            'tionẽ sequitur ypocrisis m̃dax ut',
            'sit uł in uerbꝭ pietas qͣm amiserit',
            'conscĩa. Ip̃amq\uf1ac siml̃atam pietatẽ',
            'õi u̾boꝵ m̃datio impiam reddũt',
            'false doctͥne institutis fidei sc̃itatẽ',
            'corrumꝑe molientes auriũq\uf1ac pru',
            'riginẽ sub nouello sui desiderii dog-',
            'mate aliis ingerentes qui ꝯtentõi',
            'studentes ꝯͣ ueritatem sine federe',
            'bellant. Int̾ u̾i namq\uf1ac assercõem',
            '⁊ placiti defensionẽ pertinax pug-',
            'na est dũ se ⁊ u̾itas tenet. ⁊ se uolũ-',
            'tas erroris tuetur: Horum gͥ ⁊ doͤ',
            'odibilem eccͣm eu̾tere atq\uf1ac ora o-',
            'pilare. ne uirus nequitie in alios',
            'effundͤe queant. ⁊ luc̾nam u̾itatis',
            'in candelabro exaltare uolentes',
            'in labore multo ac sudore uolum̃',
            'dͤo pr̃ante ꝯpegimꝰ. ex testimoniis',
            'u̾itatis in et̾nũ fundatis in qͣtuor li',
            'bris distinctũ in quo maioꝵ exemp-',
            'la doctͥnamq: reperies. In quo per-',
            'dñice fidei sinc̾am ꝓfessionẽ uiꝑee',
            'doctͥne fraudulentiã ꝓdidimꝰ aditũ',
            'demonstrandi u̾itatem ꝯplexi. nec',
            'ꝑiculo impie professionis inserti'])
