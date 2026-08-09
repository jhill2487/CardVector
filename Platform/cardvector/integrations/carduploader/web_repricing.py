from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from .price_updates import (
    CardUploaderPriceUpdateError,
    CardUploaderPriceUpdatePlan,
    parse_money,
    percent_delta,
)


CARDUPLOADER_AUTOMATIC_INVENTORY_URL = "https://carduploader.com/dashboard/inventory/automatic"
SAVE_MODE_MANUAL = "manual_save"
SAVE_MODE_AUTOSAVE = "autosave"
SAVE_MODE_UNKNOWN = "unknown"


CARDUPLOADER_AUTOMATIC_INVENTORY_HEADERS = {
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
    "added",
}


@dataclass(frozen=True)
class CardUploaderWebInventoryRow:
    """Visible CardUploader automatic-inventory row captured from the browser."""

    row_key: str
    title: str = ""
    current_price: Decimal = Decimal("0.00")
    quantity: int = 0
    inventory_id: str = ""
    catalog_sku: str = ""
    user_sku: str = ""
    price_input_selector: str = ""
    raw_text: str = ""

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "CardUploaderWebInventoryRow":
        return cls(
            row_key=str(row.get("row_key") or row.get("id") or "").strip(),
            title=str(row.get("title") or "").strip(),
            current_price=parse_money(row.get("current_price") or row.get("price")),
            quantity=_int(row.get("quantity") or row.get("qty")),
            inventory_id=str(row.get("inventory_id") or row.get("CardUploader ID") or "").strip(),
            catalog_sku=str(row.get("catalog_sku") or row.get("Catalog SKU") or "").strip(),
            user_sku=str(row.get("user_sku") or row.get("User SKU") or row.get("sku") or "").strip(),
            price_input_selector=str(row.get("price_input_selector") or "").strip(),
            raw_text=str(row.get("raw_text") or "").strip(),
        )


@dataclass(frozen=True)
class CardUploaderWebPageSnapshot:
    """Non-destructive browser snapshot metadata for CardUploader repricing."""

    url: str
    rows: tuple[CardUploaderWebInventoryRow, ...]
    save_mode: str = SAVE_MODE_UNKNOWN
    captured_at: str = ""
    operator_note: str = ""

    @property
    def is_automatic_inventory_page(self) -> bool:
        return self.url.rstrip("/") == CARDUPLOADER_AUTOMATIC_INVENTORY_URL.rstrip("/")


@dataclass(frozen=True)
class CardUploaderWebSafetyPolicy:
    """Safety gates for browser-assisted CardUploader price edits."""

    max_rows_per_apply: int = 25
    max_percent_move: Decimal = Decimal("25.00")
    allow_autosave: bool = False
    require_known_save_mode: bool = True
    require_explicit_live_sync_confirmation: bool = True
    require_price_input_selector: bool = True


@dataclass(frozen=True)
class CardUploaderWebPriceEdit:
    """A proposed browser edit tied to one visible CardUploader row."""

    row_key: str
    inventory_id: str
    title: str
    current_price: Decimal
    recommended_price: Decimal
    price_delta: Decimal
    percent_delta: Decimal
    approved: bool
    price_input_selector: str = ""
    source_plan_status: str = ""
    safety_notes: tuple[str, ...] = ()

    @property
    def is_apply_ready(self) -> bool:
        return self.approved and not self.safety_notes


def _int(value: Any) -> int:
    try:
        return max(0, int(float(str(value or "0").replace(",", ""))))
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalized_header(value: Any) -> str:
    return _text(value).lower()


