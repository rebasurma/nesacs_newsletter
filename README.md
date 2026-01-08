# nesacs_newsletter
NESACS Nucleus Newsletter
# NESACS Nucleus Article Card Index

**Indexes articles from NESACS "The Nucleus" newsletter ([archive](https://www.nesacs.org/the-nucleus/)) for public search and discovery as concise data cards.**

## What It Does

- Discovers all newsletter issue PDFs from the NESACS archive.
- Downloads each PDF _temporarily_ (never committed).
- Extracts and splits into individual articles using headings and heuristics.
- For each article, creates a public card (title, bullet-point summary, tags, issue info, PDF source link).
- Outputs data as both JSON and Markdown cards, structured by year and issue.
- Generates a `manifest.json` listing all indexed issues and article counts.

## Data Locations

- `data/cards_json/<year>/<issue>/<slug>.json`
- `data/cards_md/<year>/<issue>/<slug>.md`
- `data/manifest.json`

## Usage

### Locally

**Requires:** Python 3.11+, Linux/macOS recommended

1. **Install dependencies**  
   ```
   pip install -r requirements.txt
   ```

2. **Run the pipeline:**
   ```
   python scripts/scrape_archive.py
   python scripts/download_temp_pdfs.py
   python scripts/extract_and_split.py
   python scripts/build_cards.py
   ```

3. **Cleanup:**  
   Temporary downloaded PDFs and extracted text are in `tmp_pdfs/` and `tmp_articles_json/` and are **not committed**. Remove them after running:
   ```
   rm -rf tmp_pdfs/ tmp_articles_json/
   ```

### On GitHub Actions

- The workflow `.github/workflows/build_cards.yml` runs the entire pipeline.
- Runs **monthly** and on **manual dispatch**.
- Commits and pushes only data article cards (`data/cards_json/`, `data/cards_md/`) and the manifest.

## Safety & Quality

- No full article texts are stored, only public summaries/titles/tags.
- All output is validated and deduplicated.
- Strict `.gitignore` prevents inclusion of PDFs or large extracts.
- Compliant with GitHub token usage and Action security for public repos.

---

_This repository and index are unofficial and not affiliated with NESACS. All content is indexed for public, non-commercial search. For corrections, open a GitHub issue._
ew, and required disclaimers.
