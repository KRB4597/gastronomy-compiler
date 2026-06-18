import json
from pathlib import Path

from ..ir.schemas import GastronomyIR


def export_json(ir: GastronomyIR, path: str | Path | None = None) -> str:
    payload = ir.model_dump(mode="json", exclude_none=True)
    text = json.dumps(payload, indent=2)
    if path:
        Path(path).write_text(text, encoding="utf-8")
    return text
