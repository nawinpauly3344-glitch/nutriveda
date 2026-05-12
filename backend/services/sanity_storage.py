"""
Sanity asset storage — upload PDF/Word files to Sanity CDN.
Replaces local filesystem storage (which doesn't survive Render deploys).
"""

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

log = logging.getLogger(__name__)

SANITY_PROJECT_ID = os.getenv("SANITY_PROJECT_ID", "")
SANITY_DATASET = os.getenv("SANITY_DATASET", "production")
SANITY_API_VERSION = os.getenv("SANITY_API_VERSION", "2024-01-01")
SANITY_WRITE_TOKEN = os.getenv("SANITY_WRITE_TOKEN", "")


def _upload_url(asset_type: str = "file") -> str:
    """Build the Sanity asset upload endpoint URL."""
    return (
        f"https://{SANITY_PROJECT_ID}.api.sanity.io"
        f"/v{SANITY_API_VERSION}/assets/{asset_type}s/{SANITY_DATASET}"
    )


def upload_file(
    file_bytes: bytes,
    filename: str,
    content_type: str = "application/pdf",
) -> dict:
    """
    Upload a file to Sanity and return {"url": "<CDN URL>", "asset_id": "<Sanity asset _id>"}.
    Raises RuntimeError on failure.
    """
    if not SANITY_PROJECT_ID or not SANITY_WRITE_TOKEN:
        raise RuntimeError(
            "Sanity credentials not configured. "
            "Set SANITY_PROJECT_ID and SANITY_WRITE_TOKEN env vars."
        )

    try:
        resp = httpx.post(
            _upload_url("file"),
            headers={
                "Authorization": f"Bearer {SANITY_WRITE_TOKEN}",
                "Content-Type": content_type,
            },
            params={"filename": filename},
            content=file_bytes,
            timeout=60,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            doc = data.get("document", {})
            asset_url = doc.get("url", "")
            asset_id = doc.get("_id", "")
            log.info(f"Sanity upload OK: {filename} -> {asset_id}")
            return {"url": asset_url, "asset_id": asset_id}
        else:
            log.error(f"Sanity upload failed {resp.status_code}: {resp.text}")
            raise RuntimeError(f"Sanity upload {resp.status_code}: {resp.text}")

    except httpx.RequestError as e:
        log.error(f"Sanity upload request error: {e}")
        raise RuntimeError(f"Sanity request error: {e}")


def fetch_file_bytes(url: str) -> bytes:
    """Download a file from a Sanity CDN URL and return raw bytes."""
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.content
