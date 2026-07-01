Scraping pipeline for extracting product data and marketing claims from Italian supermarket websites.

## Usage

### Conad

**Stage 1 — collect product links across all catalogue pages:**

```bash
python -m conad_main --stage 1
```

**Limit to N pages (useful for testing):**

```bash
python conad_main --stage 1 --pages 3
```

| Argument | Required | Description |
|---|---|---|
| `--stage` | yes | `1` = link collection, `2` = raw data scraping |
| `--pages` | no | Max pages to crawl (default: all pages) |

### Output

Stage 1 writes one JSON file per category under:

```
link_collection/conad/DD.MM_HH/
  frutta-e-verdura.json
  formaggi.json
  ...
```

Each file contains a list of product objects with 14 fields: `code`, `name`, `brand`, `category_l1`, `category_l2`, `category_l3`, `base_price`, `unit_of_measure`, `min_weight`, `net_quantity_um`, `marketing_badge`, `badge_label`, `image_url`, `product_url`.

Files are written incrementally after every page — partial data is preserved if the run is interrupted.

## Project structure

```
src/
  adapters/    ← one file per site (SiteConfig + parsing logic)
  stages/      ← pipeline stages (stage 1: link_collector.py, stage 2: in progress...)
  utils/       ← shared helpers (browser, storage, logger, parser)
conad_main.py  ← entry point for Conad
```

## Legacy

The original exploration notebooks are preserved in `legacy/`:

- `legacy/custom_crawler_conad.ipynb` — early prototype for Conad category scraping
- `legacy/lavazza_example.ipynb` — example of extracting claims from a brand product page
