import json
import logging

from bs4 import BeautifulSoup

from .base import SiteConfig


def _discover_carrefour_categories(html: str, cfg: SiteConfig) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.select_one("nav#secondLevelNavigation")
    if not nav:
        return []

    categories = []
    for a in nav.select("a[href]"):
        href = a["href"]
        if not href.startswith("/spesa-online/"):
            continue
        slug = href.strip("/").split("/")[-1]
        if slug:
            categories.append(slug)
    return categories


def _build_carrefour_listing_url(cfg: SiteConfig, category_id: str, start: int) -> str:
    return (
        f"{cfg.base_url}/on/demandware.store/Sites-carrefour-IT-Site/it_IT/Search-UpdateGrid"
        f"?cgid={category_id}&start={start}&sz={cfg.page_size}"
    )


def _get_carrefour_product_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    footer = soup.select_one("div.grid-footer[data-product-count]")
    if not footer:
        return 0
    return int(footer["data-product-count"])


def _parse_carrefour_cards(html: str, cfg: SiteConfig) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for card in soup.select("article.product.tile[data-pid]"):
        raw = card.get("data-product-json", "{}")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        if not data.get("name"):
            continue

        link_tag = card.select_one("a.tile-link-pdp")
        href = link_tag["href"] if link_tag and link_tag.get("href") else ""
        product_url = cfg.base_url + href if href.startswith("/") else href

        img_tag = card.select_one("img.tile-image")
        image_url = ""
        if img_tag:
            # Most tiles lazy-load: real URL is in data-src, src is absent.
            # Only a handful of "above the fold" tiles are eager and use src directly.
            image_url = img_tag.get("data-src") or img_tag.get("src") or ""
        if image_url.startswith("/"):
            image_url = cfg.base_url + image_url

        try:
            breadcrumbs = json.loads(card.get("data-option-product-breadcrumbs", "[]"))
        except json.JSONDecodeError:
            breadcrumbs = []
        if not isinstance(breadcrumbs, list):
            logging.warning(
                f"Product {card.get('data-pid', '?')} has non-list breadcrumbs "
                f"({breadcrumbs!r}) — leaving category_l1/l2/l3 empty"
            )
            breadcrumbs = []
        crumb_ids = [
            c.get("categoryId", "") for c in breadcrumbs[1:]
        ]  # skip root "FOOD"

        products.append(
            {
                "ean": card.get("data-pid", ""),
                "name": data.get("name", ""),
                "brand": data.get("brand", ""),
                "category_l1": crumb_ids[0] if len(crumb_ids) > 0 else "",
                "category_l2": crumb_ids[1] if len(crumb_ids) > 1 else "",
                "category_l3": crumb_ids[2] if len(crumb_ids) > 2 else "",
                "base_price": data.get("price", ""),
                "list_price": data.get("metric19", ""),
                "weight": data.get("dimension52"),
                "image_url": image_url,
                "product_url": product_url,
            }
        )

    return products


def _parse_carrefour_product_page(html: str, cfg: SiteConfig) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")

    node = soup.select_one("[data-option-product]")
    if not node:
        return None
    try:
        data = json.loads(node["data-option-product"])
    except json.JSONDecodeError:
        return None

    ean = data.get("id")
    if not ean:
        return None

    fields = [
        "C4_SalesDenomination",
        "labeledIngredients",
        "nutritionInfo",
        "C4_Allergens",
        "C4_Storage",
        "C4_StorageMethod",
        "C4_StorageAndUseInfo",
        "C4_DurabilityAfterOpening",
        "C4_SafetyWarnings",
        "C4_Origin",
        "C4_Country",
        "C4_RecyclingInfo",
        "C4_RecyclingMoreText",
        "C4_ManufacturesAddress",
        "primaryCategory",
        "primaryCategoryName",
    ]
    return {"ean": ean, **{f: data.get(f) for f in fields}}


CARREFOUR = SiteConfig(
    name="carrefour",
    base_url="https://www.carrefour.it",
    # Stage 1 — listing (unused in http mode, kept for interface parity)
    catalogue_url="",
    category_param="cgid",
    product_card_selector="article.product.tile[data-pid]",
    badge_selector="",
    # Stage 2 — product detail page
    detail_description_selector="",
    detail_data_attr="data-option-product",
    # Fetch strategy
    fetch_mode="http",
    concurrency=25,
    page_size=25,
    bootstrap_url="https://www.carrefour.it/spesa-online/salumi-e-formaggi/",
    inter_request_delay=(1.0, 3.0),
    extra_headers={
        "Accept-Language": "it-IT,it;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    },
    # Site-specific logic
    discover_categories=_discover_carrefour_categories,
    build_listing_url=_build_carrefour_listing_url,
    get_product_count=_get_carrefour_product_count,
    parse_cards=_parse_carrefour_cards,
    parse_product_page=_parse_carrefour_product_page,
)
