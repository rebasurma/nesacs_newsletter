import os
import sys
import json
import hashlib
import re
from collections import defaultdict

IN_JSON_DIR = "tmp_articles_json"
CARDS_JSON_DIR = "data/cards_json"
CARDS_MD_DIR = "data/cards_md"
MANIFEST_PATH = "data/manifest.json"
os.makedirs(CARDS_JSON_DIR, exist_ok=True)
os.makedirs(CARDS_MD_DIR, exist_ok=True)

CONTROLLED_TAGS = [
    "analytical chemistry", "outreach", "education", "safety", "awards",
    "industry news", "conference", "obituary", "research", "career",
    "society news", "events", "community", "honors", "member spotlight",
    "environment", "student", "grant", "public policy", "history",
    # Add more as needed
]

def slugify(text, maxlen=48):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    slug = text.strip("-")
    if len(slug) > maxlen:
        slug = slug[:maxlen].strip("-")
    return slug or "untitled"

def summarize(text):
    """Generate 3-6 summary bullet points from article body."""
    # Snag the first 2–3 non-empty shortish sentences, then key points as bullets.
    sents = re.split(r"\.(?:\s|$)", text)
    points = []
    for s in sents:
        t = s.strip().replace("\n", " ")
        if 30 < len(t) < 180:
            points.append(t.lstrip("-*•").strip())
        if len(points) == 4:
            break
    # Fallback if not enough: extract main names or themes
    if len(points) < 3:
        # Try to find "This article reports..." or "The award was given..."
        points += re.findall(r"([A-Z][^\.]{20,120})", text)
    points = list(dict.fromkeys(points))  # dedup
    # Max 6
    return points[:6]

def extract_tags(text, title):
    tags = set()
    content = " ".join([title, text]).lower()
    # Key to tag vocabulary
    for tag in CONTROLLED_TAGS:
        if tag in content:
            tags.add(tag)
    # Rules: simple keyword lookup, more tags if article is longer
    # Add keyword-based
    if "school" in content or "student" in content:
        tags.add("education")
    if "award" in content or "honor" in content:
        tags.add("awards")
    if re.search(r'obit|in memoriam|passed away|remembrance', content):
        tags.add("obituary")
    # Expand to 3 if too few, fallback to "society news"
    if len(tags) < 3:
        tags.add("society news")
    return list(tags)[:8]

def validate_card(card):
    # Make sure all required fields exist and are legal
    KEYS = ["title", "summary", "tags", "issue_label", "year", "month", "source_url"]
    for k in KEYS:
        if k not in card or card[k] is None:
            return False
    if not isinstance(card["summary"], list) or not (3 <= len(card["summary"]) <= 6):
        return False
    if not isinstance(card["tags"], list) or not (3 <= len(card["tags"]) <= 8):
        return False
    if len(card["title"]) < 4:
        return False
    if not card["source_url"].startswith("http"):
        return False
    return True

def main():
    manifest = []
    per_issue_counts = defaultdict(int)
    for fname in sorted(os.listdir(IN_JSON_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(IN_JSON_DIR, fname), encoding="utf-8") as f:
            articles = json.load(f)
        if not articles:
            continue
        first_issue = articles[0].get("issue_label") or fname
        year = articles[0].get("year")
        issue_label = articles[0].get("issue_label")
        safe_issue = slugify(issue_label, maxlen=32)
        out_json_dir = os.path.join(CARDS_JSON_DIR, str(year), safe_issue)
        out_md_dir = os.path.join(CARDS_MD_DIR, str(year), safe_issue)
        os.makedirs(out_json_dir, exist_ok=True)
        os.makedirs(out_md_dir, exist_ok=True)
        for idx, art in enumerate(articles):
            title = art["title"]
            body = art["body"]
            card = {
                "title": title[:120].strip(),
                "summary": summarize(body),
                "tags": extract_tags(body, title),
                "issue_label": art["issue_label"],
                "year": art["year"],
                "month": art.get("month"),
                "source_url": art["source_url"]
            }
            # Validate & skip invalid
            if not validate_card(card):
                print(f"Skipping invalid card: {title}", file=sys.stderr)
                continue
            # Card slug: first ~40 chars of title hashed, no fulltext
            slug_raw = slugify(title)[:40] + "-" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:10]
            # JSON card
            fp_json = os.path.join(out_json_dir, f"{slug_raw}.json")
            with open(fp_json, "w", encoding="utf-8") as fout:
                json.dump(card, fout, indent=2, ensure_ascii=False)
            # Markdown card
            fp_md = os.path.join(out_md_dir, f"{slug_raw}.md")
            with open(fp_md, "w", encoding="utf-8") as fout:
                fout.write(f"# {card['title']}\n\n")
                fout.write(f"> Published in: **{card['issue_label']}** ({card['year']}{', ' + card['month'] if card.get('month') else ''})\n")
                fout.write(f"\n**Source:** [{card['source_url']}]({card['source_url']})\n\n")
                fout.write("## Summary\n")
                for b in card["summary"]:
                    fout.write(f"- {b.strip()}\n")
                fout.write("\n**Tags:** " + ", ".join(card["tags"]) + "\n")
            per_issue_counts[(card["year"], safe_issue)] += 1
        manifest.append({
            "issue_label": issue_label,
            "year": year,
            "issue_slug": safe_issue,
            "article_count": per_issue_counts[(year, safe_issue)],
        })
    # Sort manifest
    manifest_sorted = sorted(manifest, key=lambda d: (d["year"] or 0, d["issue_label"]))
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump({"issues": manifest_sorted }, f, indent=2)
    print("All cards written and manifest generated.")

if __name__ == "__main__":
    main()