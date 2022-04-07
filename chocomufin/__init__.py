import unicodedata
import logging
import csv
import sys
import re
import os
from typing import Iterable
from collections import defaultdict

import mufidecode
import tabulate
import lxml.etree as ET
import click
import tqdm

from chocomufin import parse_table, get_hex
from chocomufin.funcs import parse_table, check_file, get_hex, convert_file
from chocomufin import cmds

from .parsers import Parser, Alto
logging.getLogger().setLevel(logging.INFO)


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



def main_wrap():
    main(obj={})


if __name__ == "__main__":
    main_wrap()
