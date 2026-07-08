from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class SiteConfig:
    name: str
    base_url: str

    catalogue_url: str
    category_param: str
    product_card_selector: str
    badge_selector: str

    detail_description_selector: str
    detail_data_attr: str

    cookie_js: Optional[str] = None
    page_timeout: int = 30000
    inter_request_delay: tuple = (2.0, 5.0)
    extra_headers: dict = field(default_factory=dict)

    page_param: Optional[str] = "page"
    first_page: int = 1
    session_id: Optional[str] = None

    next_page_js: str = ""
    parse_cards: Optional[Callable] = None
    parse_product_page: Optional[Callable] = None
    get_total_pages: Optional[Callable] = None

    fetch_mode: str = "browser"
    raw_fetch_mode: Optional[str] = None
    concurrency: int = 1

    page_size: int = 25
    bootstrap_url: Optional[str] = None
    discover_categories: Optional[Callable] = None
    build_listing_url: Optional[Callable] = None
    get_product_count: Optional[Callable] = None
    group_key: Optional[Callable] = None

    breaker_rate_limited_threshold: int = 3
    breaker_window_minutes: int = 10
    breaker_pause_minutes: int = 15
