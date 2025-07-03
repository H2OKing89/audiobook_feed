#!/usr/bin/env python3
"""
audible_sample-gen.py  – fetch an Audible payload (if needed) and emit *only*
a stripped-down JSON fixture with fields:
    title • author • series • series_number • release • narrator • asin • link
The result lands in  tests/audiobook_samples/<author_slug>_clean.json
"""

from __future__ import annotations
import json, sys, urllib.parse as ulib
from pathlib import Path
from typing import Any, Dict, List

import requests

# ────────────────────────────── CONFIG ──────────────────────────────────────
CONFIG: Dict[str, Any] = {
    "sample_dir": Path("tests/audiobook_samples"),
    "author_slug": "Hiiro Shimotsuki",

    # Query builder (ignored if custom_url is set)
    "filter_type": "author",          # "author" | "title"
    "filter_value": "Hiiro Shimotsuki",
    "custom_url": None,              # drop a full API URL here to bypass building
    "num_results": 50,
    "marketplace": "US",

    # Keep podcasts?
    "include_podcasts": False,
}
# ─────────────────────────────────────────────────────────────────────────────
def ensure_dir(p: Path) -> None: p.mkdir(parents=True, exist_ok=True)

def clean_path() -> Path:
    return CONFIG["sample_dir"] / f"{CONFIG['author_slug']}_sample.json"

def audible_url() -> str:
    if CONFIG["custom_url"]:
        return CONFIG["custom_url"]
    base = "https://api.audible.com/1.0/catalog/products"
    params = dict(
        num_results=CONFIG["num_results"],
        products_sort_by="-ReleaseDate",
        response_groups="product_desc,media,contributors,series",
        marketplace=CONFIG["marketplace"],
    )
    key = "author" if CONFIG["filter_type"] == "author" else "title"
    params[key] = CONFIG["filter_value"]
    qs = "&".join(f"{k}={ulib.quote(str(v))}" for k, v in params.items())
    return f"{base}?{qs}"



def to_clean(r: Dict[str, Any]) -> Dict[str, Any]:
    """Exactly the eight fields from the jq sample."""
    return {
        "title":         r["title"],
        "author":        r["authors"][0]["name"] if r.get("authors") else "N/A",
        "series":        r.get("series", [{}])[0].get("title", "N/A"),
        "series_number": r.get("series", [{}])[0].get("sequence", "N/A"),
        "release":       r["release_date"],
        "narrator":      r.get("narrators", [{}])[0].get("name", "N/A"),
        "asin":          r["asin"],
        "link":          f"https://www.audible.com/pd/{r['asin']}",
    }

def keep_record(r: Dict[str, Any]) -> bool:
    if not CONFIG["include_podcasts"]:
        if r.get("content_type", "").lower() != "product":
            return False
        if "podcast" in r.get("content_delivery_type", "").lower():
            return False
    val = CONFIG["filter_value"].lower()
    if CONFIG["filter_type"] == "author":
        return any(val in a["name"].lower() for a in r.get("authors", []))
    return val in r.get("title", "").lower()

def fetch_audible_data() -> List[Dict[str, Any]]:
    """Fetch data from the Audible API."""
    url = audible_url()
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data.get("products", [])

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        ensure_dir(CONFIG["sample_dir"])
        clean = [to_clean(r) for r in fetch_audible_data() if keep_record(r)]
        clean_path().write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ wrote {len(clean)} record(s) → {clean_path()}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
