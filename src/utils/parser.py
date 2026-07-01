import argparse


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

    return parser
