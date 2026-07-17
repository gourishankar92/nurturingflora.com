import re
from pathlib import Path
from html import unescape

html = Path(r"C:\Users\External\Desktop\Nurturing Flora\data\sample_indoor.html").read_text(encoding="utf-8")

# Find product title patterns near overlays
titles = re.findall(r'title="([^"]+)"[^>]*href="(https://upjau\.in/buy-[^"]+)"', html)
print("title before href", len(titles))
titles2 = re.findall(r'href="(https://upjau\.in/buy-[^"]+)"[^>]*title="([^"]+)"', html)
print("href before title", len(titles2))

# product-title links
for m in re.finditer(r'<h[23][^>]*class="[^"]*"(?:[^>]*)>(.*?)</h[23]>', html, re.I|re.S):
    text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if text and len(text) < 120 and ('Plant' in text or 'Sapling' in text or 'Aglaonema' in text or 'Philodendron' in text):
        print("H:", text)

# Look at woocommerce short description / product name classes
for cls in ["product-name", "product_title", "woocommerce-loop-product__title", "p-title", "title"]:
    print(cls, html.count(cls))

# Extract using overlay anchors
pairs = []
for m in re.finditer(
    r'<a class="entry-thumbnail-overlay" href="(https://upjau\.in/buy-[^"]+)" title="([^"]+)">\s*<img[^>]+data-src="(https://upjau\.in/wp-content/uploads/[^"]+)"',
    html,
    re.I | re.S,
):
    pairs.append(m.groups())
print("overlay pairs", len(pairs))
for p in pairs[:5]:
    print(p)

# alternative without class order
pairs2 = re.findall(
    r'href="(https://upjau\.in/buy-[^"]+)" title="([^"]+)"[\s\S]{0,500}?data-src="(https://upjau\.in/wp-content/uploads/[^"]+)"',
    html,
)
print("loose pairs", len(pairs2))
for p in pairs2[:3]:
    print(p[1], p[0].split('/')[-2], p[2].split('/')[-1])