def carduploader_inventory_snapshot_script() -> str:
    """Return read-only browser JavaScript for CardUploader inventory snapshots."""

    return r"""
(() => {
  const clean = (text, max = 400) => String(text || '').replace(/\s+/g, ' ').trim().slice(0, max);
  const attr = (el, name) => el.getAttribute(name) || '';
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
  };
  const selectorFor = (el) => {
    if (!el) return '';
    if (el.id) return `#${CSS.escape(el.id)}`;
    const name = attr(el, 'name');
    if (name) return `${el.tagName.toLowerCase()}[name="${CSS.escape(name)}"]`;
    const dataAttr = Array.from(el.attributes || []).find((candidate) => candidate.name.startsWith('data-'));
    if (dataAttr) return `${el.tagName.toLowerCase()}[${dataAttr.name}="${CSS.escape(dataAttr.value)}"]`;
    return el.tagName.toLowerCase();
  };
  const controls = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a'))
    .filter(isVisible)
    .map((el) => ({
      text: clean(el.innerText || el.value, 100),
      aria_label: attr(el, 'aria-label'),
      selector: selectorFor(el),
    }));
  return {
    url: location.href,
    title: document.title,
    captured_at: new Date().toISOString(),
    controls,
    editable_controls: Array.from(document.querySelectorAll('input, textarea, [contenteditable="true"]'))
      .filter(isVisible)
      .map((el) => ({
        value: clean(el.value || el.textContent, 100),
        name: attr(el, 'name'),
        id: el.id || '',
        aria_label: attr(el, 'aria-label'),
        placeholder: attr(el, 'placeholder'),
        selector: selectorFor(el),
      })),
    tables: Array.from(document.querySelectorAll('table')).map((table, table_index) => ({
      table_index,
      headers: Array.from(table.querySelectorAll('th')).map((cell) => clean(cell.innerText, 100)),
      rows: Array.from(table.querySelectorAll('tbody tr, tr')).map((row, row_index) => ({
        row_index,
        text: clean(row.innerText, 800),
        cells: Array.from(row.querySelectorAll('td, th')).map((cell) => clean(cell.innerText, 300)),
      })),
    })),
  };
})()
""".strip()


def _looks_like_automatic_inventory_table(headers: Sequence[str]) -> bool:
    normalized = {_normalized_header(header) for header in headers}
    return len(normalized.intersection(CARDUPLOADER_AUTOMATIC_INVENTORY_HEADERS)) >= 7


