import asyncio
import logging
import random

import httpx

from src.adapters.base import SiteConfig


def make_http_client(cfg: SiteConfig) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=cfg.extra_headers,
        timeout=cfg.page_timeout / 1000,
        follow_redirects=True,
    )


def _parse_retry_after(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None  # HTTP-date form not handled; falls back to the default wait


async def fetch_html(
    client: httpx.AsyncClient,
    url: str,
    pause: asyncio.Event,
    max_retries: int = 3,
) -> tuple[str | None, str | None]:
    delay_ranges = [(3, 6), (8, 12)]
    last_reason = None
    for attempt in range(max_retries):
        await pause.wait()  # blocks here while another request is handling a 429/403
        try:
            r = await client.get(url)
            if r.status_code == 200:
                return r.text, None

            if r.status_code in (429, 403):
                last_reason = "rate_limited" if r.status_code == 429 else "forbidden"
                wait_s = _parse_retry_after(r.headers.get("Retry-After")) or 5
                logging.warning(
                    f"GET {url} -> {r.status_code}, pausing ALL requests for {wait_s}s "
                    f"(attempt {attempt + 1}, Retry-After={r.headers.get('Retry-After')})"
                )
                if pause.is_set():  # avoid stacking redundant pauses from concurrent 429s/403s
                    pause.clear()
                    await asyncio.sleep(wait_s)
                    pause.set()
                continue

            last_reason = f"http_{r.status_code}"
            logging.warning(f"GET {url} -> {r.status_code}, attempt {attempt + 1}")
        except Exception as e:
            last_reason = type(e).__name__
            logging.warning(f"GET {url} failed: {e}, attempt {attempt + 1}")

        if attempt < max_retries - 1:
            await asyncio.sleep(random.uniform(*delay_ranges[attempt]))

    logging.error(f"All retries failed for {url}")
    return None, last_reason
