import dataclasses
import json
import logging
from pathlib import Path

from src.adapters.base import SiteConfig
from src.stages.link_collector import collect_links
from src.stages.raw_scraper import scrape_raw
from src.utils.logger import setup_logger
from src.utils.parser import get_parser

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve_links_folder(arg: Path | None, link_collection_dir: Path) -> Path | None:
    if arg is not None:
        return arg
    if not link_collection_dir.exists():
        return None
    runs = sorted(link_collection_dir.iterdir(), reverse=True)
    return runs[0] if runs else None


def _resolve_resume_folder(compact: str | None, raw_data_dir: Path) -> Path | None:
    if not compact:
        return None
    if len(compact) != 6 or not compact.isdigit():
        raise ValueError(f"--resume expects a 6-digit DDMMHH value (e.g. 060711), got {compact!r}")
    day, month, hour = compact[:2], compact[2:4], compact[4:6]
    return raw_data_dir / f"{day}.{month}_{hour}"


def _load_sampling_config(path: Path) -> dict:
    if not path.exists():
        logging.warning(f"Sampling config not found at {path}, using fallback only")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning(f"Failed to load sampling config: {e}")
        return {}


async def run_main(site_name: str, cfg: SiteConfig) -> None:
    link_collection_dir = PROJECT_ROOT / "link_collection" / site_name
    raw_data_dir = PROJECT_ROOT / "raw_data" / site_name

    parser = get_parser(site_name)
    args = parser.parse_args()

    setup_logger()

    stages = set(args.stage) if args.stage else {1, 2}

    if 1 in stages:
        await collect_links(cfg, max_pages=args.pages)

    if 2 in stages:
        links_folder = _resolve_links_folder(args.links, link_collection_dir)
        if links_folder is None:
            logging.error("No link_collection folder found. Run stage 1 first.")
            return
        logging.info(f"Using links folder: {links_folder}")
        sampling_config = _load_sampling_config(args.products_config)
        overrides = {}
        if args.fetch_mode:
            overrides["raw_fetch_mode"] = args.fetch_mode
        if args.concurrency:
            overrides["concurrency"] = args.concurrency
        if args.breaker_rate_limited_threshold:
            overrides["breaker_rate_limited_threshold"] = args.breaker_rate_limited_threshold
        if args.breaker_window_minutes:
            overrides["breaker_window_minutes"] = args.breaker_window_minutes
        if args.breaker_pause_minutes:
            overrides["breaker_pause_minutes"] = args.breaker_pause_minutes
        run_cfg = dataclasses.replace(cfg, **overrides) if overrides else cfg
        await scrape_raw(
            run_cfg,
            links_folder,
            sampling_config=sampling_config,
            fallback=args.products,
            seed=args.seed,
            use_max=args.max,
            resume_folder=_resolve_resume_folder(args.resume, raw_data_dir),
        )
