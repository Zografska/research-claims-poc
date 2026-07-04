import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")


def now_rome() -> datetime:
    return datetime.now(tz=TZ)


def fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m else f"{s}s"


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
