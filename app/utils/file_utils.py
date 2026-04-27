import re
import uuid
from pathlib import Path

from app.core.config import settings


def allowed_file(filename: str) -> bool:
    suffix = Path(filename).suffix.lower()
    return suffix in settings.allowed_extensions


def safe_stored_name(original: str) -> str:
    base = Path(original).name
    base = re.sub(r"[^\w.\-]", "_", base, flags=re.UNICODE)
    if not base or base.startswith("."):
        base = "upload"
    uid = uuid.uuid4().hex[:12]
    stem = Path(base).stem[:80] or "file"
    ext = Path(base).suffix.lower()[:10]
    return f"{stem}_{uid}{ext}"
