import argparse
from pathlib import Path


def get_parser(site_name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{site_name.title()} Scraper")

    parser.add_argument(
        "--stage",
        type=int,
        nargs="+",
        choices=[1, 2],
        default=None,
        help="Stage(s) to run: 1 = link collection, 2 = raw data scraping (default: run both)",
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
        default=Path(f"config/{site_name}_sampling.json"),
        help=f"Path to per-category sampling config JSON (default: config/{site_name}_sampling.json)",
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
    parser.add_argument(
        "--fetch-mode",
        choices=["http", "browser"],
        default=None,
        help="Override stage 2's fetch mode (default: whatever the adapter config specifies)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Override stage 2's concurrency (default: whatever the adapter config specifies)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help=(
            "Resume stage 2 into an existing raw_data run, given as a compact "
            "DDMMHH folder name (e.g. 060711 for 06.07_11). Default: start a new run."
        ),
    )
    parser.add_argument(
        "-brt",
        "--breaker-rate-limited-threshold",
        type=int,
        default=None,
        help="Override how many rate_limited failures within the window trip the breaker (default: adapter config)",
    )
    parser.add_argument(
        "-bw",
        "--breaker-window-minutes",
        type=int,
        default=None,
        help="Override the rolling window (minutes) used to count rate_limited failures (default: adapter config)",
    )
    parser.add_argument(
        "-bp",
        "--breaker-pause-minutes",
        type=int,
        default=None,
        help="Override how long the breaker pauses before resuming after a rate_limited trip (default: adapter config)",
    )

    return parser
