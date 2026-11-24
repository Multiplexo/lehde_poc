"""Read PDFs and DOCX files into page texts with line positions.

Text PDFs are read with PDFium; pages without a text layer (scans) are read with
Tesseract. Positions are stored relative to the page so the frontend can mark a
quote on the rendered page.
"""

import base64
from io import BytesIO

import pypdfium2 as pdfium
import pytesseract
import structlog
from docx import Document as DocxDocument
from PIL import Image

from app.models.documents import Box, PageLine, PageText
from app.services.pipeline.gaeb import GAEB_CONTENT_TYPE, is_gaeb, read_gaeb

logger = structlog.get_logger(__name__)

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
SUPPORTED_CONTENT_TYPES = {PDF_CONTENT_TYPE, DOCX_CONTENT_TYPE, GAEB_CONTENT_TYPE}
OCR_RENDER_SCALE = 2.0
DOCX_PAGE_CHARACTERS = 3500
MAX_IMAGE_SIDE = 2000


def detect_content_type(content: bytes, filename: str) -> str | None:
    if content.startswith(b"%PDF-"):
        return PDF_CONTENT_TYPE
    if content.startswith(b"PK") and filename.lower().endswith(".docx"):
        return DOCX_CONTENT_TYPE
    if is_gaeb(content, filename):
        return GAEB_CONTENT_TYPE
    return None


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _text_lines(page: pdfium.PdfPage, width: float, height: float) -> list[PageLine]:
    text_page = page.get_textpage()
    try:
        lines: list[PageLine] = []
        for index in range(text_page.count_rects()):
            left, bottom, right, top = text_page.get_rect(index)
            text = " ".join(
                text_page.get_text_bounded(left, bottom, right, top).split()
            )
            if not text:
                continue
            lines.append(
                PageLine(
                    text=text,
                    box=Box(
                        x=_clamp(left / width),
                        y=_clamp((height - top) / height),
                        width=_clamp((right - left) / width),
                        height=_clamp((top - bottom) / height),
                    ),
                )
            )
        return lines
    finally:
        text_page.close()


def _ocr_lines(page: pdfium.PdfPage, languages: str) -> list[PageLine]:
    """Read a scanned page with Tesseract and group words into lines."""
    bitmap = page.render(scale=OCR_RENDER_SCALE)  # pyright: ignore[reportArgumentType]
    try:
        image = bitmap.to_pil().convert("L")
    finally:
        bitmap.close()
    image_width, image_height = image.size
    data = pytesseract.image_to_data(
        image, lang=languages, output_type=pytesseract.Output.DICT
    )
    grouped: dict[tuple[int, int, int], list[int]] = {}
    for index, word in enumerate(data["text"]):
        if not str(word).strip():
            continue
        key = (
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index],
        )
        grouped.setdefault(key, []).append(index)
    lines: list[PageLine] = []
    for indexes in grouped.values():
        left = min(data["left"][i] for i in indexes)
        top = min(data["top"][i] for i in indexes)
        right = max(data["left"][i] + data["width"][i] for i in indexes)
        bottom = max(data["top"][i] + data["height"][i] for i in indexes)
        lines.append(
            PageLine(
                text=" ".join(str(data["text"][i]).strip() for i in indexes),
                box=Box(
                    x=_clamp(left / image_width),
                    y=_clamp(top / image_height),
                    width=_clamp((right - left) / image_width),
                    height=_clamp((bottom - top) / image_height),
                ),
            )
        )
    return lines


def read_pdf(
    content: bytes, ocr_languages: str | None, min_text: int
) -> list[PageText]:
    pdf = pdfium.PdfDocument(content)
    try:
        pages: list[PageText] = []
        for index in range(len(pdf)):
            page = pdf[index]
            try:
                width, height = page.get_size()
                lines = _text_lines(page, width, height)
                characters = sum(len(line.text) for line in lines)
                ocr = False
                if ocr_languages and characters < min_text:
                    lines = _ocr_lines(page, ocr_languages)
                    ocr = True
                pages.append(
                    PageText(
                        number=index + 1,
                        width=width,
                        height=height,
                        ocr=ocr,
                        lines=lines,
                    )
                )
            finally:
                page.close()
        return pages
    finally:
        pdf.close()


def read_docx(content: bytes) -> list[PageText]:
    """Split a Word document into pseudo pages; DOCX has no fixed page layout."""
    document = DocxDocument(BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            paragraphs.append(" | ".join(cell.text.strip() for cell in row.cells))
    pages: list[PageText] = []
    current: list[PageLine] = []
    size = 0
    for paragraph in paragraphs:
        text = " ".join(paragraph.split())
        if not text:
            continue
        current.append(PageLine(text=text))
        size += len(text)
        if size >= DOCX_PAGE_CHARACTERS:
            pages.append(PageText(number=len(pages) + 1, lines=current))
            current, size = [], 0
    if current or not pages:
        pages.append(PageText(number=len(pages) + 1, lines=current))
    return pages


def read_document(
    content: bytes, content_type: str, ocr_languages: str | None, min_text: int
) -> list[PageText]:
    """Read pages; OCR runs for scanned pages when languages are given."""
    if content_type == PDF_CONTENT_TYPE:
        return read_pdf(content, ocr_languages, min_text)
    if content_type == DOCX_CONTENT_TYPE:
        return read_docx(content)
    if content_type == GAEB_CONTENT_TYPE:
        return read_gaeb(content)
    raise ValueError("Unsupported content type")


def _to_data_url(image: Image.Image) -> str:
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def render_page_images(
    content: bytes, page_numbers: list[int], with_title_block: bool
) -> dict[int, list[str]]:
    """Render pages for the vision model; plans also get the title block area.

    Title blocks (Plankopf) usually sit in the lower right corner, so that area is
    rendered again at a higher resolution.
    """
    pdf = pdfium.PdfDocument(content)
    try:
        images: dict[int, list[str]] = {}
        for number in page_numbers:
            if number < 1 or number > len(pdf):
                continue
            page = pdf[number - 1]
            try:
                width, height = page.get_size()
                scale = min(3.0, MAX_IMAGE_SIDE / max(width, height))
                bitmap = page.render(scale=scale)  # pyright: ignore[reportArgumentType]
                try:
                    full = bitmap.to_pil()
                finally:
                    bitmap.close()
                page_images = [_to_data_url(full)]
                if with_title_block:
                    crop_scale = min(4.0, MAX_IMAGE_SIDE / (max(width, height) * 0.45))
                    crop = (width * 0.55, 0, 0, height * 0.55)
                    bitmap = page.render(scale=crop_scale, crop=crop)  # pyright: ignore[reportArgumentType]
                    try:
                        page_images.append(_to_data_url(bitmap.to_pil()))
                    finally:
                        bitmap.close()
                images[number] = page_images
            finally:
                page.close()
        return images
    finally:
        pdf.close()
