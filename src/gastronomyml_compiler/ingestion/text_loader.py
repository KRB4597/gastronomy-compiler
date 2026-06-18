"""Pass 0 — ingest raw text from file path or string."""

import hashlib
from pathlib import Path


def load_text(source: str | Path) -> tuple[str, str]:
    """Return (text, sha256).  source may be a file path or raw text."""
    path = Path(source)
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = str(source)
    sha = hashlib.sha256(text.encode()).hexdigest()
    return text, sha
