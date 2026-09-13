"""Page-aware PDF extraction tests using generated, small local fixtures."""
from io import BytesIO
from reportlab.pdfgen import canvas
from app.services.documents.parsers.pdf_parser import extract_pages


def pdf_with_pages(*pages: str) -> bytes:
    buffer = BytesIO(); report = canvas.Canvas(buffer)
    for text in pages:
        report.drawString(72, 720, text); report.showPage()
    report.save(); return buffer.getvalue()


def test_pdf_extraction_keeps_page_order_and_usable_decisions() -> None:
    content = pdf_with_pages("Pump P-101 vibration is 4.2 mm/s.", "", "Pump P-202 temperature is 72 C.")
    pages = extract_pages(content)
    assert [page.page_number for page in pages] == [1, 2, 3]
    assert pages[0].usable and not pages[1].usable and pages[2].usable
    assert "P-101" in pages[0].text
