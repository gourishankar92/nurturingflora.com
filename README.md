# Nurturing Flora

Premium plant-care information site for [nurturingflora.com](https://nurturingflora.com) — indoor and outdoor guides with photography. No shop.

## Preview

Open `index.html` in a browser, or from this folder:

```bash
python -m http.server 5173
```

Visit http://localhost:5173

## What’s included

- **272 plant care pages** (135 indoor · 137 outdoor)
- Search, filters, and pagination
- Care essentials + troubleshooting on every plant
- Logo assets in `assets/`
- Plant photos in `assets/plants/`

## Updating the catalog

```bash
python scripts/scrape_all.py      # re-fetch listings + images
python scripts/convert_plants.py  # rebuild js/plants.js
```

Gift boxes and multi-plant combos are excluded so the library stays care-focused.
