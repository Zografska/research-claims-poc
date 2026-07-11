import json
import logging
import re
from collections import Counter

import httpx
from bs4 import BeautifulSoup

from .base import SiteConfig


def _discover_coop_categories(xml: str, cfg: SiteConfig) -> list[str]:
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
                r = client.get(f"{cfg.base_url}/ebsn/api/category", params={"slug": slug, "filtered": "true"})
                cat_id = r.json().get("data", {}).get("category", {}).get("categoryId")
                if not cat_id:
                    continue

                r2 = client.get(
                    f"{cfg.base_url}/ebsn/api/products",
                    params={"parent_category_id": cat_id, "page": 1, "page_size": 1},
                )
                total = r2.json().get("data", {}).get("page", {}).get("totItems", 0)
                if total > 0:
                    category_ids.append(str(cat_id))
            except Exception as e:
                logging.warning(f"Failed to resolve category slug {slug}: {e}")

    return category_ids


def _coop_group_key(category_id: str, products: list[dict]) -> str:
    if products:
        return products[0].get("category_l1") or category_id
    return category_id


def _build_coop_listing_url(cfg: SiteConfig, category_id: str, start: int) -> str:
    page = start // cfg.page_size + 1
    return f"{cfg.base_url}/ebsn/api/products?parent_category_id={category_id}&page={page}&page_size={cfg.page_size}"


def _get_coop_product_count(html: str) -> int:
    try:
        data = json.loads(html)
    except json.JSONDecodeError:
        return 0
    return data.get("data", {}).get("page", {}).get("totItems", 0)


def _parse_coop_cards(html: str, cfg: SiteConfig) -> list[dict]:
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
        if not product_id:
            continue

        crumb_names = [c.get("name", "") for c in (p.get("breadCrumbs") or [])]
        vendor = p.get("vendor") or {}

        thumb_url = p.get("mediaURL", "")
        image_url = thumb_url.replace("/thumb/", "/large/") if thumb_url else ""

        products.append(
            {
                "product_id": str(product_id),
                "ean": str(p.get("barcode")) if p.get("barcode") else None,
                "name": p.get("name", ""),
                "brand": vendor.get("name", ""),
                "category_l1": crumb_names[0] if len(crumb_names) > 0 else "",
                "category_l2": crumb_names[1] if len(crumb_names) > 1 else "",
                "category_l3": crumb_names[2] if len(crumb_names) > 2 else "",
                "base_price": None,
                "image_url": image_url,
                "product_url": f"{cfg.base_url}/ebsn/api/products/{product_id}",
            }
        )

    return products


def _looks_like_html_fragment(value) -> bool:
    return isinstance(value, str) and value.strip().startswith("<")


def _parse_coop_html_table(table) -> dict:
    rows = table.find_all("tr")
    if not rows:
        return {}

    header_cells = rows[0].find_all(["td", "th"])
    headers = [c.get_text(strip=True) for c in header_cells[1:]]

    values, notes = {}, []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        if any(int(c.get("colspan", 1)) > 1 for c in cells):
            note = " ".join(c.get_text(" ", strip=True) for c in cells if c.get_text(strip=True))
            if note:
                notes.append(note)
            continue

        row_label = cells[0].get_text(strip=True)
        if not row_label:
            continue

        vals = [c.get_text(strip=True) for c in cells[1:]]
        if headers and len(headers) == len(vals):
            values[row_label] = {h: v for h, v in zip(headers, vals) if v}
        elif len(vals) == 1:
            values[row_label] = vals[0]
        elif vals:
            values[row_label] = vals

    result = {"values": values}
    if notes:
        result["notes"] = notes
    return result


def _parse_coop_html_list(list_tag) -> dict | list:
    items = list_tag.find_all("li")
    pairs, plain = {}, []

    for li in items:
        spans = li.find_all("span", recursive=False)
        if len(spans) >= 2:
            label = spans[0].get_text(strip=True)
            value = ", ".join(s.get_text(strip=True) for s in spans[1:] if s.get_text(strip=True))
            if label:
                pairs[label] = value
        else:
            text = li.get_text(" ", strip=True)
            if text:
                plain.append(text)

    if pairs and plain:
        logging.warning("Mixed <li> shapes in a Coop metadata list — falling back to plain text list")
        return [li.get_text(" ", strip=True) for li in items if li.get_text(strip=True)]

    if pairs:
        return pairs
    return plain[0] if len(plain) == 1 else plain


def _clean_block_text(node) -> str:
    text = node.get_text()
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _parse_coop_html_value(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")

    table = soup.find("table")
    if table:
        return _parse_coop_html_table(table)

    list_tag = soup.find(["ul", "ol"])
    if list_tag:
        return _parse_coop_html_list(list_tag)

    paragraphs = [text for p in soup.find_all("p") if (text := _clean_block_text(p))]
    if paragraphs:
        return "\n".join(paragraphs) if len(paragraphs) > 1 else paragraphs[0]

    text = soup.get_text(" ", strip=True)
    return text or None


def _extract_coop_metadata_fields(meta_data: dict) -> dict:
    result = {}
    for group in meta_data.values():
        if not isinstance(group, dict):
            continue
        for key, value in group.items():
            if not value:
                continue
            try:
                parsed = _parse_coop_html_value(value) if _looks_like_html_fragment(value) else value
            except Exception as e:
                logging.warning(f"Failed to parse Coop metadata field {key}: {e}")
                continue
            if parsed not in (None, "", [], {}):
                result[key.lower()] = parsed
    return result


def _parse_coop_product_page(html: str, cfg: SiteConfig) -> dict | None:
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

    result.update(_extract_coop_metadata_fields(d.get("metaData", {}) or {}))
    return result


COOP = SiteConfig(
    name="coop",
    base_url="https://www.coopshop.it",
    catalogue_url="",
    category_param="parent_category_id",
    product_card_selector="",
    badge_selector="",
    detail_description_selector="",
    detail_data_attr="",
    fetch_mode="http",
    concurrency=10,
    page_size=5000,
    bootstrap_url="https://www.coopshop.it/sitemap/category.xml",
    inter_request_delay=(1.0, 3.0),
    extra_headers={
        "Accept-Language": "it-IT,it;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    },
    discover_categories=_discover_coop_categories,
    build_listing_url=_build_coop_listing_url,
    get_product_count=_get_coop_product_count,
    group_key=_coop_group_key,
    parse_cards=_parse_coop_cards,
    parse_product_page=_parse_coop_product_page,
)
