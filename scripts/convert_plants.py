"""Convert scraped plants_raw.json into clean plants.js for the website."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\External\Desktop\Nurturing Flora")
RAW = ROOT / "data" / "plants_raw.json"
OUT_JS = ROOT / "js" / "plants.js"
OUT_JSON = ROOT / "data" / "plants.json"

SKIP_NAME_RE = re.compile(
    r"(gift|combo of|marvels combo|freebie|subscription|voucher|planter only|pot only)",
    re.I,
)

BUY_NOISE = re.compile(
    r"(?i)("
    r"buy\s+[^.]*?(online|india|upjau)[^.]*\.|"
    r"add to cart[^.]*\.|"
    r"free delivery[^.]*\.|"
    r"shop\s+(now|today)[^.]*\.|"
    r"starting\s+(at|from)\s+[^.]*\.|"
    r"best price[^.]*\.|"
    r"order\s+today[^.]*\.|"
    r"click here[^.]*\.|"
    r"₹\s?\d+[^.]*\."
    r")"
)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = BUY_NOISE.sub(" ", text)
    text = re.sub(r"(?i)\bupjau\b", "Nurturing Flora", text)
    text = re.sub(r"\s+", " ", text).strip(" -–,")
    return text


def shorten(text: str, n: int = 220) -> str:
    text = clean_text(text)
    if len(text) <= n:
        return text
    cut = text[: n - 1].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def care_or_default(value: str, default: str) -> str:
    value = clean_text(value)
    if not value or len(value) < 24:
        return default
    # strip leading "Light:" labels
    value = re.sub(r"^(Light|Water|Soil|Humidity|Temperature|Fertilizer|Pot|Propagation)\s*:\s*", "", value, flags=re.I)
    return value[:420]


INDOOR_DEFAULTS = {
    "light": "Bright, indirect light. Protect tender leaves from harsh midday sun.",
    "water": "Water when the top 1–2 inches of soil feel dry. Let excess water drain.",
    "soil": "Loose, well-draining mix with cocopeat, compost, and perlite.",
    "humidity": "Average to moderate indoor humidity; mist in dry weather.",
    "temperature": "18–30°C suits most Indian indoor spaces.",
    "fertilizer": "Balanced liquid feed every 4–6 weeks in the growing season.",
    "pot": "Use a pot with drainage holes to prevent root rot.",
    "propagation": "Stem cuttings with a node, or division during repotting.",
}
OUTDOOR_DEFAULTS = {
    "light": "Usually 4–6 hours of sun; flowering types often prefer fuller sun.",
    "water": "Water deeply when topsoil dries. Increase in peak summer heat.",
    "soil": "Fertile, well-draining garden soil with compost.",
    "humidity": "Outdoor humidity is typically enough in Indian climates.",
    "temperature": "Warm outdoor conditions; shield tender plants from extreme cold.",
    "fertilizer": "Compost or bloom fertilizer during active growth.",
    "pot": "Large drained containers or garden beds with airflow.",
    "propagation": "Cuttings, layering, or seed depending on the species.",
}

PROBLEMS = {
    "indoor": [
        {"issue": "Yellow leaves", "cause": "Overwatering or poor drainage", "fix": "Let soil dry; improve drainage"},
        {"issue": "Brown tips", "cause": "Dry air or mineral-heavy water", "fix": "Mist; use filtered water"},
        {"issue": "Leggy growth", "cause": "Insufficient light", "fix": "Move to brighter indirect light"},
        {"issue": "Pests", "cause": "Mealybugs or spider mites", "fix": "Wipe leaves; apply neem oil"},
    ],
    "outdoor": [
        {"issue": "Few blooms", "cause": "Too little sun or excess nitrogen", "fix": "More sun; use bloom fertilizer"},
        {"issue": "Yellow leaves", "cause": "Water stress or nutrient gap", "fix": "Steady watering; add compost"},
        {"issue": "Wilting", "cause": "Heat stress or dry roots", "fix": "Deep water early morning"},
        {"issue": "Pests", "cause": "Aphids or mealybugs", "fix": "Neem oil spray regularly"},
    ],
}


def convert(raw: list[dict]) -> list[dict]:
    plants = []
    seen_ids = set()
    for item in raw:
        name = item.get("name") or item.get("display_name") or ""
        if SKIP_NAME_RE.search(name):
            continue
        if "combo of" in name.lower():
            continue

        pid = item["id"]
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        cat = item.get("category", "indoor")
        defaults = INDOOR_DEFAULTS if cat == "indoor" else OUTDOOR_DEFAULTS

        summary = shorten(item.get("summary") or item.get("description") or "", 230)
        if len(summary) < 40:
            summary = f"Practical care notes for {name}: light, watering, soil, and healthy growth indoors." if cat == "indoor" else f"Practical care notes for {name}: sunlight, watering, soil, and blooming outdoors."

        image = item.get("image") or item.get("image_remote") or ""
        # Prefer local asset path
        if image.startswith("http"):
            # keep remote as fallback
            pass

        plant = {
            "id": pid,
            "name": name,
            "scientific": item.get("scientific") or "",
            "category": cat,
            "tags": item.get("tags") or [cat],
            "summary": summary,
            "image": image,
            "light": care_or_default(item.get("light", ""), defaults["light"]),
            "water": care_or_default(item.get("water", ""), defaults["water"]),
            "soil": care_or_default(item.get("soil", ""), defaults["soil"]),
            "humidity": care_or_default(item.get("humidity", ""), defaults["humidity"]),
            "temperature": care_or_default(item.get("temperature", ""), defaults["temperature"]),
            "fertilizer": care_or_default(item.get("fertilizer", ""), defaults["fertilizer"]),
            "pot": care_or_default(item.get("pot", ""), defaults["pot"]),
            "propagation": care_or_default(item.get("propagation", ""), defaults["propagation"]),
            "problems": PROBLEMS[cat],
        }
        plants.append(plant)

    # Sort: indoor then outdoor, alpha
    plants.sort(key=lambda p: (0 if p["category"] == "indoor" else 1, p["name"].lower()))
    return plants


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    plants = convert(raw)
    OUT_JSON.write_text(json.dumps(plants, indent=2, ensure_ascii=False), encoding="utf-8")
    js = (
        "window.NURTURING_FLORA = "
        + json.dumps({"plants": plants}, ensure_ascii=False, indent=2)
        + ";\n"
    )
    OUT_JS.write_text(js, encoding="utf-8")
    indoor = sum(1 for p in plants if p["category"] == "indoor")
    outdoor = sum(1 for p in plants if p["category"] == "outdoor")
    print(f"Wrote {len(plants)} plants ({indoor} indoor, {outdoor} outdoor) -> {OUT_JS}")


if __name__ == "__main__":
    main()
