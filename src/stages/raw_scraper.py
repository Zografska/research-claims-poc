import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from src.adapters.base import SiteConfig
from src.utils.browser import make_browser_config
from src.utils.http_client import fetch_html, make_http_client
from src.utils.storage import fmt_duration, now_rome, timestamped_folder, write_json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"


async def _download_image(url: str, path: Path) -> None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
            path.write_bytes(r.content)
    except Exception as e:
        logging.warning(f"Image download failed {url}: {e}")


def _load_done(out_json: Path) -> set[str]:
    if not out_json.exists():
        return set()
    try:
        return {p["url"] for p in json.loads(out_json.read_text(encoding="utf-8")) if "url" in p}
    except Exception:
        return set()


async def _fetch_one(
    crawler: AsyncWebCrawler,
    cfg: SiteConfig,
    url: str,
    sem: asyncio.Semaphore,
) -> tuple[str, object, float, str | None]:
    async with sem:
        page_start = time.perf_counter()
        reason = None
        try:
            run_cfg = CrawlerRunConfig(
                js_code=cfg.cookie_js or "",
                page_timeout=60000,
                wait_until="domcontentloaded",
            )
            result = await crawler.arun(url, config=run_cfg)
            html = result.html or ""

            if html and BeautifulSoup(html, "html.parser").select_one(f"[{cfg.detail_data_attr}]"):
                await asyncio.sleep(random.uniform(*cfg.inter_request_delay))
                return url, result, time.perf_counter() - page_start, None

            status = getattr(result, "status_code", None)
            if status == 429:
                reason = "rate_limited"
            elif status == 403 or "access denied" in html.lower():
                reason = "forbidden"
            elif status and status != 200:
                reason = f"http_{status}"
            else:
                reason = "no_selector_found"
            logging.warning(f"{reason} for {url} (status={status})")
        except Exception as e:
            reason = type(e).__name__
            logging.warning(f"Failed to fetch {url}: {e}")
        return url, None, time.perf_counter() - page_start, reason


async def _fetch_one_http(
    client: httpx.AsyncClient,
    cfg: SiteConfig,
    url: str,
    sem: asyncio.Semaphore,
    pause: asyncio.Event,
) -> tuple[str, object, float, str | None]:
    async with sem:
        page_start = time.perf_counter()
        html, fail_reason = await fetch_html(client, url, pause)
        await asyncio.sleep(random.uniform(*cfg.inter_request_delay))
        result = SimpleNamespace(success=True, html=html) if html else None
        return url, result, time.perf_counter() - page_start, fail_reason


def _resolve_todo(
    products: list[dict],
    done_urls: set[str],
    category: str,
    sampling_config: dict,
    fallback: int | None,
    use_max: bool,
    seed: int,
) -> list[dict]:
    if use_max:
        return [p for p in products if p.get("product_url") not in done_urls]

    limit = sampling_config.get(category) if sampling_config else None
    if limit is None:
        limit = fallback

    if limit is None or limit >= len(products):
        return [p for p in products if p.get("product_url") not in done_urls]

    sample = random.Random(seed).sample(products, limit)
    return [p for p in sample if p.get("product_url") not in done_urls]


def _check_breaker(failures: list[dict], cfg: SiteConfig) -> tuple[str, str] | None:
    if not failures:
        return None

    latest = failures[-1]
    if latest["reason"] == "forbidden":
        return "abort", "got 'forbidden' (403)"

    if latest["reason"] == "rate_limited":
        window_start = now_rome() - timedelta(minutes=cfg.breaker_window_minutes)
        recent = [
            f
            for f in failures
            if f["reason"] == "rate_limited" and datetime.fromisoformat(f["failed_at"]) >= window_start
        ]
        if len(recent) >= cfg.breaker_rate_limited_threshold:
            return "pause", f"{len(recent)} rate_limited failures in the last {cfg.breaker_window_minutes} minutes"

    return None

    return None


