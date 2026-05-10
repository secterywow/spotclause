import os
import tempfile
import shutil
from typing import BinaryIO
from app.logger import get_logger

logger = get_logger(__name__)

# Allowed MIME types
ALLOWED_TYPES = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/webp': '.webp',
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_FREE_FILE_SIZE = 1 * 1024 * 1024  # 1MB for free users


def validate_file(file_data: bytes, content_type: str, is_free_user: bool = False) -> tuple[bool, str]:
    """Validate file size and type.
    Returns (is_valid, error_message)
    """
    # Check file type
    if content_type not in ALLOWED_TYPES:
        return False, f"Unsupported file type: {content_type}"

    # Check file size
    max_size = MAX_FREE_FILE_SIZE if is_free_user else MAX_FILE_SIZE
    if len(file_data) > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File too large. Maximum size: {max_mb}MB"

    return True, ""


def save_temp_file(file_data: bytes, content_type: str) -> str:
    """Save file data to a temporary file.
    Returns the path to the temp file.
    """
    suffix = ALLOWED_TYPES.get(content_type, '.tmp')
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(file_data)
        return path
    except:
        os.close(fd)
        raise


def parse_file_sync(file_path: str, mime_type: str) -> dict:
    """Synchronous file parsing (for non-Celery use)."""
    if mime_type == 'application/pdf':
        return _parse_pdf(file_path)
    elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return _parse_word(file_path)
    elif mime_type.startswith('image/'):
        return _parse_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")


def _parse_pdf(file_path: str) -> dict:
    import pdfplumber

    text = ""
    page_count = 0

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

    return {"text": text.strip(), "page_count": page_count, "type": "pdf"}


def _parse_word(file_path: str) -> dict:
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text.strip())

    return {"text": "\n\n".join(paragraphs), "page_count": len(doc.sections), "type": "word"}


def _parse_image(file_path: str) -> dict:
    from PIL import Image
    import pytesseract

    image = Image.open(file_path)
    text = pytesseract.image_to_string(image, lang='eng+chi_sim+chi_tra')

    return {"text": text.strip(), "page_count": 1, "type": "image"}
