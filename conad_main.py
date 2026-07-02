import asyncio
import json
import logging
from pathlib import Path

from src.adapters.conad import CONAD
from src.stages.link_collector import collect_links
from src.stages.raw_scraper import scrape_raw
from src.utils.logger import setup_logger
from src.utils.parser import get_conad_parser

LINK_COLLECTION_DIR = Path(__file__).resolve().parent / "link_collection" / "conad"


def _resolve_links_folder(arg: Path | None) -> Path | None:
    if arg is not None:
        return arg
    if not LINK_COLLECTION_DIR.exists():
        return None
    runs = sorted(LINK_COLLECTION_DIR.iterdir(), reverse=True)
    return runs[0] if runs else None


def _load_sampling_config(path: Path) -> dict:
    if not path.exists():
        logging.warning(f"Sampling config not found at {path}, using fallback only")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning(f"Failed to load sampling config: {e}")
        return {}


async def main():
    parser = get_conad_parser()
    args = parser.parse_args()

    setup_logger()

    stages = set(args.stage) if args.stage else {1, 2}

    if 1 in stages:
        await collect_links(CONAD, max_pages=args.pages)

    if 2 in stages:
        links_folder = _resolve_links_folder(args.links)
        if links_folder is None:
            logging.error("No link_collection folder found. Run stage 1 first.")
            return
        logging.info(f"Using links folder: {links_folder}")
        sampling_config = _load_sampling_config(args.products_config)
        await scrape_raw(
            CONAD,
            links_folder,
            sampling_config=sampling_config,
            fallback=args.products,
            seed=args.seed,
            use_max=args.max,
        )


if __name__ == "__main__":
    asyncio.run(main())
