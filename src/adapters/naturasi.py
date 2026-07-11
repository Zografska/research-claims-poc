import json
import logging
import re
from collections import Counter

import httpx
from bs4 import BeautifulSoup

from .base import SiteConfig

STORE_ID = "5"


def _discover_naturasi_categories(xml: str, cfg: SiteConfig) -> list[str]:
    slugs = []
    for loc in re.findall(r"<loc>(.*?)</loc>", xml):
        slug = loc.replace(cfg.base_url, "").strip("/")
        if slug:
            slugs.append(slug)

    slug_set = set(slugs)
    leaf_slugs = [s for s in slugs if not any(other.startswith(s + "/") for other in slug_set)]

    category_ids = []
    with httpx.Client(headers=cfg.extra_headers, timeout=cfg.page_timeout / 1000) as client:
        for slug in leaf_slugs:
            try:
                r = client.get(
                    f"{cfg.base_url}/ebsn/api/category",
                    params={"slug": slug, "filtered": "true", "store_id": STORE_ID},
                )
                cat_id = r.json().get("data", {}).get("category", {}).get("categoryId")
                if not cat_id:
                    continue

                r2 = client.get(
                    f"{cfg.base_url}/ebsn/api/products",
                    params={"category_id": cat_id, "store_id": STORE_ID, "page": 1, "page_size": 1},
                )
                total = r2.json().get("data", {}).get("page", {}).get("totItems", 0)
                if total > 0:
                    category_ids.append(str(cat_id))
            except Exception as e:
                logging.warning(f"Failed to resolve category slug {slug}: {e}")

    return category_ids


def _naturasi_group_key(category_id: str, products: list[dict]) -> str:
    if products:
        return products[0].get("category_l1") or category_id
    return category_id


def _build_naturasi_listing_url(cfg: SiteConfig, category_id: str, start: int) -> str:
    page = start // cfg.page_size + 1
    return (
        f"{cfg.base_url}/ebsn/api/products?category_id={category_id}&store_id={STORE_ID}"
        f"&page={page}&page_size={cfg.page_size}"
    )


def _get_naturasi_product_count(html: str) -> int:
    try:
        data = json.loads(html)
    except json.JSONDecodeError:
        return 0
    return data.get("data", {}).get("page", {}).get("totItems", 0)


def _parse_naturasi_cards(html: str, cfg: SiteConfig) -> list[dict]:
    try:
        data = json.loads(html)
    except json.JSONDecodeError:
        return []

    raw_products = data.get("data", {}).get("products", [])
    if not raw_products:
        return []

    category_counts = Counter(p.get("categoryId") for p in raw_products)
    expected_category_id = category_counts.most_common(1)[0][0]

    products = []
    for p in raw_products:
        if p.get("categoryId") != expected_category_id:
            continue
        product_id = p.get("productId")
        slug = p.get("slug")
        if not product_id or not slug:
            continue

        crumb_names = [c.get("name", "") for c in (p.get("breadCrumbs") or [])]
        vendor = p.get("vendor") or {}

        thumb_url = p.get("mediaURL", "")
        image_url = thumb_url.replace("/main/thumb/", "/main/large/") if thumb_url else ""

        products.append(
            {
                "product_id": str(product_id),
                "ean": str(p.get("barcode")) if p.get("barcode") else None,
                "name": p.get("name", ""),
                "brand": vendor.get("name", ""),
                "category_l1": crumb_names[0] if len(crumb_names) > 0 else "",
                "category_l2": crumb_names[1] if len(crumb_names) > 1 else "",
                "category_l3": crumb_names[2] if len(crumb_names) > 2 else "",
                "base_price": p.get("price", 0.0),
                "image_url": image_url,
                "product_url": f"{cfg.base_url}/ebsn/api/products?slug={slug}&store_id={STORE_ID}",
            }
        )

    return products


def _flatten_nutrition_table(rows: list) -> dict:
    flattened = {}
    for row in rows:
        if not isinstance(row, dict) or "codice" not in row:
            continue
        codice = row.get("codice")
        labels = row.get("labels") or {}
        entry = {"value": row.get("peso"), "unit": row.get("unita")}
        label = labels.get("it_IT")
        if label:
            entry["label"] = label
        flattened[codice] = entry
    return flattened


def _looks_like_nutrition_table(parsed: list) -> bool:
    return bool(parsed) and all(isinstance(item, dict) and "codice" in item for item in parsed)


def _extract_naturasi_metadata_fields(section: dict, result: dict) -> None:
    for key, value in section.items():
        if not value:
            continue
        field_key = key.lower()

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = None

            if isinstance(parsed, list) and _looks_like_nutrition_table(parsed):
                flattened = _flatten_nutrition_table(parsed)
                if flattened:
                    result[field_key] = flattened
                continue

            if isinstance(parsed, list):
                result[field_key] = [item.get("label", item) if isinstance(item, dict) else item for item in parsed]
                continue

            text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
            if text:
                result[field_key] = text
        else:
            result[field_key] = value


def _parse_naturasi_product_page(html: str, cfg: SiteConfig) -> dict | None:
    try:
        data = json.loads(html)
    except json.JSONDecodeError:
        return None

    d = data.get("data", {})
    if not d.get("productId"):
        return None

    result = {"ean": str(d.get("barcode")) if d.get("barcode") else None}

    product_classes = [c.get("name") for c in (d.get("productClasses") or []) if c.get("name")]
    if product_classes:
        result["certifications"] = product_classes

    meta_data = d.get("metaData", {})
    for section_name, section in meta_data.items():
        if not isinstance(section, dict):
            continue
        _extract_naturasi_metadata_fields(section, result)

    return result


NATURASI = SiteConfig(
    name="naturasi",
    base_url="https://www.naturasi.it",
    catalogue_url="",
    category_param="category_id",
    product_card_selector="",
    badge_selector="",
    detail_description_selector="",
    detail_data_attr="",
    fetch_mode="http",
    concurrency=10,
    page_size=5000,
    bootstrap_url="https://www.naturasi.it/category.xml",
    inter_request_delay=(1.0, 3.0),
    extra_headers={
        "Accept-Language": "it-IT,it;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    },
    discover_categories=_discover_naturasi_categories,
    build_listing_url=_build_naturasi_listing_url,
    get_product_count=_get_naturasi_product_count,
    group_key=_naturasi_group_key,
    parse_cards=_parse_naturasi_cards,
    parse_product_page=_parse_naturasi_product_page,
)
