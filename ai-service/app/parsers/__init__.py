from .base import DocumentParser
from .pdf_parser import PdfParser
from .docx_parser import DocxParser
from .csv_parser import CsvParser
from .txt_parser import TextParser
from .zip_parser import ZipParser

ALL_PARSERS = [
    PdfParser(),
    DocxParser(),
    CsvParser(),
    TextParser(),
    ZipParser()
]

__all__ = ["DocumentParser", "PdfParser", "DocxParser", "CsvParser", "TextParser", "ZipParser", "ALL_PARSERS"]

