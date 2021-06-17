import unicodedata
import logging
import csv
import sys
import re
import os
from typing import Set, Pattern, Iterable, Union, Dict, Any
from collections import defaultdict

import mufidecode
import tabulate
import lxml.etree as ET
import click
import tqdm

logging.getLogger().setLevel(logging.INFO)

NS = {"a": "http://www.loc.gov/standards/alto/ns-v4#"}
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


def check_file(file, table, normalization: str = "NFC"):
    """ Check a file for missing chars in the translation table
    """
    text = set()
    xml = ET.parse(file)
    logging.info(f"Parsing {file}")
    for line in xml.xpath("//a:String/@CONTENT", namespaces=NS):
        text = text.union(set(ignore(unicodedata.normalize(normalization, str(line)))))

    return text - table


def get_hex(char: str) -> str:
    return str(hex(ord(char))).replace("0x", "").rjust(4, "0").upper().strip()


def convert_file(file: str, control_table: Dict[str, str], normalization: str = "NFC") -> ET.ElementTree:
    xml = ET.parse(file)
    logging.info(f"Parsing {file}")
    for line in xml.xpath("//a:String", namespaces=NS):
        if not line.attrib["CONTENT"]:
            continue
        line.attrib["CONTENT"] = "".join([
            control_table.get(char, char)
            for char in unicodedata.normalize(normalization, str(line.attrib["CONTENT"]))
        ])
    return xml


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
@click.pass_context
def control(ctx: click.Context, table: str, files: Iterable[str], ignore: str):
    control_table = parse_table(table, normalization=ctx.obj["unorm"])
    errors = defaultdict(list)
    missing_chars = set()
    for file in tqdm.tqdm(files):
        if ignore in file:  # Skip converted content
            continue
        new_chars = check_file(file, table=control_table, normalization=ctx.obj["unorm"])
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


@main.command("generate")
@click.argument("table", type=click.Path(file_okay=True, dir_okay=False))
@click.argument("files", type=click.Path(exists=True, file_okay=True, dir_okay=False), nargs=-1)
@click.option("--restart", type=bool, is_flag=True, default=False, help="Write without taking into account prior"
                                                                        "existing data in `table`", show_default=True)
@click.pass_context
def generate(ctx: click.Context, table: str, files: Iterable[str], restart: bool = False):

    prior = {}

    if os.path.isfile(table) and not restart:
        with open(table) as f:
            r = csv.DictReader(f)
            for line in r:
                line = {key: unicodedata.normalize(ctx.obj["unorm"], val) for key, val in line.items()}
                prior[line["char"]] = line

    text = set()
    for file in files:
        with open(file) as f:
            text = text.union(set(f.read()))
    normal = sorted(list(text))
    content = []

    for line in normal:
        if not re.match(r"\s", line):
            line = unicodedata.normalize(ctx.obj["unorm"], line)
            cdict = {"char": line, "mufidecode": mufidecode.mufidecode(line), "codepoint": get_hex(line)}
            try:
                cdict["name"] = unicodedata.name(line)
            except ValueError:
                logging.warning(f"Character `{line}` has an unknown name (Unicode Hex Code Point: {get_hex(line)})")

            if line in prior:
                cdict = {
                    key: cdict.get(key, "").strip() or value
                    for key, value in prior[line].items()
                }
            content.append(cdict)

    with open(table, "w") as f:
        w = csv.DictWriter(f, fieldnames=["char", "name", "normalized", "codepoint", "mufidecode"])
        w.writeheader()
        w.writerows(content)


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

        xml = convert_file(file, control_table, normalization=ctx.obj["unorm"])
        with open(file.replace(".xml", suffix) if ".xml" in file else file+suffix, "w") as f:
            f.write(ET.tostring(xml, encoding=str, xml_declaration=True, pretty_print=True))


def main_wrap():
    main(obj={})


if __name__ == "__main__":
    main_wrap()
