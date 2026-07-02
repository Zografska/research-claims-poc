import argparse
from pathlib import Path


def get_conad_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Conad Scraper")

    parser.add_argument(
        "--stage",
        type=int,
        required=True,
        choices=[1, 2],
        help="Stage to run: 1 = link collection, 2 = raw data scraping",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Max number of pages to crawl (default: all pages)",
    )
    parser.add_argument(
        "--links",
        type=Path,
        default=None,
        help="Path to link_collection folder for stage 2 (default: most recent run)",
    )
    parser.add_argument(
        "--products",
        type=int,
        default=None,
        help="Global fallback cap per category when not set in --products-config (default: all)",
    )
    parser.add_argument(
        "--products-config",
        type=Path,
        default=Path("config/conad_sampling.json"),
        help="Path to per-category sampling config JSON (default: config/conad_sampling.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible product sampling (default: 42)",
    )
    parser.add_argument(
        "--max",
        action="store_true",
        help="Ignore all limits and scrape every product in every category",
    )

    return parser
