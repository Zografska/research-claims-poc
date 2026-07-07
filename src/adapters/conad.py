import json

from bs4 import BeautifulSoup

from .base import SiteConfig


def _get_conad_total_pages(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.select("div.component-Pagination a[data-page]")
    if not pages:
        return 1
    return max(int(p["data-page"]) for p in pages)


def _parse_conad_cards(html: str, cfg: SiteConfig) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for card in soup.select(cfg.product_card_selector):
        raw = card.get("data-product", "{}")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if not data.get("nome"):
            continue

        badge_el = card.select_one(cfg.badge_selector)
        badge_label = badge_el.get_text(strip=True) if badge_el else None

        link_tag = card.select_one("a.product")
        href = link_tag["href"] if link_tag and link_tag.get("href") else ""
        product_url = cfg.base_url + href if href.startswith("/") else href

        increment = data.get("increment") if isinstance(data.get("increment"), dict) else {}

        products.append(
            {
                "code": data.get("code", ""),
                "name": data.get("nome", ""),
                "brand": data.get("marchio", ""),
                "category_l1": data.get("categoriaPrimoLivello", ""),
                "category_l2": data.get("categoriaSecondoLivello", ""),
                "category_l3": data.get("categoriaTerzoLivello", ""),
                "base_price": data.get("basePrice", 0.0),
                "unit_of_measure": increment.get("unitOfMeasure"),
                "min_weight": increment.get("minWeight"),
                "net_quantity_um": data.get("netQuantityUm", ""),
                "marketing_badge": data.get("marketingCategoryBadge"),
                "badge_label": badge_label,
                "image_url": data.get("defaultImgSrc", ""),
                "product_url": product_url,
            }
        )

    return products


def _parse_conad_product_page(html: str, cfg: SiteConfig) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")

    main = soup.find("main", attrs={"data-product": True})
    if not main:
        return None
    try:
        ean = json.loads(main["data-product"]).get("ean")
    except (json.JSONDecodeError, KeyError):
        return None

    result = {"ean": ean}

    for title_el in soup.select("div.uk-accordion-title"):
        section_key = title_el.get_text(strip=True).lower().replace(" ", "_")
        content = title_el.find_next_sibling("div", class_="uk-accordion-content")
        if not content:
            continue

        wysiwyg = content.select_one("div.wysiwyg_editor")
        if not wysiwyg:
            result[section_key] = content.get_text(" ", strip=True)
            continue

        sub_sections = {}
        current_key = None
        for child in wysiwyg.children:
            if not hasattr(child, "name") or child.name is None:
                continue

            if child.name == "p":
                b = child.find("b")
                if b and b.get_text(strip=True) == child.get_text(strip=True):
                    current_key = b.get_text(strip=True).lower().replace(" ", "_")
                    continue

            if current_key is None:
                continue

            text = child.get_text(" ", strip=True)
            if not text:
                images = [child] if child.name == "img" else child.find_all("img")
                text = " ".join(img.get("alt") or img.get("title") or "" for img in images).strip()

            if text:
                sub_sections[current_key] = (sub_sections.get(current_key, "") + " " + text).strip()

        result[section_key] = sub_sections if sub_sections else content.get_text(" ", strip=True)

    return result


CONAD = SiteConfig(
    name="conad",
    base_url="https://spesaonline.conad.it",
    catalogue_url="https://spesaonline.conad.it/tutti-i-prodotti",
    category_param="cat_lev1",
    product_card_selector="div[data-product]",
    badge_selector=".badge-territorio .text",
    detail_description_selector="div.caratteristiche, div.product-other-info",
    detail_data_attr="data-product",
    cookie_js="""
(async () => {
    const btn = document.getElementById('onetrust-accept-btn-handler');
    if (btn) { btn.click(); await new Promise(r => setTimeout(r, 2000)); }
})();
""",
    page_timeout=30000,
    inter_request_delay=(2.0, 5.0),
    extra_headers={
        "Accept-Language": "it-IT,it;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    },
    page_param="page",
    first_page=1,
    session_id="conad_catalogue",
    raw_fetch_mode="browser",
    concurrency=1,
    next_page_js="""
(async () => {
    const btn = document.querySelector('a[aria-label="Pagina Successiva"]');
    if (btn) { btn.click(); await new Promise(r => setTimeout(r, 3000)); }
})();
""",
    parse_cards=_parse_conad_cards,
    parse_product_page=_parse_conad_product_page,
    get_total_pages=_get_conad_total_pages,
)
