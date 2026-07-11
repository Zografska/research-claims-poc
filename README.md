Scraping pipeline for extracting product data and marketing claims from Italian supermarket websites.

## Usage

### Conad

**Run both stages in sequence:**

```bash
python conad_main.py
```

**Run a specific stage:**

```bash
python conad_main.py --stage 1
python conad_main.py --stage 2
python conad_main.py --stage 1 2
```

**Limit pages or products (useful for testing):**

```bash
python conad_main.py --stage 1 --pages 3
python conad_main.py --stage 2 --products 5
```

| Argument | Short | Required | Default | Description |
|---|---|---|---|---|
| `--stage` | `-s` | no | both | `1` = link collection, `2` = raw data scraping, `1 2` = both explicitly |
| `--pages` | `-p` | no | all | Max catalogue pages to crawl (Stage 1) |
| `--links` | `-l` | no | most recent run | Path to a specific `link_collection` folder (Stage 2) |
| `--products` | `-n` | no | all | Global fallback cap per category when not set in `--products-config` (Stage 2) |
| `--products-config` | `-pc` | no | `config/conad_sampling.json` | Per-category sampling config (Stage 2) |
| `--seed` | `-S` | no | `42` | Random seed for reproducible product sampling (Stage 2) |
| `--max` | `-m` | no | off | Ignore all limits and scrape every product (Stage 2) |
| `--fetch-mode` | `-f` | no | adapter config | Override Stage 2's fetch engine: `http` or `browser` |
| `--concurrency` | `-c` | no | adapter config | Override Stage 2's concurrency (max simultaneous requests) |
| `--resume` | `-r` | no | start fresh | Resume Stage 2 into an existing `raw_data` run, given as compact `DDMMHH` (e.g. `060711` for `06.07_11`) |
| `--breaker-rate-limited-threshold` | `-brt` | no | adapter config | How many `rate_limited` failures within the window trip the circuit breaker |
| `--breaker-window-minutes` | `-bw` | no | adapter config | Rolling window (minutes) used to count `rate_limited` failures |
| `--breaker-pause-minutes` | `-bp` | no | adapter config | How long the breaker pauses before resuming after a `rate_limited` trip |

### Carrefour

Same commands and arguments as Conad, using `carrefour_main.py`:

```bash
python carrefour_main.py
python carrefour_main.py --stage 1 --pages 3
python carrefour_main.py --stage 2 --products 5
```

Two differences from Conad's arguments:

| Argument | Difference |
|---|---|
| `--pages` | Applies **per department** (Carrefour has ~20 independent departments), not as a single global cap |
| `--products-config` | Defaults to `config/carrefour_sampling.json` |

Carrefour fetches over plain HTTP (no browser needed) for both stages, and departments are discovered dynamically from the site's own navigation — no hardcoded category list.

Conad's Stage 1 always uses a real browser. Stage 2 can use either engine — see `--fetch-mode` below, and each adapter's `raw_fetch_mode`/`concurrency`/`breaker_*` fields in `src/adapters/`.

Stage 2 also includes a circuit breaker that pauses or aborts a run automatically when it detects signs of anti-bot blocking — see `--breaker-*` flags below.

### Eurospin, Coop, and NaturaSi

Same commands and arguments as Conad, using `eurospin_main.py`, `coop_main.py`, or `naturasi_main.py`. All three run entirely over the `ebsn` JSON API rather than scraping rendered HTML: categories are discovered from a sitemap, filtered to leaf-only slugs, resolved to numeric category IDs, then probed to drop empty categories (account pages, region pages, etc.) automatically. Like Carrefour, `--pages` applies per category rather than globally.

| Site | Category ID param | Notes |
|---|---|---|
| Eurospin | `parent_category_id` | |
| Coop | `parent_category_id` | No price for anonymous requests, so `base_price` is always `null` |
| NaturaSi | `category_id` | Every request also needs a `store_id` param; product detail is fetched by slug, not by numeric ID |

### Output

**Conad — Stage 1** writes one JSON file per category under:

