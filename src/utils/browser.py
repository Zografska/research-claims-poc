from crawl4ai import BrowserConfig, CrawlerRunConfig

from src.adapters.base import SiteConfig


def make_browser_config(cfg: SiteConfig) -> BrowserConfig:
    return BrowserConfig(
        headless=True,
        use_managed_browser=True,
        extra_args=["--disable-blink-features=AutomationControlled"],
        headers=cfg.extra_headers,
    )


def make_run_config(
    cfg: SiteConfig,
    js_code: str | None = None,
    wait_for: str | None = None,
) -> CrawlerRunConfig:
    return CrawlerRunConfig(
        js_code=js_code or "",
        page_timeout=cfg.page_timeout,
        wait_until="networkidle",
        wait_for=wait_for,
    )
