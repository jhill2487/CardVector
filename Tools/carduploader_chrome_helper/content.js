(() => {
  const CARDUPLOADER_URL_RE = /^https:\/\/carduploader\.com\/dashboard\/inventory\/automatic(?:[/?#]|$)/i;
  const CARDVECTOR_URL_RE = /^https:\/\/cardvector\.app\/operator\/repricing(?:[/?#]|$)/i;
  const STORAGE_KEY = "cardvector.latestCardUploaderAutomaticInventorySnapshot.v1";
  const PAGE_STORAGE_KEY = "cardvector.carduploaderAutomaticInventorySnapshot.v1";
  const SNAPSHOT_SOURCE = "carduploader_automatic_inventory_page_snapshot";
  const PANEL_ID = "cardvector-carduploader-helper";
  const HELPER_VERSION = "0.3.7";
  const SCROLL_SCAN_STEPS = 28;
  const SCROLL_SETTLE_MS = 350;
  const PAGE_SCAN_MAX_PAGES = 25;
  const PAGE_CHANGE_WAIT_MS = 300;
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

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
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

  function cellEvidence(cell) {
    const links = Array.from(cell.querySelectorAll("a[href]")).map((link) => ({
      text: clean(link.innerText || link.getAttribute("aria-label"), 160),
      href: link.href || ""
    })).filter((link) => link.text || link.href);
    const imageAlts = Array.from(cell.querySelectorAll("img")).map((image) => clean(image.getAttribute("alt"), 160)).filter(Boolean);
    return {
      text: clean(cell.innerText, 500),
      title: clean(cell.getAttribute("title"), 240),
      aria_label: clean(cell.getAttribute("aria-label"), 240),
      image_alt_text: imageAlts,
      links
    };
  }

  function rowActionEvidence(row) {
    return Array.from(row.querySelectorAll("button, a, [role='button']"))
      .filter(isVisible)
      .map((element) => clean(element.innerText || element.getAttribute("aria-label") || element.getAttribute("title"), 140))
      .filter(Boolean);
  }

  function rowEvidenceText(rawText, cellDetails, actionLabels) {
    return [
      rawText,
      ...cellDetails.flatMap((cell) => [
        cell.text,
        cell.title,
        cell.aria_label,
        ...(cell.image_alt_text || []),
        ...(cell.links || []).map((link) => link.text)
      ]),
      ...(actionLabels || [])
    ].filter(Boolean).join(" ");
  }

  function normalizedIdentityPart(value) {
    return clean(value, 220).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function automaticInventoryPageSignature(rows = scanAutomaticInventoryRows()) {
    const identities = rows.map(automaticInventoryRowIdentity).filter(Boolean);
    return [
      identities.length,
      identities.slice(0, 5).join("~"),
      identities.slice(-5).join("~")
    ].join("|");
  }

  function automaticInventoryRowIdentity(row) {
    return [
      row.catalog_sku,
      row.user_sku,
      row.location,
      row.title,
      row.current_price,
      row.quantity
    ].map(normalizedIdentityPart).filter(Boolean).join("|") || normalizedIdentityPart(row.raw_text || row.evidence_text || "");
  }

  function mergeRowEvidence(existing, incoming) {
    const merged = { ...existing, ...incoming };
    merged.raw_text = clean([existing.raw_text, incoming.raw_text].filter(Boolean).sort((a, b) => b.length - a.length)[0], 1600);
    merged.evidence_text = clean([existing.evidence_text, incoming.evidence_text].filter(Boolean).join(" "), 2400);
    merged.action_labels = Array.from(new Set([...(existing.action_labels || []), ...(incoming.action_labels || [])]));
    merged.links = Array.from(new Map([...(existing.links || []), ...(incoming.links || [])].map((link) => [link.href || link.text, link])).values());
    merged.cell_details = incoming.cell_details && incoming.cell_details.length >= (existing.cell_details || []).length
      ? incoming.cell_details
      : existing.cell_details;
    return merged;
  }

  function dedupeAutomaticInventoryRows(rows) {
    const byIdentity = new Map();
    rows.forEach((row) => {
      const identity = automaticInventoryRowIdentity(row);
      if (!identity) {
        return;
      }
      byIdentity.set(identity, byIdentity.has(identity) ? mergeRowEvidence(byIdentity.get(identity), row) : row);
    });
    return Array.from(byIdentity.values()).map((row, index) => ({
      ...row,
      row_number: index + 1,
      row_key: row.row_key || automaticInventoryRowIdentity(row) || `row-${index + 1}`
    }));
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

  function marketplaceTabCandidates() {
    return Array.from(document.querySelectorAll("button, a, [role='tab'], [role='button'], div, span"))
      .filter(isVisible)
      .map((element) => ({ element, label: controlText(element) || clean(element.innerText || element.textContent, 120).toLowerCase() }))
      .filter((candidate) => /^(ebay|mana pool|manapool)$/.test(candidate.label));
  }

  function hasUnderlineSignal(element) {
    const elements = [element, element.parentElement].filter(Boolean);
    return elements.some((candidate) => {
      const style = window.getComputedStyle(candidate);
      const after = window.getComputedStyle(candidate, "::after");
      return Number.parseFloat(style.borderBottomWidth || "0") > 1
        || Number.parseFloat(after.borderBottomWidth || "0") > 1
        || Number.parseFloat(after.height || "0") > 1;
    });
  }

  function isActiveMarketplaceCandidate(element) {
    return element.getAttribute("aria-selected") === "true"
      || element.getAttribute("data-state") === "active"
      || element.getAttribute("aria-current") === "page"
      || /\b(active|selected|current)\b/i.test(element.className || "")
      || hasUnderlineSignal(element);
  }

  function detectActiveMarketplaceTab() {
    const controls = marketplaceTabCandidates();
    const activeCandidate = controls.find(({ element }) => isActiveMarketplaceCandidate(element));
    if (activeCandidate && /\bmana ?pool\b/.test(activeCandidate.label)) {
      return "manapool";
    }
    if (activeCandidate && /\bebay\b/.test(activeCandidate.label)) {
      return "ebay";
    }
    const hasEbay = controls.some((candidate) => /\bebay\b/.test(candidate.label));
    const hasManapool = controls.some((candidate) => /\bmana ?pool\b/.test(candidate.label));
    const manapoolCandidate = controls.find((candidate) => /\bmana ?pool\b/.test(candidate.label));
    if (manapoolCandidate && isActiveMarketplaceCandidate(manapoolCandidate.element)) {
      return "manapool";
    }
    if (hasEbay) {
      return "ebay";
    }
    if (CARDUPLOADER_URL_RE.test(location.href)) {
      return "ebay";
    }
    return "unknown";
  }

  function platformHasEbay(value) {
    return /\bebay\b/i.test(value || "");
  }

  function platformHasManapool(value) {
    return /\bmana\s*pool\b/i.test(value || "") || /\bmanapool\b/i.test(value || "");
  }

  function rowsContainManapoolOnlyEvidence(rows) {
    return Array.isArray(rows) && rows.some((row) => (
      platformHasManapool(row.platform) && !platformHasEbay(row.platform)
    ));
  }

  function canScanForEbayPriceReview(rows = []) {
    return detectActiveMarketplaceTab() !== "manapool";
  }

  function scanAutomaticInventoryRows() {
    const rows = [];
    Array.from(document.querySelectorAll("table")).forEach((table) => {
      const headers = Array.from(table.querySelectorAll("th")).map((cell) => clean(cell.innerText, 120));
      if (!looksLikeAutomaticInventoryHeaders(headers)) {
        return;
      }
      Array.from(table.querySelectorAll("tbody tr, tr")).forEach((row) => {
        const cellElements = Array.from(row.querySelectorAll("td, th"));
        const cells = cellElements.map((cell) => clean(cell.innerText, 400));
        const cellDetails = cellElements.map(cellEvidence);
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
        const actionLabels = rowActionEvidence(row);
        const links = cellDetails.flatMap((cell) => cell.links || []);
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
          action_labels: actionLabels,
          links,
          cell_details: cellDetails,
          evidence_text: clean(rowEvidenceText(rawText, cellDetails, actionLabels), 2400),
          raw_text: rawText
        });
      });
    });
    return dedupeAutomaticInventoryRows(rows);
  }

  function scrollableElements() {
    return Array.from(document.querySelectorAll("main, [role='main'], section, article, div"))
      .filter((element) => {
        if (!isVisible(element)) {
          return false;
        }
        const style = window.getComputedStyle(element);
        return /(auto|scroll)/.test(`${style.overflowY} ${style.overflow}`) && element.scrollHeight > element.clientHeight + 80;
      })
      .slice(0, 8);
  }

  function scrollInventoryViewport() {
    let moved = false;
    const beforeWindow = window.scrollY;
    window.scrollBy({ top: Math.max(360, Math.round(window.innerHeight * 0.8)), behavior: "auto" });
    moved = moved || window.scrollY !== beforeWindow;
    scrollableElements().forEach((element) => {
      const before = element.scrollTop;
      element.scrollTop = Math.min(element.scrollHeight, element.scrollTop + Math.max(320, Math.round(element.clientHeight * 0.85)));
      moved = moved || element.scrollTop !== before;
    });
    return moved;
  }

  function controlText(element) {
    return clean([
      element.innerText,
      element.value,
      element.getAttribute("aria-label"),
      element.getAttribute("title"),
      element.getAttribute("rel")
    ].filter(Boolean).join(" "), 240).toLowerCase();
  }

  function isDisabledControl(element) {
    return element.disabled
      || element.getAttribute("aria-disabled") === "true"
      || element.getAttribute("disabled") !== null
      || /\b(disabled|inactive)\b/i.test(element.className || "");
  }

  function isInsideInventoryRow(element) {
    return Boolean(element.closest("tbody tr"));
  }

  function isMarketplaceTabControl(element) {
    return /^(ebay|mana pool|manapool)$/.test(controlText(element));
  }

  function isBlockedPaginationControl(element) {
    if (!element || !isVisible(element) || isDisabledControl(element) || isInsideInventoryRow(element) || isMarketplaceTabControl(element)) {
      return true;
    }
    const label = controlText(element);
    return /\b(mark|sold|listed|platform|batch|delete|edit|save|apply|submit|remove)\b/.test(label);
  }

  function isSafeNextPageControl(element) {
    if (isBlockedPaginationControl(element)) {
      return false;
    }
    const label = controlText(element);
    return element.getAttribute("rel") === "next"
      || /\b(next|next page|go to next)\b/.test(label)
      || /^[›»>]$/.test(label);
  }

  function pageTextRect(pageTextElement) {
    const walker = document.createTreeWalker(pageTextElement, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
      const text = node.nodeValue || "";
      const match = text.match(/\bpage\s+[0-9]+\s+of\s+[0-9]+\b/i);
      if (match) {
        const range = document.createRange();
        const start = text.indexOf(match[0]);
        range.setStart(node, start);
        range.setEnd(node, start + match[0].length);
        const rect = range.getBoundingClientRect();
        range.detach();
        if (rect.width > 0 && rect.height > 0) {
          return rect;
        }
      }
      node = walker.nextNode();
    }
    return pageTextElement.getBoundingClientRect();
  }

  function isNearPageTextNextControl(control, pageTextElement) {
    if (isBlockedPaginationControl(control)) {
      return false;
    }
    const label = controlText(control);
    const looksLikeNext = control.getAttribute("rel") === "next"
      || /\b(next|next page|go to next)\b/.test(label)
      || /^[›»>]$/.test(label);
    const isIconOnly = !label && Boolean(control.querySelector("svg, img"));
    const pageRect = pageTextRect(pageTextElement);
    const controlRect = control.getBoundingClientRect();
    const pageCenterY = (pageRect.top + pageRect.bottom) / 2;
    const controlCenterY = (controlRect.top + controlRect.bottom) / 2;
    const verticalDistance = Math.abs(controlCenterY - pageCenterY);
    return controlRect.left >= pageRect.right - 8
      && verticalDistance <= Math.max(36, pageRect.height * 2)
      && (looksLikeNext || isIconOnly);
  }

  function pageInfoFromText(text, includeComplete = false) {
    const match = clean(text, 160).match(/\bpage\s+([0-9]+)\s+of\s+([0-9]+)\b/i);
    if (!match) {
      return null;
    }
    const current = Number.parseInt(match[1], 10);
    const total = Number.parseInt(match[2], 10);
    if (!Number.isFinite(current) || !Number.isFinite(total) || (!includeComplete && current >= total)) {
      return null;
    }
    return { current, total };
  }

  function paginationTextContainers(includeComplete = false) {
    return Array.from(document.querySelectorAll("nav, [role='navigation'], [aria-label*='pagination' i], [class*='pagination' i], [class*='pager' i], div, span, p"))
      .filter(isVisible)
      .map((element) => ({
        element,
        info: pageInfoFromText(element.innerText || element.textContent || "", includeComplete)
      }))
      .filter((candidate) => candidate.info);
  }

  function currentPaginationInfo() {
    const candidates = paginationTextContainers(true)
      .map((candidate) => ({
        ...candidate,
        textLength: clean(candidate.element.innerText || candidate.element.textContent || "", 240).length
      }))
      .sort((a, b) => a.textLength - b.textLength);
    return candidates.length ? candidates[0].info : null;
  }

  function paginationContainerFor(element) {
    let current = element;
    for (let depth = 0; current && depth < 4; depth += 1) {
      const controls = Array.from(current.querySelectorAll("button, a[href], [role='button']")).filter((control) => (
        control !== element
        && isVisible(control)
        && !isDisabledControl(control)
        && !isInsideInventoryRow(control)
      ));
      if (controls.length) {
        return { container: current, controls };
      }
      current = current.parentElement;
    }
    return { container: element, controls: [] };
  }

  function findPageTextNextControl() {
    for (const candidate of paginationTextContainers()) {
      const { controls } = paginationContainerFor(candidate.element);
      const safeControls = controls.filter((control) => isNearPageTextNextControl(control, candidate.element));
      if (!safeControls.length) {
        continue;
      }
      return safeControls
        .map((control) => ({ control, rect: control.getBoundingClientRect() }))
        .sort((a, b) => b.rect.left - a.rect.left)[0].control;
    }
    return null;
  }

  function findNextPageControl() {
    const pageTextControl = findPageTextNextControl();
    if (pageTextControl) {
      return pageTextControl;
    }
    return null;
  }

  async function waitForInventoryPageChange(previousSignature, previousPageInfo = null) {
    for (let attempt = 0; attempt < 40; attempt += 1) {
      await delay(PAGE_CHANGE_WAIT_MS);
      const currentPageInfo = currentPaginationInfo();
      if (previousPageInfo && currentPageInfo && currentPageInfo.total === previousPageInfo.total && currentPageInfo.current !== previousPageInfo.current) {
        return true;
      }
      const currentSignature = automaticInventoryPageSignature();
      if (currentSignature && currentSignature !== previousSignature) {
        return true;
      }
    }
    return false;
  }

  async function safeClickNextPageControl(updateStatus = () => {}) {
    const next = findNextPageControl();
    if (!next) {
      return false;
    }
    const before = automaticInventoryPageSignature();
    const beforePageInfo = currentPaginationInfo();
    updateStatus("Moving to the next Automatic Inventory page...");
    next.scrollIntoView({ behavior: "auto", block: "center" });
    await delay(100);
    next.click();
    return waitForInventoryPageChange(before, beforePageInfo);
  }

  async function scanLoadedAutomaticInventoryRows() {
    return scanAutomaticInventoryRows();
  }

  async function scanScrollableAutomaticInventoryRows(updateStatus = () => {}) {
    const collected = [];
    for (let step = 0; step < SCROLL_SCAN_STEPS; step += 1) {
      collected.push(...scanAutomaticInventoryRows());
      const deduped = dedupeAutomaticInventoryRows(collected);
      updateStatus(`Scanning loaded inventory rows... ${deduped.length} unique rows found.`);
      const moved = scrollInventoryViewport();
      if (!moved) {
        break;
      }
      await delay(SCROLL_SETTLE_MS);
    }
    collected.push(...scanAutomaticInventoryRows());
    return dedupeAutomaticInventoryRows(collected);
  }

  async function scanPaginatedAutomaticInventoryRows(updateStatus = () => {}) {
    const collected = [];
    let pagesScanned = 0;
    for (let page = 1; page <= PAGE_SCAN_MAX_PAGES; page += 1) {
      const pageRows = await scanScrollableAutomaticInventoryRows((status) => updateStatus(`Page ${page}: ${status}`));
      collected.push(...pageRows);
      pagesScanned = page;
      const unique = dedupeAutomaticInventoryRows(collected);
      updateStatus(`Scanned page ${page}. ${unique.length} unique rows collected.`);
      const moved = await safeClickNextPageControl(updateStatus);
      if (!moved) {
        return { rows: unique, page_count: pagesScanned, reached_end: true };
      }
    }
    return { rows: dedupeAutomaticInventoryRows(collected), page_count: pagesScanned, reached_end: false };
  }

  function buildSnapshot(rows, scanMode = "loaded_rows", scanMeta = {}) {
    const activeMarketplaceTab = detectActiveMarketplaceTab();
    return {
      source: SNAPSHOT_SOURCE,
      url: location.href,
      title: document.title || "CardUploader automatic inventory",
      captured_at: new Date().toISOString(),
      active_marketplace_tab: activeMarketplaceTab,
      scan_mode: scanMode,
      scan_meta: scanMeta,
      page_count: scanMeta.page_count || 1,
      row_count: Array.isArray(rows) ? rows.length : 0,
      controls: visibleControls(),
      editable_controls: visibleEditableControls(),
      rows: Array.isArray(rows) ? rows : []
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

  function renderCardUploaderPanel(message = "Ready to scan CardUploader automatic-inventory rows.") {
    const panel = panelShell("CardVector Helper");
    const body = panel.querySelector("[data-cv-helper-body]");
    const activeMarketplaceTab = detectActiveMarketplaceTab();
    const scanBlocked = activeMarketplaceTab === "manapool";
    const scanDisabled = scanBlocked ? " disabled" : "";
    body.innerHTML = `
      <p class="cardvector-helper-status">${scanBlocked ? "Switch to the eBay tab before scanning for CardVector price review. Manapool pricing changes are intentionally out of scope." : message}</p>
      <div class="cardvector-helper-actions">
        <button class="primary" type="button" data-cv-scan-loaded${scanDisabled}>Scan Loaded Rows</button>
        <button type="button" data-cv-scan-scroll${scanDisabled}>Scroll & Scan Page</button>
        <button type="button" data-cv-scan-pages${scanDisabled}>Scan All Pages</button>
        <button type="button" data-cv-open-review>Open Review</button>
      </div>
      <div class="cardvector-helper-meta" data-cv-meta>
        <span>Active Tab</span>
        <strong>${activeMarketplaceTab}</strong>
        <span>Helper Version</span>
        <strong>${HELPER_VERSION}</strong>
        <span>Snapshot</span>
        <strong>Not scanned</strong>
        <span>Read-only. No prices are edited. Row action menus are not clicked.</span>
      </div>
    `;
    const completeScan = async (rows, scanMode, scanMeta = {}) => {
      if (!canScanForEbayPriceReview(rows) || rowsContainManapoolOnlyEvidence(rows)) {
        body.querySelector(".cardvector-helper-status").textContent = "Scan blocked. Switch to the eBay tab before preparing price-review recommendations.";
        return;
      }
      const snapshot = buildSnapshot(rows, scanMode, scanMeta);
      await saveSnapshot(snapshot);
      body.querySelector("[data-cv-meta]").innerHTML = `
        <span>Snapshot</span>
        <strong>${snapshot.rows.length} rows</strong>
        <span>${snapshot.scan_mode} captured ${snapshot.captured_at}${snapshot.page_count ? ` across ${snapshot.page_count} page(s)` : ""}</span>
      `;
      body.querySelector(".cardvector-helper-status").textContent = "Snapshot saved locally for CardVector.app review.";
    };
    body.querySelector("[data-cv-scan-loaded]").addEventListener("click", async () => {
      const rows = await scanLoadedAutomaticInventoryRows();
      await completeScan(rows, "loaded_rows");
    });
    body.querySelector("[data-cv-scan-scroll]").addEventListener("click", async () => {
      body.querySelector(".cardvector-helper-status").textContent = "Scanning loaded rows while scrolling. This remains read-only.";
      const rows = await scanScrollableAutomaticInventoryRows((status) => {
        body.querySelector(".cardvector-helper-status").textContent = status;
      });
      await completeScan(rows, "scroll_scan_loaded_rows");
    });
    body.querySelector("[data-cv-scan-pages]").addEventListener("click", async () => {
      body.querySelector(".cardvector-helper-status").textContent = "Scanning all Automatic Inventory pages. Only the pagination Next control is clicked.";
      const result = await scanPaginatedAutomaticInventoryRows((status) => {
        body.querySelector(".cardvector-helper-status").textContent = status;
      });
      await completeScan(result.rows, "paginated_scan", {
        page_count: result.page_count,
        reached_end: result.reached_end
      });
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