```
link_collection/conad/DD.MM_HH/
  frutta-e-verdura.json
  formaggi.json
  ...
```

Each file contains a list of product stubs with 14 fields: `code`, `name`, `brand`, `category_l1`, `category_l2`, `category_l3`, `base_price`, `unit_of_measure`, `min_weight`, `net_quantity_um`, `marketing_badge`, `badge_label`, `image_url`, `product_url`.

**Conad — Stage 2** reads the Stage 1 output and writes one JSON file per category plus a product image folder:

```
raw_data/conad/DD.MM_HH/
  frutta-e-verdura.json
  frutta-e-verdura/
    8001234567890.jpg
    ...
  run_summary.json
  run_failures.json
```

`run_failures.json` lists every failed product with its category, URL, and reason (`rate_limited`, `forbidden`, `http_<code>`, an exception type, `parse_failed`, or `no_product_id`).

Each product record contains: `product_id`, `ean`, `scraped_at`, `code`, `name`, `url`, and all accordion sections extracted from the product page. `product_id` is always present and keys the record/image; `ean` is `null` when the site has no barcode for that product — it's no longer dropped for that reason alone.

**Carrefour — Stage 1** writes one JSON file per department under `link_collection/carrefour/DD.MM_HH/`: `product_id`, `ean`, `name`, `brand`, `category_l1/l2/l3`, `base_price`, `list_price`, `weight`, `image_url`, `product_url`.

**Carrefour — Stage 2** writes to `raw_data/carrefour/DD.MM_HH/` in the same layout as Conad, plus the site's own claims fields verbatim (`C4_SalesDenomination`, `labeledIngredients`, `nutritionInfo`, `C4_Allergens`, `C4_Origin`, etc.).

**Eurospin, Coop, and NaturaSi — Stage 1** each write one JSON file per category under `link_collection/{site}/DD.MM_HH/`, named after the category as shown on the site rather than its numeric ID.

**Eurospin, Coop, and NaturaSi — Stage 2** write to `raw_data/{site}/DD.MM_HH/` in the same layout. Eurospin and NaturaSi flatten the site's product metadata (description, technical specs, allergens, nutrition, certifications) into plain keys; Coop's claims arrive as raw HTML fragments (tables, lists, plain text) parsed dynamically into the same shape. NaturaSi also adds a `certifications` field for organic/vegan/allergen-free style badges.

`run_summary.json` is written after every product and updated on completion with start time, end time, duration, and per-category counts. `status` is `in_progress` while running, `complete` on a normal finish, or `circuit_broken` if the breaker aborted the run.

Both stages write incrementally — partial data is preserved if the run is interrupted. Re-running within the same hour resumes in the same output folder automatically; use `--resume` to continue a specific folder from a different hour.

## Project structure

```
src/
  adapters/    ← one file per site (SiteConfig + parsing logic)
  stages/      ← pipeline stages (link_collector.py, raw_scraper.py)
  utils/       ← shared helpers (browser, http_client, storage, logger, parser)
conad_main.py      ← entry point for Conad
carrefour_main.py  ← entry point for Carrefour
eurospin_main.py   ← entry point for Eurospin
coop_main.py       ← entry point for Coop
naturasi_main.py   ← entry point for NaturaSi
```

## Notifications

Both stages can optionally post progress to a Discord webhook — run start, periodic checkpoints, completion, and failures/circuit-breaker events. Copy `.env.example` to `.env` and set `DISCORD_WEBHOOK_URL`; if it's unset, notifications are silently skipped.

## Development

This repo uses [pre-commit](https://pre-commit.com) for linting/formatting (Ruff) and basic file hygiene checks.

```bash
pip install -r requirements.txt
pre-commit install
```

After that, checks run automatically on every `git commit`. Run `pre-commit run --all-files` to check the whole repo at once.

## Legacy

The original exploration notebooks are preserved in `legacy/`:

- `legacy/custom_crawler_conad.ipynb` — early prototype for Conad category scraping
- `legacy/lavazza_example.ipynb` — example of extracting claims from a brand product page
