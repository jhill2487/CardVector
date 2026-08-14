(() => {
  const CARDUPLOADER_URL_RE = /^https:\/\/carduploader\.com\/dashboard\/inventory\/automatic(?:[/?#]|$)/i;
  const CARDVECTOR_URL_RE = /^https:\/\/cardvector\.app\/operator\/repricing(?:[/?#]|$)/i;
  const STORAGE_KEY = "cardvector.latestCardUploaderAutomaticInventorySnapshot.v1";
  const PAGE_STORAGE_KEY = "cardvector.carduploaderAutomaticInventorySnapshot.v1";
  const SNAPSHOT_SOURCE = "carduploader_automatic_inventory_page_snapshot";
  const PANEL_ID = "cardvector-carduploader-helper";
  const HELPER_VERSION = "0.3.14";
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
    "tcg",
    "game",
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

  function automaticInventoryGameLabel(value) {
    const text = clean(value, 220).toLowerCase().replace(/pok\u00e9/g, "poke").replace(/[^a-z0-9]+/g, " ").trim();
    if (!text || /^(ebay|mana pool|manapool|ebay mana pool)$/.test(text)) {
      return "";
    }
    if (/\b(pokemon|poke mon)\b/.test(text)) {
      return "Pokemon";
    }
    if (/\b(mtg|magic|magic the gathering)\b/.test(text)) {
      return "Magic";
    }
    if (/\b(yugioh|yu gi oh)\b/.test(text)) {
      return "Yu-Gi-Oh";
    }
    if (/\blorcana\b/.test(text)) {
      return "Lorcana";
    }
    if (/\bone piece\b/.test(text)) {
      return "One Piece";
    }
    return "";
  }

  function automaticInventoryGameFromRow(mapped, cells) {
    const explicit = automaticInventoryGameLabel(mapped.tcg || mapped.game || mapped["tcg game"] || mapped["game tcg"]);
    if (explicit) {
      return explicit;
    }
    return (cells || [])
      .filter((cell) => !platformHasEbay(cell) && !platformHasManapool(cell))
      .map(automaticInventoryGameLabel)
      .find(Boolean) || "";
  }

  function rowsContainManapoolOnlyEvidence(rows) {
    return Array.isArray(rows) && rows.some((row) => (
      platformHasManapool(row.platform) && !platformHasEbay(row.platform)
    ));
  }

  function canScanForEbayPriceReview(rows = []) {
    return detectActiveMarketplaceTab() !== "manapool";
  }

  function scanContextNote(activeMarketplaceTab, rows = []) {
    if (activeMarketplaceTab === "manapool") {
      return " Active tab appears to be Mana Pool; snapshot is still read-only and will include platform evidence for review.";
    }
    if (rowsContainManapoolOnlyEvidence(rows)) {
      return " Some rows appear Mana Pool-only; snapshot is still saved read-only and can be filtered during review.";
    }
    return "";
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
        const tcg = automaticInventoryGameFromRow(mapped, cells);
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
          tcg,
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
    const disabledClassTokens = String(element.className || "")
      .split(/\s+/)
      .filter(Boolean)
      .filter((token) => !token.includes(":"));
    return element.disabled
      || element.getAttribute("aria-disabled") === "true"
      || element.getAttribute("disabled") !== null
      || disabledClassTokens.some((token) => /^(disabled|inactive|is-disabled|is-inactive)$/i.test(token));
  }

  function isInsideInventoryRow(element) {
    return Boolean(element.closest("tbody tr"));
  }

  function isMarketplaceTabControl(element) {
    return /^(ebay|mana pool|manapool)$/.test(controlText(element));
  }

  function closestClickableElement(element) {
    return element.closest("button, a[href], [role='button'], [tabindex]") || element;
  }

  function ancestorElements(element, maxDepth = 6) {
    const ancestors = [];
    let current = element;
    for (let depth = 0; current && depth < maxDepth; depth += 1) {
      ancestors.push(current);
      current = current.parentElement;
    }
    return ancestors;
  }

  function isLikelyClickableElement(element) {
    if (!element || !isVisible(element)) {
      return false;
    }
    const tag = (element.tagName || "").toLowerCase();
    const role = (element.getAttribute("role") || "").toLowerCase();
    const className = String(element.className || "");
    const style = window.getComputedStyle(element);
    return tag === "button"
      || tag === "a"
      || role === "button"
      || element.getAttribute("tabindex") !== null
      || style.cursor === "pointer"
      || /\b(button|btn|clickable|cursor-pointer)\b/i.test(className);
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
    const tag = (control.tagName || "").toLowerCase();
    const hasIcon = tag === "svg" || tag === "img" || Boolean(control.querySelector("svg, img"));
    const isIconOnly = !label && hasIcon;
    const pageRect = pageTextRect(pageTextElement);
    const controlRect = control.getBoundingClientRect();
    const pageCenterY = (pageRect.top + pageRect.bottom) / 2;
    const controlCenterY = (controlRect.top + controlRect.bottom) / 2;
    const verticalDistance = Math.abs(controlCenterY - pageCenterY);
    const horizontalDistance = controlRect.left - pageRect.right;
    const compactIconControl = controlRect.width <= 96 && controlRect.height <= 96;
    return controlRect.left >= pageRect.right - 8
      && horizontalDistance <= 180
      && verticalDistance <= Math.max(36, pageRect.height * 2)
      && (looksLikeNext || (isIconOnly && compactIconControl && isLikelyClickableElement(control)));
  }

  function isCoordinatePaginationCandidate(control, pageTextElement) {
    if (isBlockedPaginationControl(control)) {
      return false;
    }
    const pageRect = pageTextRect(pageTextElement);
    const controlRect = control.getBoundingClientRect();
    const pageCenterY = (pageRect.top + pageRect.bottom) / 2;
    const controlCenterY = (controlRect.top + controlRect.bottom) / 2;
    const verticalDistance = Math.abs(controlCenterY - pageCenterY);
    const horizontalDistance = controlRect.left - pageRect.right;
    return controlRect.left >= pageRect.right - 8
      && horizontalDistance <= 180
      && verticalDistance <= Math.max(40, pageRect.height * 2.5)
      && controlRect.width <= 120
      && controlRect.height <= 120;
  }

  function paginationControlsFromPoint(pageTextElement) {
    const pageRect = pageTextRect(pageTextElement);
    const yOffsets = [0, -8, 8, -16, 16];
    const xOffsets = [8, 16, 24, 32, 44, 56, 72, 96, 128, 160];
    const seen = new Set();
    const controls = [];
    yOffsets.forEach((yOffset) => {
      xOffsets.forEach((xOffset) => {
        const x = Math.min(window.innerWidth - 1, pageRect.right + xOffset);
        const y = Math.max(0, Math.min(window.innerHeight - 1, (pageRect.top + pageRect.bottom) / 2 + yOffset));
        document.elementsFromPoint(x, y).forEach((element) => {
          ancestorElements(closestClickableElement(element)).forEach((candidate) => {
            if (seen.has(candidate)) {
              return;
            }
            seen.add(candidate);
            if (isCoordinatePaginationCandidate(candidate, pageTextElement)) {
              controls.push(candidate);
            }
          });
        });
      });
    });
    return controls
      .map((control) => {
        const controlRect = control.getBoundingClientRect();
        return { control, distance: Math.abs(controlRect.left - pageRect.right) };
      })
      .sort((a, b) => a.distance - b.distance)
      .map((candidate) => candidate.control);
  }

  function paginationControlsNearPageText(pageTextElement) {
    const seen = new Set();
    const queriedControls = Array.from(document.querySelectorAll("button, a[href], [role='button'], [tabindex], svg, img, div, span"))
      .map((element) => closestClickableElement(element))
      .filter((element) => {
        if (seen.has(element)) {
          return false;
        }
        seen.add(element);
        return true;
      })
      .filter((control) => isNearPageTextNextControl(control, pageTextElement))
      .map((control) => {
        const pageRect = pageTextRect(pageTextElement);
        const controlRect = control.getBoundingClientRect();
        return { control, distance: Math.abs(controlRect.left - pageRect.right) };
      })
      .sort((a, b) => a.distance - b.distance)
      .map((candidate) => candidate.control);
    return queriedControls.length ? queriedControls : paginationControlsFromPoint(pageTextElement);
  }

  function rectSummary(element) {
    if (!element || !element.getBoundingClientRect) {
      return null;
    }
    const rect = element.getBoundingClientRect();
    return {
      left: Math.round(rect.left),
      top: Math.round(rect.top),
      right: Math.round(rect.right),
      bottom: Math.round(rect.bottom),
      width: Math.round(rect.width),
      height: Math.round(rect.height)
    };
  }

  function elementSummary(element, pageTextElement = null) {
    if (!element) {
      return null;
    }
    const className = String(element.className || "");
    return {
      tag: (element.tagName || "").toLowerCase(),
      text: controlText(element),
      aria_label: clean(element.getAttribute("aria-label"), 160),
      title: clean(element.getAttribute("title"), 160),
      role: clean(element.getAttribute("role"), 80),
      rel: clean(element.getAttribute("rel"), 80),
      disabled: isDisabledControl(element),
      marketplace_tab: isMarketplaceTabControl(element),
      likely_clickable: isLikelyClickableElement(element),
      safe_next: isSafeNextPageControl(element),
      near_page_text_next: pageTextElement ? isNearPageTextNextControl(element, pageTextElement) : false,
      coordinate_candidate: pageTextElement ? isCoordinatePaginationCandidate(element, pageTextElement) : false,
      class_name: clean(className, 220),
      rect: rectSummary(element)
    };
  }

  function paginationProbeElements(pageTextElement) {
    const pageRect = pageTextRect(pageTextElement);
    const seen = new Set();
    const probes = [];
    [8, 16, 24, 32, 44, 56, 72, 96, 128, 160].forEach((xOffset) => {
      const x = Math.min(window.innerWidth - 1, pageRect.right + xOffset);
      const y = Math.max(0, Math.min(window.innerHeight - 1, (pageRect.top + pageRect.bottom) / 2));
      document.elementsFromPoint(x, y).forEach((element) => {
        ancestorElements(closestClickableElement(element)).forEach((candidate) => {
          if (seen.has(candidate)) {
            return;
          }
          seen.add(candidate);
          probes.push({
            x_offset: xOffset,
            element: elementSummary(candidate, pageTextElement)
          });
        });
      });
    });
    return probes.slice(0, 40);
  }

  function paginationDiagnosticReport() {
    const pageContainers = paginationTextContainers(true);
    return {
      helper_version: HELPER_VERSION,
      url: location.href,
      active_marketplace_tab: detectActiveMarketplaceTab(),
      page_info: currentPaginationInfo(),
      page_container_count: pageContainers.length,
      selected_next_control: elementSummary(findNextPageControl()),
      page_containers: pageContainers.slice(0, 6).map((candidate) => ({
        text: clean(candidate.element.innerText || candidate.element.textContent, 240),
        info: candidate.info,
        rect: rectSummary(candidate.element),
        page_text_rect: rectSummary({ getBoundingClientRect: () => pageTextRect(candidate.element) }),
        near_controls: paginationControlsNearPageText(candidate.element).slice(0, 8).map((control) => elementSummary(control, candidate.element)),
        probe_elements: paginationProbeElements(candidate.element)
      }))
    };
  }

  async function copyTextToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "readonly");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.documentElement.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    return copied;
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
      const safeControls = paginationControlsNearPageText(candidate.element);
      if (!safeControls.length) {
        continue;
      }
      return safeControls[0];
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
    const contextMessage = activeMarketplaceTab === "manapool"
      ? "Active tab appears to be Mana Pool. Scans remain read-only; use the eBay tab for eBay price review snapshots."
      : message;
    body.innerHTML = `
      <p class="cardvector-helper-status">${contextMessage}</p>
      <div class="cardvector-helper-actions">
        <button class="primary" type="button" data-cv-scan-loaded>Scan Loaded Rows</button>
        <button type="button" data-cv-scan-scroll>Scroll & Scan Page</button>
        <button type="button" data-cv-scan-pages>Scan All Pages</button>
        <button type="button" data-cv-diagnose-pagination>Diagnose Pagination</button>
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
      const snapshot = buildSnapshot(rows, scanMode, scanMeta);
      await saveSnapshot(snapshot);
      body.querySelector("[data-cv-meta]").innerHTML = `
        <span>Snapshot</span>
        <strong>${snapshot.rows.length} rows</strong>
        <span>${snapshot.scan_mode} captured ${snapshot.captured_at}${snapshot.page_count ? ` across ${snapshot.page_count} page(s)` : ""}</span>
      `;
      body.querySelector(".cardvector-helper-status").textContent = `Snapshot saved locally for CardVector.app review.${scanContextNote(snapshot.active_marketplace_tab, snapshot.rows)}`;
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
    body.querySelector("[data-cv-diagnose-pagination]").addEventListener("click", async () => {
      const report = paginationDiagnosticReport();
      const text = JSON.stringify(report, null, 2);
      await copyTextToClipboard(text);
      body.querySelector(".cardvector-helper-status").textContent = `Pagination diagnostic copied. Found ${report.page_container_count} page counter candidate(s); next control ${report.selected_next_control ? "was detected" : "was not detected"}.`;
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
