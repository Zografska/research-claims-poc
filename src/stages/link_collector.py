import asyncio
import logging
import random
import time
from collections import defaultdict
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from src.adapters.base import SiteConfig
from src.utils.browser import make_browser_config
from src.utils.http_client import fetch_html, make_http_client
from src.utils.storage import (
    fmt_duration,
    safe_filename,
    timestamped_folder,
    write_json,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LINK_COLLECTION_DIR = PROJECT_ROOT / "link_collection"


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
        f"| page {fmt_duration(page_time)} | uptime {fmt_duration(elapsed)}"
    )
    for cat, items in sorted(by_category.items()):
        logging.info(f"  {cat}: {len(items)}")


def _has_cards(html: str, cfg: SiteConfig) -> bool:
    return bool(BeautifulSoup(html, "html.parser").select(cfg.product_card_selector))


async def _fetch_page(
    crawler: AsyncWebCrawler,
    cfg: SiteConfig,
    js_code: str,
    page_num: int,
    max_retries: int = 3,
) -> str | None:
    delays = [5, 10, 20]

    for attempt in range(max_retries):
        try:
            if page_num == 1:
                run_cfg = CrawlerRunConfig(
                    session_id=cfg.session_id,
                    js_code=js_code,
                    page_timeout=cfg.page_timeout,
                    wait_until="networkidle",
                    wait_for=f"css:{cfg.product_card_selector}",
                )
                result = await crawler.arun(cfg.catalogue_url, config=run_cfg)
            else:
                run_cfg = CrawlerRunConfig(
                    session_id=cfg.session_id,
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


async def _fetch_listing_page(
    client: httpx.AsyncClient,
    cfg: SiteConfig,
    category_id: str,
    start: int,
    sem: asyncio.Semaphore,
    pause: asyncio.Event,
) -> list[dict]:
    async with sem:
        url = cfg.build_listing_url(cfg, category_id, start)
        html, _ = await fetch_html(client, url, pause)
        await asyncio.sleep(random.uniform(*cfg.inter_request_delay))
        return cfg.parse_cards(html, cfg) if html else []


async def _fetch_category_products(
    client: httpx.AsyncClient,
    cfg: SiteConfig,
    category_id: str,
    max_pages: int | None,
    sem: asyncio.Semaphore,
    pause: asyncio.Event,
    by_category: dict[str, list],
    out_folder: Path,
) -> list[dict]:
    first_url = cfg.build_listing_url(cfg, category_id, 0)
    html, _ = await fetch_html(client, first_url, pause)
    if html is None:
        return []

    total = cfg.get_product_count(html)
    by_category[category_id] = cfg.parse_cards(html, cfg)
    _flush(by_category, out_folder)

    starts = list(range(cfg.page_size, total, cfg.page_size))
    if max_pages:
        starts = starts[: max_pages - 1]

    tasks = [_fetch_listing_page(client, cfg, category_id, start, sem, pause) for start in starts]
    for coro in asyncio.as_completed(tasks):
        page_products = await coro
        by_category[category_id].extend(page_products)
        _flush(by_category, out_folder)

    return by_category[category_id]


async def _collect_links_http(cfg: SiteConfig, max_pages: int | None = None) -> Path:
    out_folder = timestamped_folder(LINK_COLLECTION_DIR, cfg.name)
    run_start = time.perf_counter()
    all_products: list[dict] = []
    by_category: dict[str, list] = defaultdict(list)
    pause = asyncio.Event()
    pause.set()

    async with make_http_client(cfg) as client:
        logging.info(f"Discovering categories from {cfg.bootstrap_url}")
        bootstrap_html = await fetch_html(client, cfg.bootstrap_url, pause)
        if bootstrap_html is None:
            logging.error("Failed to load bootstrap page. Aborting.")
            return out_folder

        categories = cfg.discover_categories(bootstrap_html, cfg)
        logging.info(f"Discovered {len(categories)} categories: {categories}")

        sem = asyncio.Semaphore(cfg.concurrency)

        for i, category_id in enumerate(categories, start=1):
            cat_start = time.perf_counter()
            products = await _fetch_category_products(
                client, cfg, category_id, max_pages, sem, pause, by_category, out_folder
            )
            all_products.extend(products)
            logging.info(
                f"Category {i}/{len(categories)} '{category_id}' — {len(products)} products "
                f"| {fmt_duration(time.perf_counter() - cat_start)} total "
                f"| uptime {fmt_duration(time.perf_counter() - run_start)}"
            )
            await asyncio.sleep(random.uniform(*cfg.inter_request_delay))

    logging.info(f"Stage 1 complete — {len(all_products)} total products → {out_folder}")
    return out_folder


async def collect_links(cfg: SiteConfig, max_pages: int | None = None) -> Path:
    if cfg.parse_cards is None:
        raise ValueError(f"Adapter '{cfg.name}' does not define parse_cards")

    if cfg.fetch_mode == "http":
        return await _collect_links_http(cfg, max_pages)

    out_folder = timestamped_folder(LINK_COLLECTION_DIR, cfg.name)
    browser_cfg = make_browser_config(cfg)
    all_products: list[dict] = []

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        run_start = time.perf_counter()

        logging.info(f"Loading {cfg.catalogue_url}")
        page_start = time.perf_counter()
        html = await _fetch_page(crawler, cfg, js_code=cfg.cookie_js or "", page_num=1)
        if html is None:
            logging.error("Failed to load catalogue page. Aborting.")
            return out_folder

        total_pages = cfg.get_total_pages(html) if cfg.get_total_pages else 1
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

        for page in range(2, total_pages + 1):
            page_start = time.perf_counter()
            html = await _fetch_page(crawler, cfg, js_code=cfg.next_page_js, page_num=page)
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
    logging.info(f"Stage 1 complete — {len(all_products)} total products → {out_folder}")
    return out_folder
