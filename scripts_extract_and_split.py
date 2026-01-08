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
        month = m.group(1)
        year = int(m.group(2))
    else:
        y = re.search(r'(\d{4})', issue_label)
        if y:
            year = int(y.group(1))
    return year, month

def split_articles(pages):
    """Given a list of page texts from one issue, split into articles."""
    alltext = "\n".join(pages)
    article_delims = [
        r"(^|\n)([A-Z][A-Za-z0-9 -]*)(\n+By [A-Z][a-zA-Z .]*)?\n",  # likely article title, optional "By" line
        r"(^|\n)([A-Z][A-Za-z0-9 -]*)(\n+by [A-Z][a-zA-Z .]*)?\n",
        r"(^|\n)News\s+briefs(\s*\n|:)",  # catch News Briefs
    ]
    # Use a less greedy split: look for title-in-allcaps + "By" line
    pattern = r"(?:^|\n)([A-Z][A-Z0-9 ,\-\(\)'&]+)(\n+by [A-Z][a-zA-Z .]*)?\n"
    matches = list(re.finditer(pattern, alltext, flags=re.MULTILINE))
    article_spans = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(alltext)
        article_spans.append((start, end))
    articles = []
    for idx, (a, b) in enumerate(article_spans):
        body = alltext[a:b]
        # Remove excessive whitespace
        body = re.sub(r'\n{3,}', '\n\n', body.strip())
        if len(body) > 200:
            articles.append(body)
    # If splitting failed, fallback
    if not articles:
        articles = [t.strip() for t in re.split(r"\n{2,}", alltext) if len(t.strip()) > 250]
    # Deduplicate by content hash
    seen = set()
    deduped = []
    for art in articles:
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
            # Title is first ~line, fallback to "Untitled Article"
            t_match = re.match(r"^\s*([^\n]{8,80})\n+", art)
            title = t_match.group(1).strip() if t_match else None
            title = title if title and re.search(r"\w", title) else f"Untitled Article {i+1}"
            # Compose
            articles_struct.append({
                "title": title,
                "body": art,
                "issue_label": issue_label,
                "year": year,
                "month": month,
                "source_url": pdf_url,
                "idx": i
            })
        # Write out per-issue as JSON
        slug_issue = slugify(issue_label, maxlen=32)
        outpath = os.path.join(OUTPUT_JSON_DIR, f"{year or 'unknown'}_{slug_issue}.json")
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(articles_struct, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(articles_struct)} articles for {issue_label}")
    print("Extraction and splitting complete.")

if __name__ == "__main__":
    main()