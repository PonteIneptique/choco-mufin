import unicodedata
import logging
import csv
import sys
import re
import os
from typing import Set, Pattern, Iterable, Union, Dict, Any, ClassVar
from collections import defaultdict

import mufidecode
import tabulate
import lxml.etree as ET
import click
import tqdm


from .parsers import Parser, Alto
logging.getLogger().setLevel(logging.INFO)

IGNORE = re.compile(r"[\s']+")


def ignore(line: str, regex: Pattern = IGNORE) -> str:
    """ Replaces characters that needs to be ignored
    """
    return regex.sub("", line)


def parse_table(table_file: str = "table.csv", as_dict: bool = False,
                normalization: str = "NFC") -> Union[Set[str], Dict[str, str]]:
    """ Parse a character translation table
    """
    if as_dict:
        chars = {}
        with open(table_file) as f:
            r = csv.DictReader(f)
            for line in r:
                line = {key: unicodedata.normalize(normalization, val) for key, val in line.items()}
                if line["char"] != line["normalized"]:
                    chars[line["char"]] = line["normalized"]
        return chars

    # if not as_dict, returns a set
    chars = set()
    with open(table_file) as f:
        r = csv.DictReader(f)
        for line in r:
            line = {key: unicodedata.normalize(normalization, val) for key, val in line.items()}
            chars.add(line["char"])
    return chars


def check_file(file, table, normalization: str = "NFC", parser: ClassVar[Parser] = Alto):
    """ Check a file for missing chars in the translation table
    """
    text = set()

    instance = Parser(file)
    logging.info(f"Parsing {file}")
    for line in instance.get_lines():
        text = text.union(set(ignore(unicodedata.normalize(normalization, str(line)))))

    return text - table


def get_hex(char: str) -> str:
    return str(hex(ord(char))).replace("0x", "").rjust(4, "0").upper().strip()


def convert_file(file: str, control_table: Dict[str, str], normalization: str = "NFC",
                 parser: ClassVar[Parser] = Alto) -> Parser:
    logging.info(f"Parsing {file}")
    def _normalize(line_text: str) -> str:
        return "".join([
            control_table.get(char, char)
            for char in unicodedata.normalize(normalization, str(line_text))
        ])

    instance = parser(file)

    for _ in instance.get_lines(set_callback=_normalize):
        continue

    return instance


@click.group()
@click.option("--debug", default=False, is_flag=True, show_default=True)
@click.option("-n", "--norm", default="NFC", help="Unicode normalization to apply", show_default=True)
@click.pass_context
def main(ctx: click.Context, debug: bool = False, norm: str = "NFC"):
    """Mufi checkers allow for multiple things"""
    if debug:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)
    ctx.obj["unorm"] = norm


