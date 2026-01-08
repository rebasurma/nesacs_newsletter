import requests
from bs4 import BeautifulSoup
import re
import json
import sys
import time

ARCHIVE_URL = "https://www.nesacs.org/the-nucleus/"
HEADERS = {
    "User-Agent": "NESACS-Nucleus-Indexer/1.0 (mailto:info@example.com)"
}

def polite_get(url, retries=3, backoff=2):
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp
            else:
                print(f"Error: Got status {resp.status_code} for {url}", file=sys.stderr)
        except Exception as e:
            print(f"Exception requesting {url}: {e}", file=sys.stderr)
        time.sleep(backoff * (i+1))
    return None

def extract_issues(soup):
    """
    Find all issue links + PDF URLs from the Nucleus archive page.
    Returns list of dicts:
      { "issue_label", "year", "month" (optional), "pdf_url" }
    """
    issues = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith(".pdf"):
            issue_label = ""
            year, month = None, None
            text = a.get_text(" ", strip=True)
            # Try to heuristically get year and month
            # Typical label: "Vol 104 No 5 - December 2025"
            text_full = text
            # Try the parent block for more context
            if not re.search(r'\d{4}', text):
                parent = a.find_parent(['li', 'td', 'tr', 'div'])
                if parent:
                    text_full = parent.get_text(" ", strip=True)
            # Extract year and (optional) month
            m = re.search(r'([A-Z][a-z]+\s)?((19|20)\d\d)', text_full)
            if m:
                if m.group(1):
                    month = m.group(1).strip()
                year = int(m.group(2))
            # Clean label
            lbl = text_full.strip()
            if lbl.lower().startswith("the nucleus"):
                lbl = lbl[len("the nucleus"):].strip(" -")
            if not lbl:
                lbl = href.split("/")[-1]
            issues.append({
                "issue_label": lbl,
                "year": year,
                "month": month,
                "pdf_url": requests.compat.urljoin(ARCHIVE_URL, href),
            })
    # Deduplicate by PDF URL and label
    seen = set()
    out = []
    for i in issues:
        key = (i['pdf_url'].lower(), i['issue_label'])
        if key not in seen:
            out.append(i)
            seen.add(key)
    return out

def main():
    print(f"Fetching archive: {ARCHIVE_URL}")
    resp = polite_get(ARCHIVE_URL)
    if not resp:
        print("Failed to fetch archive page.", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    issues = extract_issues(soup)
    if not issues:
        print("No issues found on archive page.", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(issues)} issues (PDF links)")
    # Write output for downstream use
    with open("data/issues.json", "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)
    print("Written data/issues.json")

if __name__ == "__main__":
    main()