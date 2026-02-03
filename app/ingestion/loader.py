from __future__ import annotations

import asyncio
from typing import List

from pypdf import PdfReader


async def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Extract text from PDF bytes asynchronously.

    Args:
        data: Raw PDF file bytes.

    Returns:
        Extracted text as a single string.
    """
    def _read(d: bytes) -> str:
        reader = PdfReader(d)
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                pages.append("")
        return "\n".join(pages)

    return await asyncio.to_thread(_read, data)
