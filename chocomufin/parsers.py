from typing import Iterable, Dict, Optional, Callable, List
from abc import ABCMeta

import lxml.etree as ET


class Parser(metaclass=ABCMeta):
    def __init__(self, filepath: str):
        self.fp = filepath

    def get_lines(self, set_callback: Optional[Callable[[str], str]] = None) -> Iterable[str]:
        raise NotImplementedError

    def dump(self) -> str:
        raise NotImplementedError


class XmlParser(Parser):
    def __init__(self, filepath: str):
        super(XmlParser, self).__init__(filepath)
        self.xml = ET.parse(filepath)
        self.ns = self.get_ns(self.xml)

    @staticmethod
    def get_ns(xml: ET.ElementBase) -> Dict[str, str]:
        raise NotImplementedError

    def dump(self):
        return ET.tostring(self.xml, encoding=str, xml_declaration=False, pretty_print=True)


class Alto(XmlParser):
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
        return


class PlainText(Parser):
    def __init__(self, filepath: str):
        super(PlainText, self).__init__(filepath)
        with open(self.fp) as file:
            self._text: List[str] = list(file.readlines())

    def get_lines(self, set_callback: Optional[Callable[[str], str]] = None) -> Iterable[str]:
        if set_callback:
            for line_id, line in enumerate(self._text):
                if line.strip():
                    self._text[line_id] = set_callback(line)
                    yield self._text[line_id]
        else:
            yield from [text for text in self._text if text.strip()]

    def dump(self) -> str:
        return "".join(self._text)
