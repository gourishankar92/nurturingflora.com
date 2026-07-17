"""Scrape Upjau indoor/outdoor plant listings (names, links, images)."""
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

OUT = Path(r"C:\Users\External\Desktop\Nurturing Flora\data")
OUT.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


class ProductExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.products = []
        self._in_li = False
        self._li_depth = 0
        self._capture = False
        self._curr = None
        self._in_title = False
        self._title_buf = []
        self._attrs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._attrs = attrs
        classes = attrs.get("class", "")

        if tag == "li" and "product" in classes.split():
            self._in_li = True
            self._li_depth = 1
            self._curr = {"name": "", "url": "", "image": "", "classes": classes}
            return

        if self._in_li and tag == "li":
            self._li_depth += 1

        if not self._in_li or not self._curr:
            return

        if tag == "a" and not self._curr["url"]:
            href = attrs.get("href", "")
            if href and "upjau.in" in href and "/product/" in href or (href.startswith("https://upjau.in/") and "/product" in href):
                self._curr["url"] = href
            elif href.startswith("https://upjau.in/") and "product" in href:
                self._curr["url"] = href
            elif "/product/" in href:
                self._curr["url"] = href

        if tag == "a" and "woocommerce-LoopProduct-link" in classes:
            href = attrs.get("href", "")
            if href:
                self._curr["url"] = href

        if tag == "img":
            src = (
                attrs.get("data-src")
                or attrs.get("data-lazy-src")
                or attrs.get("src")
                or ""
            )
            srcset = attrs.get("data-srcset") or attrs.get("srcset") or ""
            if srcset and ("wp-content" in srcset or "uploads" in srcset):
                # pick largest
                parts = [p.strip() for p in srcset.split(",") if p.strip()]
                best = ""
                best_w = 0
                for p in parts:
                    bits = p.split()
                    if not bits:
                        continue
                    u = bits[0]
                    w = 0
                    if len(bits) > 1 and bits[1].endswith("w"):
                        try:
                            w = int(bits[1][:-1])
                        except ValueError:
                            w = 0
                    if w >= best_w:
                        best_w = w
                        best = u
                if best:
                    src = best
            if src and "data:image" not in src and ("uploads" in src or "wp-content" in src):
                if not self._curr["image"] or "-300x" in self._curr["image"] or "-150x" in self._curr["image"]:
                    self._curr["image"] = src.split("?")[0]

        if tag in ("h2", "h3") and ("woocommerce-loop-product__title" in classes or "product-title" in classes):
            self._in_title = True
            self._title_buf = []

    def handle_endtag(self, tag):
        if self._in_title and tag in ("h2", "h3"):
            self._in_title = False
            if self._curr is not None:
                self._curr["name"] = re.sub(r"\s+", " ", "".join(self._title_buf)).strip()

        if self._in_li and tag == "li":
            self._li_depth -= 1
            if self._li_depth <= 0:
                if self._curr and self._curr.get("name") and self._curr.get("url"):
                    self.products.append(self._curr)
                self._in_li = False
                self._curr = None
                self._li_depth = 0

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)


def scrape_category(slug: str, pages: int = 10):
    all_products = []
    seen = set()
    for page in range(1, pages + 1):
        url = f"https://upjau.in/{slug}/" if page == 1 else f"https://upjau.in/{slug}/page/{page}/"
        print(f"Fetching {url}")
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        # Fallback regex extract if parser misses
        parser = ProductExtractor()
        parser.feed(html)
        items = parser.products

        if len(items) < 5:
            # WooCommerce JSON-LD or product blocks
            # Match product cards more loosely
            for m in re.finditer(
                r'<li[^>]*class="[^"]*product[^"]*"[^>]*>(.*?)</li>',
                html,
                re.I | re.S,
            ):
                block = m.group(0)
                name_m = re.search(r'woocommerce-loop-product__title[^>]*>(.*?)</', block, re.I | re.S)
                if not name_m:
                    name_m = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.I | re.S)
                link_m = re.search(r'href="(https://upjau\.in/product/[^"]+)"', block)
                img_m = re.search(
                    r'(?:data-src|data-large_image|src)="(https://upjau\.in/wp-content/uploads/[^"]+\.(?:jpg|jpeg|png|webp))"',
                    block,
                    re.I,
                )
                if not img_m:
                    img_m = re.search(
                        r'srcset="([^"]+)"',
                        block,
                        re.I,
                    )
                    if img_m:
                        # parse srcset
                        srcset = img_m.group(1)
                        best = ""
                        best_w = 0
                        for part in srcset.split(","):
                            bits = part.strip().split()
                            if not bits:
                                continue
                            u = bits[0]
                            w = 0
                            if len(bits) > 1 and bits[1].endswith("w"):
                                try:
                                    w = int(bits[1][:-1])
                                except ValueError:
                                    pass
                            if "uploads" in u and w >= best_w:
                                best_w = w
                                best = u
                        img_url = best
                    else:
                        img_url = ""
                else:
                    img_url = img_m.group(1)

                if name_m and link_m:
                    name = re.sub(r"<[^>]+>", "", name_m.group(1))
                    name = re.sub(r"\s+", " ", name).strip()
                    items.append(
                        {
                            "name": name,
                            "url": link_m.group(1),
                            "image": img_url.split("?")[0] if img_url else "",
                        }
                    )

        added = 0
        for p in items:
            key = p.get("url") or p.get("name")
            if not key or key in seen:
                continue
            seen.add(key)
            p["category"] = "indoor" if "indoor" in slug else "outdoor"
            # upgrade image to full size if thumbnail
            img = p.get("image") or ""
            img = re.sub(r"-\d+x\d+(?=\.(?:jpg|jpeg|png|webp))", "", img, flags=re.I)
            p["image"] = img
            all_products.append(p)
            added += 1
        print(f"  got {len(items)} raw, +{added} unique (total {len(all_products)})")
        time.sleep(0.6)
    return all_products


def main():
    indoor = scrape_category("indoor-plants", 10)
    outdoor = scrape_category("outdoor-plants", 10)
    data = {"indoor": indoor, "outdoor": outdoor, "counts": {"indoor": len(indoor), "outdoor": len(outdoor)}}
    out_file = OUT / "upjau_listings.json"
    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Saved", out_file)
    print("Indoor:", len(indoor), "Outdoor:", len(outdoor))


if __name__ == "__main__":
    main()
