"""Scrape Upjau indoor/outdoor listings + product pages for care text & images."""
from __future__ import annotations

import json
import re
import time
import urllib.request
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(r"C:\Users\External\Desktop\Nurturing Flora")
DATA = ROOT / "data"
IMG_DIR = ROOT / "assets" / "plants"
DATA.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

SKIP_SLUGS = {
    "buy-plants-online-in-chennai-for-sale",
    "buy-plants-online-in-delhi",
    "buy-plants-online-in-kolkata",
    "buy-plants-online-in-gurgaon",
    "buy-plants-online-in-bangalore",
    "buy-plants-online-in-mumbai",
    "buy-plants-online-in-hyderabad",
    "buy-plants-online-in-pune",
    "buy-plants-online-in-jaipur",
    "buy-plants-online-india",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 1000:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://upjau.in/"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return dest.stat().st_size > 500
    except Exception as e:
        print("  download fail", url, e)
        return False


def clean_name(name: str) -> str:
    name = unescape(name)
    name = re.sub(r"\s+", " ", name).strip()
    # strip shoppy suffixes
    name = re.sub(r"\s*\(Sapling\)\s*$", "", name, flags=re.I)
    name = re.sub(r"\s*Sapling\s*$", "", name, flags=re.I)
    name = re.sub(r"\s*Plant\s*$", "", name, flags=re.I)  # keep if needed? better keep Plant words in middle
    # Actually restore "Plant" if it was meaningful - user wants plant names as listed
    # Re-do more gently:
    return unescape(re.sub(r"\s+", " ", name)).strip()


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def extract_listing_products(html: str, category: str) -> list[dict]:
    products = []
    seen = set()
    # Primary: thumbnail overlay with title + image
    pattern = re.compile(
        r'<a class="entry-thumbnail-overlay" href="(https://upjau\.in/[^"]+/)" title="([^"]+)">\s*'
        r'<img[^>]*data-src="(https://upjau\.in/wp-content/uploads/[^"]+)"',
        re.I | re.S,
    )
    for url, title, image in pattern.findall(html):
        path = urlparse(url).path.strip("/")
        if path in SKIP_SLUGS or path.startswith("buy-plants-online-in-"):
            continue
        if "combo" in title.lower() and "adenium marvels" in title.lower():
            # keep combos optional - skip bundle combos for care focus
            pass
        if url in seen:
            continue
        # Prefer primary thumb (first occurrence)
        seen.add(url)
        products.append(
            {
                "name": unescape(title).strip(),
                "url": url,
                "image": image.split("?")[0],
                "category": category,
            }
        )

    # Fallback via product-title anchors if primary missed some
    title_pat = re.compile(
        r'<h4 class="product-name product-title[^"]*">\s*'
        r'<a title="([^"]+)"[^>]+href="(https://upjau\.in/[^"]+/)"',
        re.I | re.S,
    )
    for title, url in title_pat.findall(html):
        path = urlparse(url).path.strip("/")
        if path in SKIP_SLUGS or path.startswith("buy-plants-online-in-"):
            continue
        if url in seen:
            continue
        seen.add(url)
        # try find nearby image for this url
        img_m = re.search(
            rf'href="{re.escape(url)}"[^>]*>\s*<img[^>]*data-src="(https://upjau\.in/wp-content/uploads/[^"]+)"',
            html,
            re.I | re.S,
        )
        products.append(
            {
                "name": unescape(title).strip(),
                "url": url,
                "image": (img_m.group(1).split("?")[0] if img_m else ""),
                "category": category,
            }
        )
    return products


def strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_care_from_product(html: str) -> dict:
    """Pull description / care-ish fields from a product page."""
    out = {
        "summary": "",
        "description": "",
        "light": "",
        "water": "",
        "soil": "",
        "humidity": "",
        "temperature": "",
        "fertilizer": "",
        "pot": "",
        "propagation": "",
        "scientific": "",
        "gallery": [],
    }

    # Woo short description
    m = re.search(
        r'<div[^>]*class="[^"]*woocommerce-product-details__short-description[^"]*"[^>]*>([\s\S]*?)</div>',
        html,
        re.I,
    )
    if m:
        out["summary"] = strip_html(m.group(1))[:400]

    # Main description tab
    m = re.search(
        r'<div[^>]*id="tab-description"[^>]*>([\s\S]*?)</div>\s*<div[^>]*id="tab-',
        html,
        re.I,
    )
    if not m:
        m = re.search(
            r'<div[^>]*class="[^"]*woocommerce-Tabs-panel--description[^"]*"[^>]*>([\s\S]*?)</div>',
            html,
            re.I,
        )
    if m:
        desc = strip_html(m.group(1))
        out["description"] = desc[:2500]

    full = (out["summary"] + " " + out["description"]).lower()
    text = out["summary"] + " " + out["description"]

    def grab(keys, default=""):
        for key in keys:
            # sentence containing key
            pat = re.compile(rf"([^.]*\b{key}\b[^.]*\.)", re.I)
            mm = pat.search(text)
            if mm:
                return mm.group(1).strip()
        return default

    out["light"] = grab(["sunlight", "light requirement", "indirect light", "bright light", "full sun", "low light"])
    out["water"] = grab(["water", "watering", "overwatering"])
    out["soil"] = grab(["soil", "potting mix", "well-draining", "well draining"])
    out["humidity"] = grab(["humidity", "mist"])
    out["temperature"] = grab(["temperature", "°c", "celsius"])
    out["fertilizer"] = grab(["fertilizer", "fertilise", "fertilize", "feed"])
    out["propagation"] = grab(["propagat", "cutting"])
    out["pot"] = grab(["pot with drainage", "drainage hole", "container"])

    # scientific from parentheses in title area
    sci = re.search(r"<h1[^>]*class=\"[^\"]*product_title[^\"]*\"[^>]*>[\s\S]*?</h1>", html, re.I)
    # also look for italic latin names
    sci2 = re.search(r"\(([A-Z][a-z]+ [a-z]+)\)", text)
    if sci2:
        out["scientific"] = sci2.group(1)

    # gallery images
    gallery = re.findall(
        r'data-src="(https://upjau\.in/wp-content/uploads/[^"]+\.(?:webp|jpg|jpeg|png))"',
        html,
        re.I,
    )
    # dedupe keep order
    seen = set()
    for g in gallery:
        g = g.split("?")[0]
        if g not in seen and "-100x" not in g and "-150x" not in g:
            seen.add(g)
            out["gallery"].append(g)
    return out


CARE_DEFAULTS = {
    "indoor": {
        "light": "Bright, indirect light suits most indoor tropical plants. Avoid harsh midday sun on tender leaves.",
        "water": "Water when the top 1–2 inches of soil feel dry. Ensure excess water drains freely.",
        "soil": "Use a loose, well-draining potting mix with cocopeat, compost, and perlite.",
        "humidity": "Average to moderate indoor humidity. Mist occasionally in dry seasons.",
        "temperature": "Ideally 18–30°C in most Indian homes.",
        "fertilizer": "Feed with a balanced liquid fertilizer every 4–6 weeks in the growing season.",
        "pot": "Choose a pot with drainage holes; avoid chronically soggy soil.",
        "propagation": "Many indoor plants propagate from stem cuttings with a node, or by division.",
    },
    "outdoor": {
        "light": "Most outdoor flowering plants prefer 4–6 hours of direct sun; check variety needs.",
        "water": "Water deeply when the topsoil dries. Increase frequency in peak summer heat.",
        "soil": "Fertile, well-draining garden soil enriched with compost.",
        "humidity": "Outdoor humidity is usually sufficient in Indian climates.",
        "temperature": "Thrives in warm outdoor conditions; protect tender types from extreme cold.",
        "fertilizer": "Apply compost or bloom fertilizer during active growth and flowering seasons.",
        "pot": "Large containers with drainage, or garden beds with good airflow.",
        "propagation": "Often propagated by cuttings, layering, or seeds depending on the species.",
    },
}


def fill_care(plant: dict, scraped: dict) -> dict:
    cat = plant["category"]
    defaults = CARE_DEFAULTS[cat]
    for key in defaults:
        plant[key] = scraped.get(key) or defaults[key]
    summary = scraped.get("summary") or scraped.get("description")
    if summary:
        # remove shopping CTA phrases
        summary = re.sub(r"(?i)buy\s+(now|online|this)[^.]*\.?", "", summary)
        summary = re.sub(r"(?i)add to cart[^.]*\.?", "", summary)
        summary = re.sub(r"(?i)free delivery[^.]*\.?", "", summary)
        summary = re.sub(r"\s+", " ", summary).strip()
        plant["summary"] = summary[:280]
    else:
        plant["summary"] = f"Care guide for {plant['display_name']} — light, watering, soil, and healthy growth tips."
    if scraped.get("scientific"):
        plant["scientific"] = scraped["scientific"]
    plant["description"] = (scraped.get("description") or plant["summary"])[:1200]
    plant["gallery"] = scraped.get("gallery") or []
    return plant


def scrape_category(slug: str, category: str, pages: int = 10) -> list[dict]:
    all_items = []
    seen = set()
    for page in range(1, pages + 1):
        url = f"https://upjau.in/{slug}/" if page == 1 else f"https://upjau.in/{slug}/page/{page}/"
        print(f"LIST {url}")
        try:
            html = fetch(url)
        except Exception as e:
            print("  list fail", e)
            continue
        items = extract_listing_products(html, category)
        added = 0
        for it in items:
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            all_items.append(it)
            added += 1
        print(f"  +{added} (total {len(all_items)})")
        time.sleep(0.4)
    return all_items


def main():
    indoor = scrape_category("indoor-plants", "indoor", 10)
    outdoor = scrape_category("outdoor-plants", "outdoor", 10)
    listings = {"indoor": indoor, "outdoor": outdoor}
    (DATA / "upjau_listings.json").write_text(json.dumps(listings, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Listings indoor", len(indoor), "outdoor", len(outdoor))

    plants = []
    # Limit detail fetches if huge — user asked for almost all; fetch all.
    combined = indoor + outdoor
    for i, raw in enumerate(combined, 1):
        name = raw["name"]
        display = clean_name(name)
        # restore cleaner display: remove trailing (Sapling) only
        display = re.sub(r"\s*\((?:Sapling|Any color|Any Colour)\)\s*$", "", display, flags=re.I).strip()
        display = re.sub(r"\s+Sapling\s*$", "", display, flags=re.I).strip()

        pid = slugify(display) or slugify(urlparse(raw["url"]).path)
        # avoid collisions
        base = pid
        n = 2
        existing = {p["id"] for p in plants}
        while pid in existing:
            pid = f"{base}-{n}"
            n += 1

        print(f"[{i}/{len(combined)}] {display}")
        plant = {
            "id": pid,
            "name": display,
            "display_name": display,
            "source_name": name,
            "source_url": raw["url"],
            "category": raw["category"],
            "scientific": "",
            "tags": [raw["category"]],
            "image_remote": raw.get("image") or "",
            "image": "",
        }

        scraped = {}
        try:
            html = fetch(raw["url"])
            scraped = extract_care_from_product(html)
            time.sleep(0.35)
        except Exception as e:
            print("  product fail", e)

        plant = fill_care(plant, scraped)

        # Tags heuristics
        tags = {raw["category"]}
        blob = (plant["name"] + " " + plant["summary"] + " " + plant["description"]).lower()
        if any(k in blob for k in ["beginner", "easy", "low maintenance", "low-maintenance"]):
            tags.add("beginner")
        if any(k in blob for k in ["air purif", "nasa", "oxygen"]):
            tags.add("air-purifying")
        if any(k in blob for k in ["flower", "bloom"]):
            tags.add("flowering")
        if any(k in blob for k in ["succulent", "cactus", "adenium", "desert rose"]):
            tags.add("succulent")
        if any(k in blob for k in ["climber", "vine", "trailing"]):
            tags.add("climber")
        if any(k in blob for k in ["fragrant", "perfume", "scent", "jasmine"]):
            tags.add("fragrant")
        if "low light" in blob:
            tags.add("low-light")
        plant["tags"] = sorted(tags)

        # Download primary image
        img_url = plant["image_remote"] or (plant["gallery"][0] if plant.get("gallery") else "")
        if img_url:
            ext = Path(urlparse(img_url).path).suffix or ".webp"
            fname = f"{pid}{ext}"
            dest = IMG_DIR / fname
            if download(img_url, dest):
                plant["image"] = f"assets/plants/{fname}"
            else:
                plant["image"] = img_url
        plants.append(plant)

        # checkpoint every 25
        if i % 25 == 0:
            (DATA / "plants_raw.json").write_text(json.dumps(plants, indent=2, ensure_ascii=False), encoding="utf-8")

    (DATA / "plants_raw.json").write_text(json.dumps(plants, indent=2, ensure_ascii=False), encoding="utf-8")
    print("DONE plants", len(plants))
    print("Indoor", sum(1 for p in plants if p["category"] == "indoor"))
    print("Outdoor", sum(1 for p in plants if p["category"] == "outdoor"))


if __name__ == "__main__":
    main()
