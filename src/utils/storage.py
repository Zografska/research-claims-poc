import json
from pathlib import Path

from src.utils.time import now_rome


def timestamped_folder(base: Path, site_name: str) -> Path:
    ts = now_rome().strftime("%d.%m_%H")
    folder = base / site_name / ts
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_json(path: Path, data: list | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_filename(name: str) -> str:
    return name.lower().replace(" ", "-").replace("/", "-").replace("'", "").replace(",", "").strip("-")
