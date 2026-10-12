import base64
import io

import pytest
from PIL import Image

from app.services.pdf_compilation_service import PdfCompilationService


def _image_base64():
    image = Image.new("RGB", (320, 180), color=(40, 90, 160))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_pdf_includes_all_screens_in_sequence_and_extends_contents_list():
    screens = [
        {
            "sequence": sequence,
            "name": f"Requirement screen {sequence:02d}",
            "screenType": "detail_view",
            "purpose": "Review the related business requirements.",
            "image_base64": _image_base64(),
        }
        for sequence in reversed(range(1, 21))
    ]

    service = PdfCompilationService()
    pdf_bytes = service.compile_pdf(
        "Claims Portal",
        "Claims Project",
        "claims-brd.pdf",
        "Claims workflow",
        screens,
    )

    import pymupdf

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        assert service.count_pages(pdf_bytes) == 22
        assert "Requirement screen 01" in document[0].get_text()
        assert "Requirement screen 20" in document[1].get_text()
        for screen_index in range(20):
            assert f"Requirement screen {screen_index + 1:02d}" in document[screen_index + 2].get_text()
        assert "Page 22 of 22" in document[21].get_text()
        assert "Local PyMuPDF renderer" in document[0].get_text()


def test_pdf_rejects_a_screen_with_no_generated_image():
    service = PdfCompilationService()

    with pytest.raises(ValueError, match="Generated image missing"):
        service.compile_pdf(
            "Claims Portal",
            "Claims Project",
            "claims-brd.pdf",
            "Claims workflow",
            [{"sequence": 1, "name": "Claims queue"}],
        )


def test_pdf_rejects_invalid_images_and_duplicate_sequences():
    service = PdfCompilationService()

    with pytest.raises(ValueError, match="not valid base64"):
        service.compile_pdf(
            "Claims Portal",
            "Claims Project",
            "claims-brd.pdf",
            "Claims workflow",
            [{"sequence": 1, "name": "Claims queue", "image_base64": "not-base64"}],
        )

    with pytest.raises(ValueError, match="Duplicate screen sequence"):
        service.compile_pdf(
            "Claims Portal",
            "Claims Project",
            "claims-brd.pdf",
            "Claims workflow",
            [
                {"sequence": 1, "name": "Claims queue", "image_base64": _image_base64()},
                {"sequence": 1, "name": "Claim details", "image_base64": _image_base64()},
            ],
        )


def test_pdf_rejects_empty_screen_lists():
    with pytest.raises(ValueError, match="At least one generated screen"):
        PdfCompilationService().compile_pdf("Claims Portal", "", "", "", [])


def test_pdf_discloses_when_the_brd_was_truncated():
    service = PdfCompilationService()
    pdf_bytes = service.compile_pdf(
        "Claims Portal",
        "Claims Project",
        "claims-brd.pdf",
        "Claims workflow. This plan is based on a truncated BRD excerpt; omitted content was not analyzed.",
        [{"sequence": 1, "name": "Claims queue", "image_base64": _image_base64()}],
    )

    import pymupdf

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        cover_text = document[0].get_text()
    assert "Coverage: PARTIAL" in cover_text
    assert "omitted content was not analyzed" in cover_text
    assert "Schema validated" in cover_text
