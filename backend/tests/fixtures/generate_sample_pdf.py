"""One-time generator for backend/tests/fixtures/sample.pdf.

Produces a two-page PDF where page 1 contains the single line
"Page one content." and page 2 contains the single line
"Page two content.". Re-run this script only if the fixture needs to be
regenerated; the resulting sample.pdf is committed to the repository.
"""
from reportlab.pdfgen import canvas

PDF_PATH = "backend/tests/fixtures/sample.pdf"


def generate() -> None:
    pdf_canvas = canvas.Canvas(PDF_PATH, pagesize=(612, 792))

    pdf_canvas.drawString(72, 700, "Page one content.")
    pdf_canvas.showPage()

    pdf_canvas.drawString(72, 700, "Page two content.")
    pdf_canvas.showPage()

    pdf_canvas.save()


if __name__ == "__main__":
    generate()
