import io
import pytest
from app.parsers.txt_parser import TextParser
from app.parsers.csv_parser import CsvParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.docx_parser import DocxParser
from app.services.document_service import DocumentService


def test_txt_parser():
    parser = TextParser()
    assert parser.supports("text/plain", "notes.txt")
    assert parser.supports("", "doc.md")
    assert parser.supports("application/json", "data.json")
    
    content = b"Hello World!\nThis is a test document."
    extracted = parser.parse(content)
    assert "Hello World!" in extracted
    assert "test document" in extracted


def test_csv_parser():
    parser = CsvParser()
    assert parser.supports("text/csv", "data.csv")
    assert parser.supports("", "records.csv")
    
    csv_content = b"Name,Role,Team\nAlice,Developer,Backend\nBob,QA,Automation\n"
    extracted = parser.parse(csv_content)
    assert "Row 1: Name=Alice, Role=Developer, Team=Backend" in extracted
    assert "Row 2: Name=Bob, Role=QA, Team=Automation" in extracted


import zipfile
from app.parsers.zip_parser import ZipParser


def test_document_service_cleaning():
    service = DocumentService()
    raw = "Line 1\r\n\r\n\r\n\r\nLine 2\x00\r\n"
    cleaned = service.clean_text(raw)
    assert "\x00" not in cleaned
    assert "\r" not in cleaned
    assert "Line 1\n\nLine 2" == cleaned


def test_zip_parser():
    parser = ZipParser()
    assert parser.supports("application/zip", "project.zip")
    assert parser.supports("application/x-zip-compressed", "code.zip")
    assert parser.supports("", "archive.zip")
    assert not parser.supports("application/pdf", "doc.pdf")

    # Create an in-memory zip file with sample code
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("src/App.java", "public class App { public static void main(String[] args) {} }")
        z.writestr("README.md", "# Test Project\nSample repository for testing.")

    zip_bytes = buf.getvalue()
    extracted = parser.parse(zip_bytes)
    assert "src/App.java" in extracted
    assert "public class App" in extracted
    assert "Test Project" in extracted

