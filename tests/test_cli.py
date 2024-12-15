import csv
import glob

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

        assert rows[0] == {'char': '#r#l’', 'name': 'LATIN SMALL LETTER L WITH STROKE', 'replacement': 'ł',
                           'codepoint': '', 'mufidecode': '', 'order': '0'}, \
            "First row should be the old same row"

        assert rows[-3:] == [
            {'char': ';', 'name': 'SEMICOLON', 'replacement': '', 'codepoint': '003B', 'mufidecode': ';', 'order': ''},
            {'char': '̃', 'name': 'COMBINING TILDE', 'replacement': '', 'codepoint': '0303', 'mufidecode': '',
             'order': ''},
            {'char': '̾', 'name': 'COMBINING VERTICAL TILDE', 'replacement': '', 'codepoint': '033E', 'mufidecode': '',
             'order': ''}
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
        assert [row["char"] for row in rows] == [
            'V',
            '#r#[a-ik-uw-zA-IK-UW-Z]',
            '#r#[\\u0363-\\u036D\\u036F\\u1DDA\\u1DDC\\u1DDD\\u1DE0\\u1DE4\\u1DE6\\u1DE8\\u1DEB\\u1DEE\\u1DF1\\uF02B\\uF030\\uF033]',
            '#r#[ᵃᵇᶜᵈᵉᶠᵍʰⁱᵏˡᵐⁿᵒᵖ\U000107a5ʳˢᵗᵘʷˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹]',
            '#r#[./:⟦⟧‸\\-]',
            ';',
            '̃',
            '̾'
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
            'ᷤ', 'ꝑ', 'ꝰ', 'l', 'D', 'I', 'u', 'z', 'd', 's', 'o', '\uf1ac', ':', '⁊', 'x', 'f', 'g', 'ᷠ', '-', '̾', 'ˢ',
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