async def scrape_raw(
    cfg: SiteConfig,
    links_folder: Path,
    sampling_config: dict | None = None,
    fallback: int | None = None,
    seed: int = 42,
    use_max: bool = False,
    resume_folder: Path | None = None,
) -> Path:
    if cfg.parse_product_page is None:
        raise ValueError(f"Adapter '{cfg.name}' does not define parse_product_page")

    mode = cfg.raw_fetch_mode or cfg.fetch_mode
    out_folder = resume_folder if resume_folder else timestamped_folder(RAW_DATA_DIR, cfg.name)
    run_start = time.perf_counter()
    sem = asyncio.Semaphore(cfg.concurrency)
    pause = asyncio.Event()
    pause.set()

    summary_path = out_folder / "run_summary.json"
    existing_summary = {}
    if summary_path.exists():
        try:
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    started_at_str = existing_summary.get("started_at") or now_rome().isoformat(timespec="seconds")

    failures_path = out_folder / "run_failures.json"
    failures: list[dict] = []
    if failures_path.exists():
        try:
            failures = json.loads(failures_path.read_text(encoding="utf-8"))
        except Exception:
            failures = []

    category_files = sorted(links_folder.glob("*.json"))
    logging.info(f"Found {len(category_files)} categories in {links_folder}")

    category_plan = []
    for cat_file in category_files:
        category = cat_file.stem
        try:
            products = json.loads(cat_file.read_text(encoding="utf-8"))
        except Exception as e:
            logging.warning(f"Skipping {category}: could not read {cat_file} — {e}")
            continue
        done_urls = _load_done(out_folder / f"{category}.json")
        todo = _resolve_todo(
            products,
            done_urls,
            category,
            sampling_config or {},
            fallback,
            use_max,
            seed,
        )
        category_plan.append((cat_file, category, products, done_urls, todo))

    global_total = sum(len(todo) for _, _, _, _, todo in category_plan)
    logging.info(f"Total products to scrape this run: {global_total}")

    total_ok = existing_summary.get("total_ok", 0)
    total_fail = existing_summary.get("total_failed", 0)
    cat_stats: dict[str, dict] = dict(existing_summary.get("categories", {}))

    if mode == "http":
        conn_cm = make_http_client(cfg)
    else:
        conn_cm = AsyncWebCrawler(config=make_browser_config(cfg))

    async with conn_cm as conn:
        for cat_file, category, products, done_urls, todo in category_plan:
            out_json = out_folder / f"{category}.json"
            img_folder = out_folder / category
            img_folder.mkdir(parents=True, exist_ok=True)

            if not todo:
                logging.info(f"{category}: already complete, skipping")
                prior = cat_stats.get(category, {"ok": 0, "failed": 0})
                cat_stats[category] = {
                    "ok": prior.get("ok", 0),
                    "failed": prior.get("failed", 0),
                    "skipped": True,
                }
                continue

            logging.info(f"{category}: {len(todo)} to scrape, {len(done_urls)} already done")

            records = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else []
            url_to_product = {p["product_url"]: p for p in todo}
            cat_start = time.perf_counter()
            prior_ok = cat_stats.get(category, {}).get("ok", 0)
            prior_fail = cat_stats.get(category, {}).get("failed", 0)
            cat_ok, cat_fail = 0, 0

            if mode == "http":
                tasks = [asyncio.create_task(_fetch_one_http(conn, cfg, p["product_url"], sem, pause)) for p in todo]
            else:
                tasks = [asyncio.create_task(_fetch_one(conn, cfg, p["product_url"], sem)) for p in todo]
            breaker_action = None
            for coro in asyncio.as_completed(tasks):
                url, result, page_time, fetch_fail_reason = await coro
                product = url_to_product[url]
                product_id = None
                ean = None
                fail_reason = None

                if not result or not result.success or not result.html:
                    logging.warning(f"Skipping {url}")
                    fail_reason = fetch_fail_reason or "fetch_failed"
                else:
                    parsed = cfg.parse_product_page(result.html, cfg)
                    if not parsed:
                        logging.warning(f"No content parsed from {url}")
                        fail_reason = "parse_failed"
                    else:
                        ean = parsed.pop("ean", None)
                        product_id = product.get("product_id")
                        if not product_id:
                            logging.warning(f"No product_id at {url}")
                            fail_reason = "no_product_id"

                if product_id:
                    if any(f["url"] == url for f in failures):
                        failures = [f for f in failures if f["url"] != url]
                        write_json(failures_path, failures)

                    img_path = img_folder / f"{product_id}.jpg"
                    if not img_path.exists() and product.get("image_url"):
                        await _download_image(product["image_url"], img_path)

                    record = {
                        "product_id": product_id,
                        "ean": ean,
                        "scraped_at": now_rome().isoformat(timespec="seconds"),
                        "code": product.get("code", ""),
                        "name": product.get("name", ""),
                        "url": url,
                        **parsed,
                    }
                    records.append(record)
                    write_json(out_json, records)
                    cat_ok += 1
                    total_ok += 1
                    logging.info(
                        f"  [{total_ok + total_fail}/{global_total}] {product_id} — {product.get('name', '')} "
                        f"| page {fmt_duration(page_time)} | uptime {fmt_duration(time.perf_counter() - run_start)}"
                    )
                else:
                    cat_fail += 1
                    total_fail += 1
                    logging.info(
                        f"  [{total_ok + total_fail}/{global_total}] FAILED {url} ({fail_reason}) "
                        f"| uptime {fmt_duration(time.perf_counter() - run_start)}"
                    )
                    failures.append(
                        {
                            "category": category,
                            "url": url,
                            "code": product.get("code", ""),
                            "name": product.get("name", ""),
                            "reason": fail_reason,
                            "failed_at": now_rome().isoformat(timespec="seconds"),
                        }
                    )
                    write_json(failures_path, failures)
                    breaker_result = _check_breaker(failures, cfg)
                    if breaker_result:
                        breaker_action, breaker_message = breaker_result
                        logging.warning(f"Circuit breaker tripped: {breaker_message}")

                write_json(
                    summary_path,
                    {
                        "status": "in_progress",
                        "started_at": started_at_str,
                        "total_ok": total_ok,
                        "total_failed": total_fail,
                        "categories": {
                            **cat_stats,
                            category: {"ok": prior_ok + cat_ok, "failed": prior_fail + cat_fail},
                        },
                    },
                )

                if breaker_action:
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    break

            cat_stats[category] = {"ok": prior_ok + cat_ok, "failed": prior_fail + cat_fail}
            logging.info(
                f"{category}: {cat_ok} ok, {cat_fail} failed | {fmt_duration(time.perf_counter() - cat_start)}"
            )

            if breaker_action == "abort":
                ended_at = now_rome().isoformat(timespec="seconds")
                write_json(
                    summary_path,
                    {
                        "status": "circuit_broken",
                        "started_at": started_at_str,
                        "ended_at": ended_at,
                        "duration": fmt_duration(time.perf_counter() - run_start),
                        "total_ok": total_ok,
                        "total_failed": total_fail,
                        "categories": cat_stats,
                    },
                )
                logging.error(f"Circuit breaker aborted the run → {out_folder}. Resume later with --resume.")
                return out_folder

            if breaker_action == "pause":
                logging.warning(f"Circuit breaker pausing for {cfg.breaker_pause_minutes} minutes...")
                await asyncio.sleep(cfg.breaker_pause_minutes * 60)
                logging.info("Circuit breaker pause finished, resuming.")

    ended_at = now_rome().isoformat(timespec="seconds")
    summary = {
        "status": "complete",
        "started_at": started_at_str,
        "ended_at": ended_at,
        "duration": fmt_duration(time.perf_counter() - run_start),
        "total_ok": total_ok,
        "total_failed": total_fail,
        "categories": cat_stats,
    }
    write_json(summary_path, summary)
    logging.info(
        f"Stage 2 complete → {out_folder} | "
        f"{total_ok} ok, {total_fail} failed | {fmt_duration(time.perf_counter() - run_start)}"
    )
    return out_folder
