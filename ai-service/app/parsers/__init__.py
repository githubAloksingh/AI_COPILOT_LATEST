from .base import DocumentParser
from .pdf_parser import PdfParser
from .docx_parser import DocxParser
from .csv_parser import CsvParser
from .txt_parser import TextParser

ALL_PARSERS = [
    PdfParser(),
    DocxParser(),
    CsvParser(),
    TextParser()
]

__all__ = ["DocumentParser", "PdfParser", "DocxParser", "CsvParser", "TextParser", "ALL_PARSERS"]