def _mapped_cells(headers: Sequence[str], cells: Sequence[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for index, header in enumerate(headers):
        key = _normalized_header(header)
        if not key or index >= len(cells):
            continue
        mapped[key] = _text(cells[index])
    return mapped


def _detect_save_mode(payload: Mapping[str, Any]) -> str:
    controls = payload.get("controls") or ()
    control_text = " ".join(
        _text((control or {}).get("text") or (control or {}).get("aria_label"))
        for control in controls
        if isinstance(control, Mapping)
    ).lower()
    if "autosave" in control_text or "auto-save" in control_text:
        return SAVE_MODE_AUTOSAVE
    if any(word in control_text for word in ("save", "update", "apply")):
        return SAVE_MODE_MANUAL
    return SAVE_MODE_UNKNOWN


def normalize_carduploader_web_snapshot(payload: Mapping[str, Any]) -> CardUploaderWebPageSnapshot:
    """Normalize a read-only CardUploader browser payload into a page snapshot."""

    rows: list[CardUploaderWebInventoryRow] = []
    for table in payload.get("tables") or ():
        if not isinstance(table, Mapping):
            continue
        headers = tuple(_text(header) for header in table.get("headers") or ())
        if not _looks_like_automatic_inventory_table(headers):
            continue
        for row in table.get("rows") or ():
            if not isinstance(row, Mapping):
                continue
            cells = tuple(_text(cell) for cell in row.get("cells") or ())
            if not cells or cells == headers:
                continue
            mapped = _mapped_cells(headers, cells)
            catalog_sku = mapped.get("catalog sku", "")
            user_sku = mapped.get("user sku", "")
            title = mapped.get("card", "")
            row_index = _int(row.get("row_index"))
            row_key = catalog_sku or user_sku or f"row-{row_index}"
            rows.append(
                CardUploaderWebInventoryRow.from_mapping(
                    {
                        "row_key": row_key,
                        "title": title,
                        "current_price": mapped.get("price", ""),
                        "quantity": mapped.get("qty", ""),
                        "inventory_id": catalog_sku,
                        "catalog_sku": catalog_sku,
                        "user_sku": user_sku,
                        "raw_text": row.get("text", ""),
                    }
                )
            )
    note = ""
    if rows and not any(row.price_input_selector for row in rows):
        note = "Read-only table snapshot; CardUploader price inputs were not visible."
    return CardUploaderWebPageSnapshot(
        url=str(payload.get("url") or "").strip(),
        rows=tuple(rows),
        save_mode=_detect_save_mode(payload),
        captured_at=str(payload.get("captured_at") or "").strip(),
        operator_note=note,
    )


def _identity_values(*values: str) -> set[str]:
    return {str(value or "").strip().lower() for value in values if str(value or "").strip()}


def _match_row(
    rows: Iterable[CardUploaderWebInventoryRow],
    plan: CardUploaderPriceUpdatePlan,
) -> CardUploaderWebInventoryRow | None:
    plan_identities = _identity_values(
        plan.inventory_id,
        plan.catalog_sku,
        plan.user_sku,
        plan.tcgplayer_sku,
        plan.tcgplayer_product_id,
    )
    title = str(plan.title or "").strip().lower()
    for row in rows:
        row_identities = _identity_values(row.inventory_id, row.catalog_sku, row.user_sku)
        if plan_identities and plan_identities.intersection(row_identities):
            return row
        if title and title == row.title.strip().lower():
            return row
    return None


def build_web_price_edits(
    snapshot: CardUploaderWebPageSnapshot,
    plans: Iterable[CardUploaderPriceUpdatePlan],
    *,
    policy: CardUploaderWebSafetyPolicy | None = None,
) -> tuple[CardUploaderWebPriceEdit, ...]:
    """Create browser edit intents; this never writes to CardUploader."""

    active_policy = policy or CardUploaderWebSafetyPolicy()
    edits: list[CardUploaderWebPriceEdit] = []
    for plan in plans:
        row = _match_row(snapshot.rows, plan)
        notes: list[str] = []
        if row is None:
            notes.append("visible_carduploader_row_not_found")
            row = CardUploaderWebInventoryRow(row_key="", title=plan.title)
        if row.current_price != plan.current_price:
            notes.append("visible_price_does_not_match_plan")
        if active_policy.require_price_input_selector and not row.price_input_selector:
            notes.append("price_input_selector_missing")
        pct = percent_delta(row.current_price, plan.recommended_price)
        if row.current_price > 0 and abs(pct) > active_policy.max_percent_move:
            notes.append("exceeds_web_max_percent_move")
        edits.append(
            CardUploaderWebPriceEdit(
                row_key=row.row_key,
                inventory_id=plan.inventory_id,
                title=plan.title or row.title,
                current_price=row.current_price,
                recommended_price=plan.recommended_price,
                price_delta=(plan.recommended_price - row.current_price),
                percent_delta=pct,
                approved=plan.is_apply_ready,
                price_input_selector=row.price_input_selector,
                source_plan_status=plan.status,
                safety_notes=tuple(notes),
            )
        )
    return tuple(edits)


def require_web_apply_ready(
    snapshot: CardUploaderWebPageSnapshot,
    edits: Iterable[CardUploaderWebPriceEdit],
    *,
    policy: CardUploaderWebSafetyPolicy | None = None,
    confirm_live_sync: bool = False,
) -> tuple[CardUploaderWebPriceEdit, ...]:
    """Validate that browser automation may apply edits, without applying them."""

    active_policy = policy or CardUploaderWebSafetyPolicy()
    rows = tuple(edits)
    blockers: list[str] = []
    if not snapshot.is_automatic_inventory_page:
        blockers.append("not_carduploader_automatic_inventory_page")
    if active_policy.require_known_save_mode and snapshot.save_mode == SAVE_MODE_UNKNOWN:
        blockers.append("carduploader_save_mode_unknown")
    if snapshot.save_mode == SAVE_MODE_AUTOSAVE and not active_policy.allow_autosave:
        blockers.append("autosave_page_blocked")
    if active_policy.require_explicit_live_sync_confirmation and not confirm_live_sync:
        blockers.append("live_sync_confirmation_required")
    if len(rows) > active_policy.max_rows_per_apply:
        blockers.append("too_many_rows_for_single_apply")
    unsafe_rows = [edit for edit in rows if not edit.is_apply_ready]
    if unsafe_rows:
        blockers.append(f"unsafe_or_unapproved_rows:{len(unsafe_rows)}")
    if blockers:
        raise CardUploaderPriceUpdateError(
            "CardUploader web apply blocked: " + ", ".join(blockers)
        )
    return rows


__all__ = [
    "CARDUPLOADER_AUTOMATIC_INVENTORY_URL",
    "SAVE_MODE_AUTOSAVE",
    "SAVE_MODE_MANUAL",
    "SAVE_MODE_UNKNOWN",
    "CardUploaderWebInventoryRow",
    "CardUploaderWebPageSnapshot",
    "CardUploaderWebPriceEdit",
    "CardUploaderWebSafetyPolicy",
    "build_web_price_edits",
    "carduploader_inventory_snapshot_script",
    "normalize_carduploader_web_snapshot",
    "require_web_apply_ready",
]
