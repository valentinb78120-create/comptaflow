"""
Tesseract OCR fallback.

Used when the Mistral API is not configured or fails.  Quality is lower
than Mistral on real-world scans, but it keeps the pipeline functional
offline and at zero marginal cost.

PDF files are rasterized with pdf2image (poppler) before OCR.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytesseract
from PIL import Image

from app.services.mistral_ocr import InvoiceOCRResult, parse_invoice_text

logger = logging.getLogger(__name__)

# French + English models; PSM 4 = single column of text of variable sizes,
# a good default for invoices.
TESSERACT_CONFIG = "--psm 4"
TESSERACT_LANGS = "fra+eng"

# Cap pages rasterized from a PDF — invoices are virtually always 1-2 pages.
MAX_PDF_PAGES = 3


def run_tesseract(file_path: Path, mime_type: str) -> InvoiceOCRResult:
    """
    OCR *file_path* locally with Tesseract and return parsed invoice fields.

    Raises RuntimeError when the file cannot be read or rasterized.
    """
    if mime_type == "application/pdf":
        text = _ocr_pdf(file_path)
    else:
        text = _ocr_image(file_path)

    result = parse_invoice_text(text)
    result.raw_response = {"engine": "tesseract", "text_length": len(text)}
    # Tesseract output is noisier than Mistral — cap the confidence so that
    # invoices always land in human review.
    result.confidence = min(result.confidence, 0.6)
    return result


def _ocr_image(file_path: Path) -> str:
    """OCR a single raster image (JPG/PNG/TIFF/WebP)."""
    try:
        with Image.open(file_path) as img:
            # Tesseract works best on grayscale, reasonably sized images
            gray = img.convert("L")
            return pytesseract.image_to_string(gray, lang=TESSERACT_LANGS, config=TESSERACT_CONFIG)
    except (OSError, pytesseract.TesseractError) as exc:
        raise RuntimeError(f"Tesseract a échoué sur l'image: {exc}") from exc


def _ocr_pdf(file_path: Path) -> str:
    """Rasterize PDF pages (poppler) then OCR each page."""
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise RuntimeError("pdf2image non installé — fallback PDF indisponible") from exc

    try:
        pages = convert_from_path(str(file_path), dpi=300, first_page=1, last_page=MAX_PDF_PAGES)
    except Exception as exc:  # pdf2image raises various poppler errors
        raise RuntimeError(f"Rasterisation PDF impossible: {exc}") from exc

    chunks: list[str] = []
    for i, page in enumerate(pages):
        try:
            chunks.append(pytesseract.image_to_string(page.convert("L"), lang=TESSERACT_LANGS, config=TESSERACT_CONFIG))
        except pytesseract.TesseractError as exc:
            logger.warning("Tesseract a échoué sur la page %d: %s", i + 1, exc)

    if not chunks:
        raise RuntimeError("Aucune page PDF n'a pu être OCRisée")

    return "\n".join(chunks)
