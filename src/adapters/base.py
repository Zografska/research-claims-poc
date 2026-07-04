from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class SiteConfig:
    name: str                               # e.g. "conad"
    base_url: str                           # e.g. "https://spesaonline.conad.it"

    # Stage 1 — where to find products
    catalogue_url: str                      # the all-products page
    category_param: str                     # query param name, e.g. "cat_lev1"
    product_card_selector: str              # CSS for product cards, e.g. "div[data-product]"
    badge_selector: str                     # CSS for badge text, e.g. ".badge-territorio .text"

    # Stage 2 — what to extract on each product page
    detail_description_selector: str        # CSS for description block, e.g. "div.caratteristiche"
    detail_data_attr: str                   # HTML attribute holding the JSON blob, e.g. "data-product"

    # Browser behaviour
    cookie_js: Optional[str] = None         # JS to click away the cookie banner
    page_timeout: int = 30000               # milliseconds before crawl4ai gives up on a page
    inter_request_delay: tuple = (2.0, 5.0) # random pause range between requests
    extra_headers: dict = field(default_factory=dict)  # User-Agent, Accept-Language, etc.

    # Pagination
    page_param: Optional[str] = "page"     # query param for page number
    first_page: int = 1                    # page number the site starts at
    session_id: Optional[str] = None       # browser session ID for tab reuse across pages

    # Site-specific logic (fat adapter pattern)
    next_page_js: str = ""                  # JS to navigate to next page; empty if URL-based
    parse_cards: Optional[Callable] = None         # fn(html, cfg) -> list[dict]; defined in each adapter
    parse_product_page: Optional[Callable] = None  # fn(html, cfg) -> dict; defined in each adapter
    get_total_pages: Optional[Callable] = None     # fn(html) -> int; defined in each adapter

    # Fetch strategy — "browser" (default, crawl4ai) or "http" (plain httpx, no browser)
    fetch_mode: str = "browser"
    concurrency: int = 1                    # max simultaneous in-flight requests (Semaphore size)

    # HTTP-mode pagination (offset-based, multi-category) — used when fetch_mode == "http"
    page_size: int = 25                             # items per request, e.g. "sz" param
    bootstrap_url: Optional[str] = None              # page fetched once to discover categories
    discover_categories: Optional[Callable] = None   # fn(html) -> list[str] of category ids
    build_listing_url: Optional[Callable] = None     # fn(cfg, category_id, start) -> str
    get_product_count: Optional[Callable] = None     # fn(html) -> int; total items in a category
