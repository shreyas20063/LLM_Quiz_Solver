"""
Optional media/ocr helpers that call external services if configured.

These functions are no-ops unless you provide service endpoints via env vars.
"""
import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


async def transcribe_media(media_url: str) -> Optional[str]:
    """
    Send a media URL (audio/video) to an external transcription service.

    Requires env:
      MEDIA_TRANSCRIBE_ENDPOINT: endpoint that accepts POST {"url": media_url}
      MEDIA_TRANSCRIBE_API_KEY: optional bearer token
    """
    endpoint = os.getenv("MEDIA_TRANSCRIBE_ENDPOINT")
    if not endpoint:
        logger.info("MEDIA_TRANSCRIBE_ENDPOINT not set; skipping media transcription")
        return None

    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("MEDIA_TRANSCRIBE_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, json={"url": media_url}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # Common keys: transcript, text, result
            for key in ("transcript", "text", "result"):
                if key in data and isinstance(data[key], str):
                    logger.info("Received media transcript from external service")
                    return data[key]
            logger.warning("Transcription response missing expected keys")
            return None
    except Exception as exc:
        logger.warning(f"Media transcription failed: {exc}")
        return None


async def ocr_image(image_url: str) -> Optional[str]:
    """
    Send an image URL to an external OCR service.

    Requires env:
      OCR_ENDPOINT: endpoint that accepts POST {"url": image_url}
      OCR_API_KEY: optional bearer token
    """
    endpoint = os.getenv("OCR_ENDPOINT")
    if not endpoint:
        logger.info("OCR_ENDPOINT not set; skipping OCR")
        return None

    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("OCR_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint, json={"url": image_url}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            for key in ("text", "result", "ocr"):
                if key in data and isinstance(data[key], str):
                    logger.info("Received OCR text from external service")
                    return data[key]
            logger.warning("OCR response missing expected keys")
            return None
    except Exception as exc:
        logger.warning(f"OCR failed: {exc}")
        return None
