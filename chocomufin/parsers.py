from typing import Iterable, Dict, Optional, Callable
from abc import ABCMeta

import lxml.etree as ET


class Parser(metaclass=ABCMeta):
    def __init__(self, filepath: str):
        self.fp = filepath
        self.xml = ET.parse(filepath)
        self.ns = self.get_ns(self.xml)

    @staticmethod
    def get_ns(xml: ET.ElementBase) -> Dict[str, str]:
        raise NotImplementedError

    def get_lines(self, set_callback: Optional[Callable[[str], str]] = None) -> Iterable[str]:
        raise NotImplementedError


class Alto(Parser):
    @staticmethod
    def get_ns(xml: ET.ElementBase) -> Dict[str, str]:
        return {"a": "http://www.loc.gov/standards/alto/ns-v4#"}

    def get_lines(self, set_callback: Optional[Callable[[str], str]] = None) -> Iterable[str]:
        for line in self.xml.xpath("//a:String", namespaces=self.ns):
            if not line.attrib["CONTENT"]:
                continue
            if set_callback is not None:
                line.attrib["CONTENT"] = set_callback(line.attrib["CONTENT"])
            yield line.attrib["CONTENT"]
