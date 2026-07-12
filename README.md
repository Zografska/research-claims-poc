Scraping pipeline for extracting product data and marketing claims from Italian supermarket websites.

## Usage

Every site follows the same two-stage pattern: Stage 1 collects product links per category, Stage 2 scrapes full product data (and images) using those links.

```bash
python conad_main.py                       # both stages
python conad_main.py --stage 1             # Stage 1 only
python conad_main.py --stage 2             # Stage 2 only
python conad_main.py --stage 1 --pages 3   # capped, useful for testing
python conad_main.py --stage 2 --products 5
```

Same commands and flags for every site, just swap the entry point: `carrefour_main.py`, `eurospin_main.py`, `coop_main.py`, `naturasi_main.py`, `conad_main.py`.

| Argument | Short | Default | Description |
|---|---|---|---|
| `--stage` | `-s` | both | `1` = link collection, `2` = raw data scraping, `1 2` = both explicitly |
| `--pages` | `-p` | all | Max pages to crawl in Stage 1 (per department/category for Carrefour, Eurospin, Coop, NaturaSi; global for Conad) |
| `--links` | `-l` | most recent run | Path to a specific `link_collection` folder (Stage 2) |
| `--products` | `-n` | all | Global fallback cap per category when not set in `--products-config` (Stage 2) |
| `--products-config` | `-pc` | `config/{site}_sampling.json` | Per-category sampling config (Stage 2) |
| `--seed` | `-S` | `42` | Random seed for reproducible product sampling (Stage 2) |
| `--max` | `-m` | off | Ignore all limits and scrape every product (Stage 2) |
| `--fetch-mode` | `-f` | adapter config | Override Stage 2's fetch engine: `http` or `browser` |
| `--concurrency` | `-c` | adapter config | Override Stage 2's concurrency (max simultaneous requests) |
| `--resume` | `-r` | start fresh | Resume Stage 2 into an existing `raw_data` run, given as compact `DDMMHH` (e.g. `060711` for `06.07_11`) |
| `--breaker-rate-limited-threshold` | `-brt` | adapter config | How many `rate_limited` failures within the window trip the circuit breaker |
| `--breaker-window-minutes` | `-bw` | adapter config | Rolling window (minutes) used to count `rate_limited` failures |
| `--breaker-pause-minutes` | `-bp` | adapter config | How long the breaker pauses before resuming after a `rate_limited` trip |

Conad's Stage 1 always uses a real browser (a cookie-consent banner and pagination require it); Stage 2 can use either engine. Carrefour, Eurospin, Coop, and NaturaSi run entirely over HTTP/JSON APIs, no browser needed for either stage.

Stage 2 includes a circuit breaker that pauses or aborts a run automatically when it detects signs of anti-bot blocking, see the `--breaker-*` flags above.

## How each site works

**Conad** renders its catalogue page with a real browser (crawl4ai/Playwright), since a cookie-consent banner and JS-driven pagination block a plain HTTP fetch. Product cards embed a `data-product` JSON blob parsed directly out of the HTML. Product detail pages use an accordion UI, flattened into nested sections per accordion group.

**Carrefour** is HTTP-only, backed by a Salesforce Commerce Cloud (SFCC) storefront. Departments are discovered by scraping the nav menu off a bootstrap page, then listing pages are fetched through SFCC's `Search-UpdateGrid` endpoint. Product detail pages embed a `data-option-product` JSON attribute with the claims fields used downstream.

**Eurospin, Coop, and NaturaSi** all run on the same `ebsn` JSON API platform. Categories are discovered from a sitemap, filtered to leaf-only slugs, resolved to numeric category IDs via an API call, then probed against the product-listing endpoint to drop empty categories automatically. Coop's claims arrive as raw HTML fragments rather than structured JSON, parsed dynamically by detecting the shape of each fragment. NaturaSi additionally requires a `store_id` param on every request and fetches product detail by slug rather than by numeric ID.

## Output

**Stage 1** writes one JSON file per category/department under `link_collection/{site}/DD.MM_HH/`, containing lightweight product stubs (code, name, brand, category path, price, image URL, product URL).

**Stage 2** reads that output and writes one JSON file per category under `raw_data/{site}/DD.MM_HH/`, plus a subfolder of downloaded product images per category, plus `run_summary.json` and `run_failures.json`:

```
raw_data/{site}/DD.MM_HH/
  some-category.json
  some-category/
    8001234567890.jpg
    ...
  run_summary.json
  run_failures.json
```

Each product record includes `product_id` (always present, keys the record and its image), `ean` (null if the site has no barcode for that product), `scraped_at`, and all the claims/nutrition/ingredients fields the site exposes, in whatever shape that site's adapter parses them into. `run_failures.json` lists every failed product with its category, URL, and failure reason. `run_summary.json` tracks `status` (`in_progress`, `complete`, or `circuit_broken`), start/end time, duration, and per-category counts.

Both stages write incrementally, so partial data survives an interrupted run. Re-running within the same hour resumes into the same output folder automatically; use `--resume` to continue a specific folder from a different hour.

## Project structure

```
src/
  adapters/    one file per site (SiteConfig + parsing logic)
  stages/      pipeline stages (link_collector.py, raw_scraper.py)
  utils/       shared helpers (browser, http_client, storage, logger, parser)
conad_main.py, carrefour_main.py, eurospin_main.py, coop_main.py, naturasi_main.py
  entry points, one per site
```

## Notifications

Both stages can optionally post progress to a Discord webhook: run start, periodic checkpoints, completion, and failures/circuit-breaker events. Copy `.env.example` to `.env` and set `DISCORD_WEBHOOK_URL`; if it's unset, notifications are silently skipped.

## Running on INDACO (SLURM)

`slurm/*.sbatch` has one job script per site for running the pipeline on INDACO's cluster:

```bash
sbatch slurm/coop.sbatch
squeue -u $USER
```

`submit_slurm_jobs.sh` submits all five in one go:

```bash
./submit_slurm_jobs.sh
```

Each job's `--output`/`--error` log is renamed to the project's own `DD.MM_HH` timestamp convention (e.g. `coop-11.07_23.out`) once it starts running.

Each site's job also syncs its scraped images to OneDrive once it finishes, via `sync_onedrive.sh` (JSON files stay local, only the per-category image folders are moved). To sync manually instead of waiting for a scheduled scrape:

```bash
sbatch slurm/sync.sbatch coop   # sync just one site
sbatch slurm/sync.sbatch        # sync all five sites, one after another
```

A weekly cron job on INDACO submits all five scraping jobs automatically.

Build the venv on INDACO with `/usr/bin/python3.11` (present on both the login node and compute nodes) and `requirements-indaco.txt`:

```bash
/usr/bin/python3.11 -m venv .venv
.venv/bin/pip install -r requirements-indaco.txt
.venv/bin/python -m playwright install chromium
```

There are two requirements files because INDACO's compute nodes only have Python up to 3.11 available, while `requirements.txt` (used everywhere else) is frozen from a 3.12+ environment. `requirements-indaco.txt` is identical except for two packages pinned to versions compatible with 3.11.

## Development

This repo uses [pre-commit](https://pre-commit.com) for linting/formatting (Ruff) and basic file hygiene checks.

```bash
pip install -r requirements.txt
pre-commit install
```

After that, checks run automatically on every `git commit`. Run `pre-commit run --all-files` to check the whole repo at once.

## Legacy

The original exploration notebooks are preserved in `legacy/`:

- `legacy/custom_crawler_conad.ipynb`, early prototype for Conad category scraping
- `legacy/lavazza_example.ipynb`, example of extracting claims from a brand product page
