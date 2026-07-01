import asyncio
import logging
import random
import time
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from src.adapters.base import SiteConfig
from src.utils.browser import make_browser_config
from src.utils.storage import safe_filename, timestamped_folder, write_json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LINK_COLLECTION_DIR = PROJECT_ROOT / "link_collection"
SESSION_ID = "conad_catalogue"


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m else f"{s}s"


def _log_page_summary(
    page: int,
    total_pages: int,
    products: list[dict],
    by_category: dict,
    running_total: int,
    page_time: float,
    elapsed: float,
) -> None:
    logging.info(
        f"Page {page}/{total_pages} — {len(products)} new | {running_total} total "
        f"| page {_fmt(page_time)} | uptime {_fmt(elapsed)}"
    )
    for cat, items in sorted(by_category.items()):
        logging.info(f"  {cat}: {len(items)}")


def _get_total_pages(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.select("div.component-Pagination a[data-page]")
    if not pages:
        return 1
    return max(int(p["data-page"]) for p in pages)


def _has_cards(html: str, cfg: SiteConfig) -> bool:
    return bool(BeautifulSoup(html, "html.parser").select(cfg.product_card_selector))


async def _fetch_page(
    crawler: AsyncWebCrawler,
    cfg: SiteConfig,
    js_code: str,
    page_num: int,
    max_retries: int = 3,
) -> str | None:
    """
    Fetch the current page using the persistent session.
    For page 1: loads the catalogue URL fresh.
    For page 2+: runs next_page_js on the existing tab without reloading.
    """
    delays = [5, 10, 20]

    for attempt in range(max_retries):
        try:
            if page_num == 1:
                # Fresh load: navigate to URL, accept cookies
                run_cfg = CrawlerRunConfig(
                    session_id=SESSION_ID,
                    js_code=js_code,
                    page_timeout=cfg.page_timeout,
                    wait_until="networkidle",
                    wait_for=f"css:{cfg.product_card_selector}",
                )
                result = await crawler.arun(cfg.catalogue_url, config=run_cfg)
            else:
                # Stay on the same tab — run next_page_js without reloading
                run_cfg = CrawlerRunConfig(
                    session_id=SESSION_ID,
                    js_code=js_code,
                    js_only=True,
                    page_timeout=cfg.page_timeout,
                    wait_for=f"css:{cfg.product_card_selector}",
                )
                result = await crawler.arun(cfg.catalogue_url, config=run_cfg)

            if _has_cards(result.html, cfg):
                return result.html

            logging.warning(f"No cards on page {page_num}, attempt {attempt + 1}")

        except Exception as e:
            logging.warning(f"Page {page_num} failed on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(delays[attempt])

    logging.error(f"All retries failed for page {page_num}")
    return None


def _flush(by_category: dict, out_folder: Path) -> None:
    for category, products in by_category.items():
        path = out_folder / f"{safe_filename(category)}.json"
        write_json(path, products)


async def collect_links(cfg: SiteConfig, max_pages: int | None = None) -> Path:
    if cfg.parse_cards is None:
        raise ValueError(f"Adapter '{cfg.name}' does not define parse_cards")

    out_folder = timestamped_folder(LINK_COLLECTION_DIR, cfg.name)
    browser_cfg = make_browser_config(cfg)
    all_products: list[dict] = []

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        run_start = time.perf_counter()

        # Page 1: fresh load + accept cookies
        logging.info(f"Loading {cfg.catalogue_url}")
        page_start = time.perf_counter()
        html = await _fetch_page(crawler, cfg, js_code=cfg.cookie_js or "", page_num=1)
        if html is None:
            logging.error("Failed to load catalogue page. Aborting.")
            return out_folder

        total_pages = _get_total_pages(html)
        if max_pages:
            total_pages = min(max_pages, total_pages)
        logging.info(f"Total pages to crawl: {total_pages}")

        products = cfg.parse_cards(html, cfg)
        all_products.extend(products)
        by_category: dict[str, list] = defaultdict(list)
        for p in products:
            by_category[p.get("category_l1") or "uncategorised"].append(p)
        _flush(by_category, out_folder)
        _log_page_summary(
            page=1,
            total_pages=total_pages,
            products=products,
            by_category=by_category,
            running_total=len(all_products),
            page_time=time.perf_counter() - page_start,
            elapsed=time.perf_counter() - run_start,
        )

        # Pages 2+: click next on the same tab
        for page in range(2, total_pages + 1):
            page_start = time.perf_counter()
            html = await _fetch_page(
                crawler, cfg, js_code=cfg.next_page_js, page_num=page
            )
            if html is None:
                logging.warning(f"Skipping page {page} after all retries failed")
                continue

            products = cfg.parse_cards(html, cfg)
            all_products.extend(products)
            for p in products:
                by_category[p.get("category_l1") or "uncategorised"].append(p)
            _flush(by_category, out_folder)
            _log_page_summary(
                page=page,
                total_pages=total_pages,
                products=products,
                by_category=by_category,
                running_total=len(all_products),
                page_time=time.perf_counter() - page_start,
                elapsed=time.perf_counter() - run_start,
            )

            delay = random.uniform(*cfg.inter_request_delay)
            await asyncio.sleep(delay)

    _flush(by_category, out_folder)
    logging.info(
        f"Stage 1 complete — {len(all_products)} total products → {out_folder}"
    )
    return out_folder
