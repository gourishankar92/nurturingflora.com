import re
from pathlib import Path

html = Path(r"C:\Users\External\Desktop\Nurturing Flora\data\sample_indoor.html").read_text(encoding="utf-8")

idx = html.find("product-thumb-primary")
Path(r"C:\Users\External\Desktop\Nurturing Flora\data\snippet.html").write_text(html[idx:idx+3500], encoding="utf-8")

# Count patterns
patterns = {
    "buy-links": r'href="(https://upjau\.in/buy-[^"]+)"',
    "data-src": r'data-src="(https://upjau\.in/wp-content/uploads/[^"]+)"',
    "data-lazy-src": r'data-lazy-src="(https://upjau\.in/wp-content/uploads/[^"]+)"',
    "noscript img": r'<noscript>.*?<img[^>]+src="(https://upjau\.in/wp-content/uploads/[^"]+)"',
    "product titles h2": r'<h2 class="woocommerce-loop-product__title">([^<]+)</h2>',
    "product-title class": r'class="[^"]*product-title[^"]*"[^>]*>([^<]+)',
    "entry-title": r'class="[^"]*woocommerce-loop-product__title[^"]*"',
}
for name, pat in patterns.items():
    ms = re.findall(pat, html, flags=re.I | re.S)
    print(name, len(ms))
    if ms:
        print(" ", ms[0] if isinstance(ms[0], str) else ms[0][:120])

# Unique buy links
buys = list(dict.fromkeys(re.findall(r'href="(https://upjau\.in/buy-[^"]+)"', html)))
print("unique buy links", len(buys))
print("\n".join(buys[:8]))
