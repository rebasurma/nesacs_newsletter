import os
import sys
import re
import json
import pdfplumber
import hashlib

TMP_PDF_DIR = "tmp_pdfs"
ISSUE_LIST_JSON = "data/issues.json"
OUTPUT_JSON_DIR = "tmp_articles_json"
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

def slugify(text, maxlen=48):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    slug = text.strip("-")
    if len(slug) > maxlen:
        slug = slug[:maxlen].strip("-")
    return slug or "untitled"

def parse_issue_title(issue_label):
    year, month = None, None
    m = re.search(r'([A-Z][a-z]+)\s*(\d{4})', issue_label)
    if m:
        month, year = m.group(1), int(m.group(2))
    else:
        y = re.search(r'(\d{4})', issue_label)
        if y:
            year = int(y.group(1))
    return year, month

def split_articles(pages):
    # Join all page text
    alltext = "\n".join([pg if pg else "" for pg in pages])
    # Use likely title = ALLCAPS or Title Case line (optionally followed by By ...); start of block
    # Require >100 char for a section to be considered article (to avoid ads/listings)
    # Pattern: Title (by Author)? \n\n (byline is optional)
    blocks = []
    matches = list(re.finditer(r'(?<=\n|^)([A-Z][A-Z0-9 ,\-()&\':]{10,80}|.{18,80}\nby [A-Z][^\n]{1,50})\n', alltext, flags=re.MULTILINE))
    positions = [m.start() for m in matches] + [len(alltext)]
    for i in range(len(positions)-1):
        chunk = alltext[positions[i]:positions[i+1]]
        if len(chunk.strip()) > 180:  # threshold-ish
            blocks.append(chunk.strip())
    # If none found, fallback on double-newline splits
    if not blocks:
        blocks = [t.strip() for t in re.split(r"\n{2,}", alltext) if len(t.strip()) > 200]
    # Dedup by content hash
    seen = set()
    deduped = []
    for art in blocks:
        h = hashlib.sha256(art.encode("utf-8")).hexdigest()
        if h not in seen:
            deduped.append(art)
            seen.add(h)
    return deduped

def main():
    with open(ISSUE_LIST_JSON, "r", encoding="utf-8") as f:
        issues = json.load(f)
    for idx, issue in enumerate(issues):
        pdf_url = issue["pdf_url"]
        issue_label = issue["issue_label"]
        year = issue["year"] or parse_issue_title(issue_label)[0]
        month = issue["month"] or parse_issue_title(issue_label)[1]
        pdf_filename = os.path.basename(pdf_url)
        pdf_path = os.path.join(TMP_PDF_DIR, pdf_filename)
        if not os.path.exists(pdf_path):
            print(f"[SKIP] Missing PDF: '{pdf_path}'")
            continue
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_texts = [p.extract_text() or "" for p in pdf.pages]
        except Exception as e:
            print(f"Failed to open {pdf_path}: {e}", file=sys.stderr)
            continue
        articles = split_articles(page_texts)
        articles_struct = []
        for i, art in enumerate(articles):
            first_lines = art.split('\n', 4)
            # Try to infer a title: first non-empty line <80 chars
            title_candidate = next((ln.strip() for ln in first_lines if 8 < len(ln.strip()) < 80), None)
            title = title_candidate if title_candidate and re.search(r'\w', title_candidate) else f"Untitled Article {i+1}"
            articles_struct.append({
                "title": title,
                "body": art,
                "issue_label": issue_label,
                "year": year,
                "month": month,
                "source_url": pdf_url,
                "idx": i
            })
        slug_issue = slugify(issue_label, maxlen=32)
        outpath = os.path.join(OUTPUT_JSON_DIR, f"{year or 'unknown'}_{slug_issue}.json")
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(articles_struct, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(articles_struct)} articles for {issue_label}")
    print("Extraction and splitting complete.")

if __name__ == "__main__":
    main()