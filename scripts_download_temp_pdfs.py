import os
import sys
import json
import requests
import time
from urllib.parse import urlparse, unquote

TMP_PDF_DIR = "tmp_pdfs"
ISSUE_LIST_JSON = "data/issues.json"
HEADERS = {
    "User-Agent": "NESACS-Nucleus-Indexer/1.0 (mailto:info@example.com)"
}

os.makedirs(TMP_PDF_DIR, exist_ok=True)

def polite_download(url, dest):
    """Download with slow rate and chunked write."""
    resp = None
    for i in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
            if resp.status_code == 200:
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True
            else:
                print(f"Warning: HTTP {resp.status_code} for {url}", file=sys.stderr)
        except Exception as e:
            print(f"Download error for {url}: {e}", file=sys.stderr)
        time.sleep(3 * (i+1))
    return False

def filename_from_url(url):
    fname = os.path.basename(urlparse(url).path)
    fname = unquote(fname)
    return fname.replace("/", "_").replace("..", "_")

def main():
    with open(ISSUE_LIST_JSON, "r", encoding="utf-8") as f:
        issues = json.load(f)
    print(f"Downloading {len(issues)} issue PDFs to {TMP_PDF_DIR}")
    for idx, issue in enumerate(issues):
        url = issue["pdf_url"]
        fname = filename_from_url(url)
        filepath = os.path.join(TMP_PDF_DIR, fname)
        if not os.path.exists(filepath):
            print(f"  [{idx+1}/{len(issues)}] Downloading {url}...")
            ok = polite_download(url, filepath)
            if not ok:
                print(f"Failed to download {url}", file=sys.stderr)
        else:
            print(f"  [{idx+1}/{len(issues)}] Already downloaded {filepath}")
        time.sleep(2)
    print("All downloads complete.")

if __name__ == "__main__":
    main()