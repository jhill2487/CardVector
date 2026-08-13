(() => {
  const CARDUPLOADER_URL_RE = /^https:\/\/carduploader\.com\/dashboard\/inventory\/automatic(?:[/?#]|$)/i;
  const CARDVECTOR_URL_RE = /^https:\/\/cardvector\.app\/operator\/repricing(?:[/?#]|$)/i;
  const STORAGE_KEY = "cardvector.latestCardUploaderAutomaticInventorySnapshot.v1";
  const PAGE_STORAGE_KEY = "cardvector.carduploaderAutomaticInventorySnapshot.v1";
  const SNAPSHOT_SOURCE = "carduploader_automatic_inventory_page_snapshot";
  const PANEL_ID = "cardvector-carduploader-helper";
  const EXPECTED_HEADERS = new Set([
    "card",
    "status",
    "platform",
    "user sku",
    "catalog sku",
    "condition",
    "variant",
    "price",
    "market",
    "qty",
    "added"
  ]);

  function clean(value, max = 600) {
    return String(value || "").replace(/\s+/g, " ").trim().slice(0, max);
  }

  function money(value) {
    const match = String(value || "").match(/\$?\s*([0-9]+(?:\.[0-9]{1,2})?)/);
    return match ? Number(match[1]) : null;
  }

  function integer(value) {
    const parsed = Number.parseInt(String(value || "").replace(/,/g, ""), 10);
    return Number.isFinite(parsed) ? Math.max(0, parsed) : null;
  }

  function headerKey(value) {
    return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  function looksLikeAutomaticInventoryHeaders(headers) {
    return headers.map(headerKey).filter((header) => EXPECTED_HEADERS.has(header)).length >= 7;
  }

  function mappedCells(headers, cells) {
    const mapped = {};
    headers.forEach((header, index) => {
      const key = headerKey(header);
      if (key && index < cells.length) {
        mapped[key] = clean(cells[index], 400);
      }
    });
    return mapped;
  }

  function selectorFor(element) {
    if (!element) {
      return "";
    }
    if (element.id) {
      return `#${CSS.escape(element.id)}`;
    }
    const name = element.getAttribute("name");
    if (name) {
      return `${element.tagName.toLowerCase()}[name="${CSS.escape(name)}"]`;
    }
    const dataAttr = Array.from(element.attributes || []).find((candidate) => candidate.name.startsWith("data-"));
    if (dataAttr) {
      return `${element.tagName.toLowerCase()}[${dataAttr.name}="${CSS.escape(dataAttr.value)}"]`;
    }
    return element.tagName.toLowerCase();
  }

  function isVisible(element) {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
  }

  function visibleControls() {
    return Array.from(document.querySelectorAll("button, input[type='button'], input[type='submit'], a"))
      .filter(isVisible)
      .map((element) => ({
        text: clean(element.innerText || element.value, 120),
        aria_label: clean(element.getAttribute("aria-label"), 120),
        selector: selectorFor(element)
      }));
  }

  function visibleEditableControls() {
    return Array.from(document.querySelectorAll("input, textarea, [contenteditable='true']"))
      .filter(isVisible)
      .map((element) => ({
        value: clean(element.value || element.textContent, 120),
        name: clean(element.getAttribute("name"), 120),
        id: element.id || "",
        aria_label: clean(element.getAttribute("aria-label"), 120),
        placeholder: clean(element.getAttribute("placeholder"), 120),
        selector: selectorFor(element)
      }));
  }

  function scanAutomaticInventoryRows() {
    const rows = [];
    Array.from(document.querySelectorAll("table")).forEach((table) => {
      const headers = Array.from(table.querySelectorAll("th")).map((cell) => clean(cell.innerText, 120));
      if (!looksLikeAutomaticInventoryHeaders(headers)) {
        return;
      }
      Array.from(table.querySelectorAll("tbody tr, tr")).forEach((row) => {
        const cells = Array.from(row.querySelectorAll("td, th")).map((cell) => clean(cell.innerText, 400));
        const rawText = clean(row.innerText || cells.join(" "), 1400);
        if (!rawText || cells.length < 2) {
          return;
        }
        if (headers.length && cells.join("|").toLowerCase() === headers.join("|").toLowerCase()) {
          return;
        }
        const mapped = mappedCells(headers, cells);
        const catalogSku = ((rawText.match(/\bCS-[A-Z0-9-]+\b/i) || [""])[0] || "").toUpperCase();
        const location = ((rawText.match(/\bETB-[0-9]{3}-[A-J](?:\.[0-9]+)?\b/i) || [""])[0] || "").toUpperCase();
        const priceCell = mapped.price || cells.find((cell) => /\$[0-9]/.test(cell)) || "";
        rows.push({
          row_number: rows.length + 1,
          row_key: mapped["catalog sku"] || catalogSku || mapped["user sku"] || location || `row-${rows.length + 1}`,
          title: mapped.card || cells[0] || rawText.slice(0, 120),
          status: mapped.status || "",
          platform: mapped.platform || "",
          catalog_sku: mapped["catalog sku"] || catalogSku,
          user_sku: mapped["user sku"] || location,
          location,
          condition: mapped.condition || "",
          variant: mapped.variant || "",
          current_price: money(priceCell),
          market_price: money(mapped.market || ""),
          quantity: integer(mapped.qty),
          added: mapped.added || "",
          raw_text: rawText
        });
      });
    });
    return rows;
  }

  function buildSnapshot() {
    return {
      source: SNAPSHOT_SOURCE,
      url: location.href,
      title: document.title || "CardUploader automatic inventory",
      captured_at: new Date().toISOString(),
      controls: visibleControls(),
      editable_controls: visibleEditableControls(),
      rows: scanAutomaticInventoryRows()
    };
  }

  function saveSnapshot(snapshot) {
    return chrome.storage.local.set({ [STORAGE_KEY]: snapshot });
  }

  function readSnapshot() {
    return chrome.storage.local.get(STORAGE_KEY).then((result) => result[STORAGE_KEY] || null);
  }

  function writeSnapshotToCardVectorPage(snapshot) {
    window.localStorage.setItem(PAGE_STORAGE_KEY, JSON.stringify(snapshot));
    window.dispatchEvent(new CustomEvent("cardvector:carduploader-helper-snapshot", { detail: snapshot }));
  }

  function panelShell(title) {
    const existing = document.getElementById(PANEL_ID);
    if (existing) {
      return existing;
    }
    const panel = document.createElement("aside");
    panel.id = PANEL_ID;
    panel.className = "cardvector-helper-panel";
    panel.innerHTML = `
      <header>
        <h2>${title}</h2>
        <button type="button" data-cv-helper-close aria-label="Hide CardVector helper">Hide</button>
      </header>
      <div class="cardvector-helper-body" data-cv-helper-body></div>
    `;
    document.documentElement.appendChild(panel);
    panel.querySelector("[data-cv-helper-close]").addEventListener("click", () => panel.remove());
    return panel;
  }

  function renderCardUploaderPanel(message = "Ready to scan visible automatic-inventory rows.") {
    const panel = panelShell("CardVector Helper");
    const body = panel.querySelector("[data-cv-helper-body]");
    body.innerHTML = `
      <p class="cardvector-helper-status">${message}</p>
      <div class="cardvector-helper-actions">
        <button class="primary" type="button" data-cv-scan>Scan Visible Rows</button>
        <button type="button" data-cv-open-review>Open Review</button>
      </div>
      <div class="cardvector-helper-meta" data-cv-meta>
        <span>Snapshot</span>
        <strong>Not scanned</strong>
        <span>Read-only. No prices are edited.</span>
      </div>
    `;
    body.querySelector("[data-cv-scan]").addEventListener("click", async () => {
      const snapshot = buildSnapshot();
      await saveSnapshot(snapshot);
      body.querySelector("[data-cv-meta]").innerHTML = `
        <span>Snapshot</span>
        <strong>${snapshot.rows.length} rows</strong>
        <span>Captured ${snapshot.captured_at}</span>
      `;
      body.querySelector(".cardvector-helper-status").textContent = "Snapshot saved locally for CardVector.app review.";
    });
    body.querySelector("[data-cv-open-review]").addEventListener("click", () => {
      window.open("https://cardvector.app/operator/repricing", "_blank", "noopener,noreferrer");
    });
  }

  async function renderCardVectorPanel() {
    const panel = panelShell("CardVector Helper");
    const body = panel.querySelector("[data-cv-helper-body]");
    const snapshot = await readSnapshot();
    const count = snapshot && Array.isArray(snapshot.rows) ? snapshot.rows.length : 0;
    body.innerHTML = `
      <p class="cardvector-helper-status">${count ? "A CardUploader snapshot is available in this Chrome profile." : "No CardUploader snapshot has been scanned in this Chrome profile yet."}</p>
      <div class="cardvector-helper-actions">
        <button class="primary" type="button" data-cv-sync${count ? "" : " disabled"}>Send to Page</button>
        <button type="button" data-cv-open-carduploader>Open CardUploader</button>
      </div>
      <div class="cardvector-helper-meta">
        <span>Latest Snapshot</span>
        <strong>${count} rows</strong>
        <span>${snapshot && snapshot.captured_at ? snapshot.captured_at : "Not captured"}</span>
      </div>
    `;
    body.querySelector("[data-cv-sync]")?.addEventListener("click", async () => {
      const latest = await readSnapshot();
      if (latest) {
        writeSnapshotToCardVectorPage(latest);
        body.querySelector(".cardvector-helper-status").textContent = "Snapshot sent to CardVector.app. Click Check helper status, then Load helper snapshot.";
      }
    });
    body.querySelector("[data-cv-open-carduploader]").addEventListener("click", () => {
      window.open("https://carduploader.com/dashboard/inventory/automatic", "_blank", "noopener,noreferrer");
    });
    if (snapshot) {
      writeSnapshotToCardVectorPage(snapshot);
    }
  }

  if (CARDUPLOADER_URL_RE.test(location.href)) {
    renderCardUploaderPanel();
  } else if (CARDVECTOR_URL_RE.test(location.href)) {
    renderCardVectorPanel();
  }
})();
