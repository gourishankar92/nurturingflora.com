(function () {
  const PER_PAGE = 24;

  function getPlants() {
    return (window.NURTURING_FLORA && window.NURTURING_FLORA.plants) || [];
  }

  function plantHref(id) {
    return `plant.html?id=${encodeURIComponent(id)}`;
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* Header sticky + mobile */
  const header = document.getElementById("siteHeader");
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");

  if (header) {
    const onScroll = () => {
      const sticky = window.scrollY > 120;
      header.classList.toggle("is-sticky", sticky);
      document.body.classList.toggle("has-sticky-header", sticky);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const open = links.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      document.body.style.overflow = open ? "hidden" : "";
    });
    links.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", () => {
        links.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        document.body.style.overflow = "";
      });
    });
  }

  /* Hero slider */
  const slides = document.querySelectorAll(".hero-slide");
  const dots = document.querySelectorAll(".hero-dot");
  let slideIndex = 0;
  let slideTimer;

  function goSlide(i) {
    if (!slides.length) return;
    slideIndex = (i + slides.length) % slides.length;
    slides.forEach((s, idx) => s.classList.toggle("is-active", idx === slideIndex));
    dots.forEach((d, idx) => d.classList.toggle("is-active", idx === slideIndex));
  }

  function startSlider() {
    if (slides.length < 2) return;
    clearInterval(slideTimer);
    slideTimer = setInterval(() => goSlide(slideIndex + 1), 7000);
  }

  dots.forEach((dot, i) => {
    dot.addEventListener("click", () => {
      goSlide(i);
      startSlider();
    });
  });
  startSlider();

  /* Stats */
  function mountStats() {
    const plants = getPlants();
    const indoor = plants.filter((p) => p.category === "indoor").length;
    const outdoor = plants.filter((p) => p.category === "outdoor").length;
    document.querySelectorAll("[data-stat]").forEach((el) => {
      const key = el.dataset.stat;
      if (key === "total") el.textContent = String(plants.length);
      if (key === "indoor") el.textContent = String(indoor);
      if (key === "outdoor") el.textContent = String(outdoor);
    });
  }

  function renderPlantCard(plant) {
    return `
      <a class="plant-card" href="${plantHref(plant.id)}">
        <div class="plant-card-img">
          <img src="${escapeHtml(plant.image)}" alt="${escapeHtml(plant.name)}" loading="lazy" />
          <span class="plant-badge">${escapeHtml(plant.category)}</span>
        </div>
        <div class="plant-card-body">
          <h6>${escapeHtml(plant.name)}</h6>
          <p>${escapeHtml(plant.summary)}</p>
          <span class="read-more">View Care Guide →</span>
        </div>
      </a>`;
  }

  function renderPortfolioItem(plant) {
    return `
      <a class="portfolio-item" href="${plantHref(plant.id)}" data-category="${escapeHtml(plant.category)}">
        <img src="${escapeHtml(plant.image)}" alt="${escapeHtml(plant.name)}" loading="lazy" />
        <div class="portfolio-overlay">
          <div>
            <h3>${escapeHtml(plant.name)}</h3>
            <h5>${escapeHtml(plant.category)} plant</h5>
          </div>
        </div>
      </a>`;
  }

  function mountFeatured() {
    const grid = document.querySelector("[data-featured-plants]");
    if (!grid) return;
    const featured = getPlants().slice(0, 8);
    grid.innerHTML = featured.map(renderPlantCard).join("");
  }

  function mountHomePortfolio() {
    const grid = document.querySelector("[data-home-portfolio]");
    const filterWrap = document.querySelector("[data-home-portfolio-filter]");
    if (!grid) return;

    const items = getPlants().slice(0, 9);

    function render(filter) {
      const list =
        filter === "all" ? items : items.filter((p) => p.category === filter);
      grid.innerHTML = list.map(renderPortfolioItem).join("");
    }

    if (filterWrap) {
      filterWrap.querySelectorAll(".filter-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          filterWrap.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("is-active"));
          btn.classList.add("is-active");
          render(btn.dataset.filter || "all");
        });
      });
    }
    render("all");
  }

  function mountPlantGrid() {
    const grid = document.querySelector("[data-plant-grid]");
    if (!grid) return;

    const searchInput = document.querySelector("[data-plant-search]");
    const chips = document.querySelectorAll("[data-filter-chip]");
    const resultsEl = document.querySelector("[data-results-count]");
    const pagerEl = document.querySelector("[data-pagination]");
    const category = grid.dataset.category || null;
    let activeFilter = "all";
    let page = 1;

    function filtered() {
      const q = (searchInput && searchInput.value.trim().toLowerCase()) || "";
      let plants = getPlants();
      if (category) plants = plants.filter((p) => p.category === category);
      if (activeFilter && activeFilter !== "all") {
        plants = plants.filter((p) => (p.tags || []).includes(activeFilter));
      }
      if (q) {
        plants = plants.filter((p) => {
          const hay = `${p.name} ${p.scientific} ${p.summary} ${(p.tags || []).join(" ")}`.toLowerCase();
          return hay.includes(q);
        });
      }
      return plants;
    }

    function renderPager(totalPages) {
      if (!pagerEl) return;
      if (totalPages <= 1) {
        pagerEl.innerHTML = "";
        return;
      }
      let html = `<button type="button" class="page-btn" data-page="prev" ${page <= 1 ? "disabled" : ""}>‹</button>`;
      const start = Math.max(1, page - 2);
      const end = Math.min(totalPages, start + 4);
      for (let i = start; i <= end; i++) {
        html += `<button type="button" class="page-btn ${i === page ? "is-active" : ""}" data-page="${i}">${i}</button>`;
      }
      html += `<button type="button" class="page-btn" data-page="next" ${page >= totalPages ? "disabled" : ""}>›</button>`;
      pagerEl.innerHTML = html;
      pagerEl.querySelectorAll("[data-page]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const val = btn.getAttribute("data-page");
          if (val === "prev") page = Math.max(1, page - 1);
          else if (val === "next") page = Math.min(totalPages, page + 1);
          else page = Number(val);
          apply(false);
          window.scrollTo({ top: grid.offsetTop - 100, behavior: "smooth" });
        });
      });
    }

    function apply(resetPage) {
      if (resetPage) page = 1;
      const plants = filtered();
      const totalPages = Math.max(1, Math.ceil(plants.length / PER_PAGE));
      if (page > totalPages) page = totalPages;
      const start = (page - 1) * PER_PAGE;
      const slice = plants.slice(start, start + PER_PAGE);

      if (resultsEl) {
        resultsEl.textContent = plants.length
          ? `Showing ${start + 1}–${Math.min(start + PER_PAGE, plants.length)} of ${plants.length} plants`
          : "No plants match your search";
      }

      if (!slice.length) {
        grid.innerHTML = `<p class="empty-state">No plants match your search.</p>`;
        renderPager(0);
        return;
      }

      grid.innerHTML = slice.map(renderPlantCard).join("");
      renderPager(totalPages);
    }

    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        chips.forEach((c) => c.classList.remove("is-active"));
        chip.classList.add("is-active");
        activeFilter = chip.dataset.filterChip;
        apply(true);
      });
    });

    if (searchInput) searchInput.addEventListener("input", () => apply(true));
    apply(true);
  }

  function mountPlantDetail() {
    const root = document.querySelector("[data-plant-detail]");
    if (!root) return;

    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    const plant = getPlants().find((p) => p.id === id);

    if (!plant) {
      root.innerHTML = `
        <div class="breadcrumb-area" style="background-image:url('assets/plants/monstera-swiss-cheese.webp')">
          <div class="breadcrumb-content"><h2>Plant Not Found</h2></div>
        </div>
        <section class="section-padding"><div class="container text-center">
          <p>That plant is not in our guide yet.</p>
          <a class="btn btn-primary" href="indoor.html" style="margin-top:20px">Browse Plants</a>
        </div></section>`;
      return;
    }

    document.title = `${plant.name} Care Guide · Nurturing Flora`;

    const careFields = [
      ["Light", plant.light],
      ["Water", plant.water],
      ["Soil", plant.soil],
      ["Humidity", plant.humidity],
      ["Temperature", plant.temperature],
      ["Fertilizer", plant.fertilizer],
      ["Pot", plant.pot],
      ["Propagation", plant.propagation],
    ];

    const careHtml = careFields
      .map(
        ([label, val]) =>
          `<div class="care-table-item"><h4>${escapeHtml(label)}</h4><p>${escapeHtml(val)}</p></div>`
      )
      .join("");

    const problemsRows = (plant.problems || [])
      .map(
        (row) =>
          `<tr><td>${escapeHtml(row.issue)}</td><td>${escapeHtml(row.cause)}</td><td>${escapeHtml(row.fix)}</td></tr>`
      )
      .join("");

    root.innerHTML = `
      <div class="plant-detail-hero" style="background-image:url('${escapeHtml(plant.image)}')">
        <div class="container">
          <span class="tag">${escapeHtml(plant.category)}</span>
          <h1>${escapeHtml(plant.name)}</h1>
          ${plant.scientific ? `<p style="color:rgba(255,255,255,.85);font-style:italic">${escapeHtml(plant.scientific)}</p>` : ""}
        </div>
      </div>
      <section class="section-padding">
        <div class="container">
          <div class="section-heading" style="text-align:left;margin-bottom:30px">
            <h2 style="font-size:28px">Care Essentials</h2>
            <p style="margin:0;text-align:left">${escapeHtml(plant.summary)}</p>
          </div>
          <div class="care-table">${careHtml}</div>
        </div>
      </section>
      <section class="section-padding bg-light" style="padding-top:0">
        <div class="container">
          <div class="section-heading" style="text-align:left;margin-bottom:20px">
            <h2 style="font-size:28px">Common Problems</h2>
          </div>
          <table class="problems-table">
            <thead><tr><th>Problem</th><th>Cause</th><th>Solution</th></tr></thead>
            <tbody>${problemsRows}</tbody>
          </table>
          <p style="margin-top:30px">
            <a class="btn btn-outline" href="${plant.category}.html">← Back to ${plant.category} plants</a>
          </p>
        </div>
      </section>`;
  }

  document.addEventListener("DOMContentLoaded", () => {
    mountStats();
    mountFeatured();
    mountHomePortfolio();
    mountPlantDetail();
    mountPlantGrid();
  });
})();
