from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup


def extract_text_from_url(url: str) -> str:
    """Fetch and extract readable visible text from a URL."""
    if not url or not url.strip():
        return ""

    try:
        response = requests.get(
            url.strip(),
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-visible content blocks.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()
