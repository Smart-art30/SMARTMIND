# posts/watermark.py
import io
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from pypdf import PdfReader, PdfWriter


def _make_watermark_page(text, width, height):
    """
    Build a 1-page PDF containing the diagonal watermark text.

    Tuned for visibility: darker, larger, more opaque than the
    original subtle style — but still readable for exam content.
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(width, height))

    c.saveState()

    # ---- VISIBILITY SETTINGS ----
    c.setFont("Helvetica-Bold", 60)                        # bigger
    c.setFillColor(Color(0.20, 0.20, 0.20, alpha=0.50))    # darker + more opaque

    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()

    c.save()
    packet.seek(0)
    return PdfReader(packet).pages[0]


def watermark_pdf(source, label="Smarmind"):
    """Apply a diagonal watermark to every page of a PDF."""
    if isinstance(source, (bytes, bytearray)):
        reader = PdfReader(io.BytesIO(source))
    else:
        reader = PdfReader(source)

    writer = PdfWriter()

    for page in reader.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        page.merge_page(_make_watermark_page(label, w, h))
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output