@main.command("control")
@click.argument("table", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument("files", type=click.Path(exists=True, file_okay=True, dir_okay=False), nargs=-1)
@click.option("-s", "--ignore", type=click.STRING, default=".mufichecker.xml", show_default=True)
@click.option("--parser", type=click.Choice(["alto"]), default="alto", help="XML format of the file", show_default=True)
@click.pass_context
def control(ctx: click.Context, table: str, files: Iterable[str], ignore: str, parser: str = "alto"):
    control_table = parse_table(table, normalization=ctx.obj["unorm"])
    errors = defaultdict(list)
    missing_chars = set()
    for file in tqdm.tqdm(files):
        if ignore in file:  # Skip converted content
            continue
        new_chars = check_file(file, table=control_table, normalization=ctx.obj["unorm"], parser=Alto)
        if new_chars:
            for char in new_chars:
                errors[char].append(file)
            missing_chars = missing_chars.union(new_chars)

    # Generate the controlling table
    table = [["Character", "Hex-representation", "Files"]]
    for char in errors:
        table.append([
            char.strip(),
            get_hex(char),
            errors[char][0]
        ])
        if len(errors[char]) > 1:
            for file in errors[char][1:]:
                table.append(["", "", file])

    # Prints table and exits
    if len(table) > 1:
        click.echo(
            click.style(f"ERROR : {len(errors)} characters found that were not in the conversion table", fg='red'),
            color=True
        )
        click.echo("----\nREPORT\n----")
        print(tabulate.tabulate(table, headers="firstrow", tablefmt="fancy_grid"))
        sys.exit(1)
    else:
        click.echo(
            click.style("No new characters found", fg="green")
        )
        sys.exit(0)


@main.command("convert")
@click.option("-s", "--suffix", type=click.STRING, default=".mufichecker.xml", show_default=True)
@click.argument("table", type=click.Path(file_okay=True, dir_okay=False))
@click.argument("files", type=click.Path(exists=True, file_okay=True, dir_okay=False), nargs=-1)
@click.pass_context
def convert(ctx: click.Context, table: str, files: Iterable[str], suffix: str = ".mufichecker.xml"):
    """ Given a conversion TABLE generated by the `generate` command, normalizes FILES and saves the output
    in file with SUFFIX."""
    control_table = parse_table(table, as_dict=True, normalization=ctx.obj["unorm"])

    for file in tqdm.tqdm(files):
        if suffix in file:  # Skip converted content
            continue

        instance: Parser = convert_file(file, control_table, normalization=ctx.obj["unorm"])
        with open(file.replace(".xml", suffix) if ".xml" in file else file+suffix, "w") as f:
            f.write(ET.tostring(instance.xml, encoding=str, xml_declaration=False, pretty_print=True))


@main.command("generate")
@click.argument("table", type=click.Path(file_okay=True, dir_okay=False))
@click.argument("files", type=click.Path(exists=True, file_okay=True, dir_okay=False), nargs=-1)
@click.option("--mode", type=click.Choice(["keep", "reset", "cleanup"]),
              default="keep", help="Mode used to take into account the original [TABLE] if it exists. "
                                   "--mode=keep keeps the original data, even if they are not in the [FILES],"
                                   " --mode=reset will drop everything from the original table,"
                                   " --mode=cleanup will drop values which have not been found in the [FILES].",
              show_default=True)
@click.option("--parser", type=click.Choice(["alto"]), default="alto", help="XML format of the file", show_default=True)
@click.pass_context
def generate(ctx: click.Context, table: str, files: Iterable[str], mode: str = "keep", parser: str = "alto"):
    """ Generate a [TABLE] of accepted character for transcriptions based on [FILES]
    """
    prior = {}
    if parser == "alto":
        parser = Alto

    if os.path.isfile(table) and mode != "reset":
        click.echo(click.style(f"Loading previous table at path `{table}`", fg="yellow"))

        with open(table) as f:
            r = csv.DictReader(f)
            for char_from_table in r:
                char_from_table = {
                    key: unicodedata.normalize(ctx.obj["unorm"], val) if key == "char" else val
                    for key, val in char_from_table.items()
                }
                print(char_from_table)
                prior[char_from_table["char"]] = char_from_table
        click.echo(click.style(f"`{len(prior)} characters found in the original table`", fg="green"))

    text = set()
    for file in tqdm.tqdm(files):
        instance = parser(file)
        text = text.union(set(
            unicodedata.normalize(
                ctx.obj["unorm"],
                " ".join(instance.get_lines())
            )
        ))

    all_chars = sorted([char for char in text if char.strip()])
    content = []

    for char_from_xmls in all_chars:
        if not re.match(r"\s", char_from_xmls):
            try:
                mufi_char = mufidecode.mufidecode(char_from_xmls)
            except:
                logging.warning(f"Error parsing MUFI value for `{char_from_xmls}`"
                                f" (Unicode Hex Code Point: {get_hex(char_from_xmls)})")
                mufi_char = "[UNKNOWN]"
            cdict = {
                "char": char_from_xmls,
                "mufidecode": mufi_char,
                "codepoint": get_hex(char_from_xmls)
            }
            try:
                cdict["name"] = unicodedata.name(char_from_xmls)
            except ValueError:
                logging.warning(f"Character `{char_from_xmls}` has an unknown name"
                                f" (Unicode Hex Code Point: {get_hex(char_from_xmls)})")
                cdict["name"] = "[UNKNOWN-NAME]"

            if char_from_xmls in prior:
                cdict = {
                    key: cdict.get(key, "").strip() or value
                    for key, value in prior[char_from_xmls].items()
                }
                prior.pop(char_from_xmls)
            content.append(cdict)

    # ToDo: if a character is not in the XML set but in the table.csv, should we keep it in the table.csv ?
    if prior:
        if mode == "keep":
            for character in prior:
                content.append(prior[character])
            click.echo(click.style(f"Characters kept with keep mode: `{', '.join(prior.keys())}`", fg="yellow"))
        elif mode == "cleanup":
            click.echo(click.style(f"Characters dropped with clean-up mode: `{', '.join(prior.keys())}`", fg="yellow"))

    with open(table, "w") as f:
        w = csv.DictWriter(f, fieldnames=["char", "name", "normalized", "codepoint", "mufidecode"])
        w.writeheader()
        w.writerows(content)


def main_wrap():
    main(obj={})


if __name__ == "__main__":
    main_wrap()
