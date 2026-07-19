from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False
    TkinterDnD = None
    DND_FILES = None

from . import __version__
from .config import (
    CONFIG_DIR,
    load_app_config,
    load_recent_files,
    remember_recent_file,
    save_pricing_profile,
)
from .csv_import import SOURCE_CARDUPLOADER, SOURCE_CUSTOM, SOURCE_EBAY
from .engine import MarketplaceIntelligenceEngine
from .reports import result_row


BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk

THEME = {
    "bg": "#EEF2F7",
    "panel": "#FFFFFF",
    "panel_alt": "#F8FAFC",
    "border": "#CBD5E1",
    "navy": "#0F172A",
    "blue": "#2563EB",
    "blue_hover": "#1D4ED8",
    "text": "#111827",
    "muted": "#64748B",
    "success": "#047857",
    "danger": "#B91C1C",
    "warning": "#B45309",
}


class MarketplaceIntelligenceApp(BaseTk):
    def __init__(self):
        super().__init__()
        self.title(f"Marketplace Intelligence v{__version__}")
        self.geometry("1220x780")
        self.minsize(1080, 680)
        self.configure(bg=THEME["bg"])
        self.engine = MarketplaceIntelligenceEngine()
        self.pricing_profile = dict(self.engine.config.pricing_profile)
        self.input_path = tk.StringVar(value="")
        self.source_type_var = tk.StringVar(value="auto")
        self.detected_source = tk.StringVar(value="Detected source: not checked")
        self.source_profile_var = tk.StringVar(value="")
        self.status = tk.StringVar(value="Ready.")
        self.summary = tk.StringVar(value="Import an eBay Active Listings, CardUploader, or mapped custom CSV to begin.")
        self.analysis_only = tk.BooleanVar(value=False)
        self.minimum_price_var = tk.StringVar(value=str(self.pricing_profile.get("minimum_price", "1.49")))
        self.ignore_changes_var = tk.StringVar(value=str(self.pricing_profile.get("ignore_changes_under", "0.25")))
        self.max_increase_var = tk.StringVar(value=str(self.pricing_profile.get("maximum_increase_percent", "50.00")))
        self.max_decrease_var = tk.StringVar(value=str(self.pricing_profile.get("maximum_decrease_percent", "35.00")))
        self.shipping_assumption_var = tk.StringVar(value=str(self.pricing_profile.get("shipping_assumption", "buyer_pays_shipping")))
        self.flat_shipping_cost_var = tk.StringVar(value=str(self.pricing_profile.get("flat_shipping_cost", "0.00")))
        self.output_dir: Path | None = None
        self.last_results = []
        self.build_styles()
        self.build_ui()

    def build_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "MI.Treeview",
            background=THEME["panel"],
            foreground=THEME["text"],
            fieldbackground=THEME["panel"],
            bordercolor=THEME["border"],
            rowheight=30,
            font=("Segoe UI", 10),
        )
        style.configure(
            "MI.Treeview.Heading",
            background=THEME["panel_alt"],
            foreground=THEME["text"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map("MI.Treeview", background=[("selected", THEME["blue"])], foreground=[("selected", "#FFFFFF")])
        style.configure("MI.Vertical.TScrollbar", gripcount=0, background=THEME["panel_alt"], troughcolor=THEME["bg"])
        style.configure("MI.Horizontal.TScrollbar", gripcount=0, background=THEME["panel_alt"], troughcolor=THEME["bg"])

    def card(self, parent, title: str = ""):
        frame = tk.Frame(parent, bg=THEME["panel"], highlightbackground=THEME["border"], highlightthickness=1)
        frame.pack(fill="x", pady=(0, 12))
        if title:
            tk.Label(
                frame,
                text=title,
                bg=THEME["panel"],
                fg=THEME["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack(anchor="w", padx=16, pady=(14, 8))
        return frame

    def button(self, parent, text, command, primary=False):
        bg = THEME["blue"] if primary else THEME["panel_alt"]
        fg = "#FFFFFF" if primary else THEME["text"]
        active_bg = THEME["blue_hover"] if primary else "#E2E8F0"
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
        )

    def build_ui(self):
        root = tk.Frame(self, bg=THEME["bg"])
        root.pack(fill="both", expand=True)

        header = tk.Frame(root, bg=THEME["navy"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="CardVector Pricing Engine",
            bg=THEME["navy"],
            fg="#FFFFFF",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w", padx=24, pady=(16, 0))
        tk.Label(
            header,
            text="Universal CSV intake, normalized listings, pricing recommendations, and source-safe exports.",
            bg=THEME["navy"],
            fg="#CBD5E1",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=24, pady=(0, 8))
        badge_row = tk.Frame(header, bg=THEME["navy"])
        badge_row.pack(anchor="w", padx=24, pady=(0, 12))
        for badge in [f"v{__version__}", "Changed-only exports", "Analysis Only beta"]:
            tk.Label(
                badge_row,
                text=badge,
                bg="#1E293B",
                fg="#E2E8F0",
                font=("Segoe UI", 9, "bold"),
                padx=10,
                pady=4,
            ).pack(side="left", padx=(0, 8))

        content = tk.Frame(root, bg=THEME["bg"])
        content.pack(fill="both", expand=True, padx=18, pady=16)

        input_frame = self.card(content, "Universal CSV Intake")
        input_row = tk.Frame(input_frame, bg=THEME["panel"])
        input_row.pack(fill="x", padx=16, pady=(0, 12))
        tk.Entry(
            input_row,
            textvariable=self.input_path,
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            relief="flat",
            insertbackground=THEME["text"],
            font=("Segoe UI", 10),
        ).pack(side="left", fill="x", expand=True, ipady=8)
        action_row = tk.Frame(input_frame, bg=THEME["panel"])
        action_row.pack(fill="x", padx=16, pady=(0, 14))
        self.button(action_row, "Browse", self.browse).pack(side="left")
        self.button(action_row, "Analyze", self.analyze, primary=True).pack(side="left", padx=(8, 0))
        self.button(action_row, "Open Report Folder", self.open_output_folder).pack(side="left", padx=(8, 0))
        tk.Checkbutton(
            action_row,
            text="Analysis Only",
            variable=self.analysis_only,
            bg=THEME["panel"],
            fg=THEME["text"],
            activebackground=THEME["panel"],
            selectcolor=THEME["panel_alt"],
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(18, 0))
        tk.Label(
            action_row,
            text="Skips bulk revise CSV and produces reports only. Non-eBay sources always skip bulk revise.",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(10, 0))
        source_row = tk.Frame(input_frame, bg=THEME["panel"])
        source_row.pack(fill="x", padx=16, pady=(0, 14))
        tk.Label(source_row, textvariable=self.detected_source, bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(source_row, text="Override", bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(18, 6))
        ttk.Combobox(
            source_row,
            textvariable=self.source_type_var,
            values=["auto", SOURCE_EBAY, SOURCE_CARDUPLOADER, SOURCE_CUSTOM],
            state="readonly",
            width=24,
        ).pack(side="left")
        tk.Label(source_row, text="Custom profile", bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(18, 6))
        tk.Entry(source_row, textvariable=self.source_profile_var, bg=THEME["panel_alt"], fg=THEME["text"], relief="flat", width=28).pack(side="left", ipady=5)

        settings_frame = self.card(content, "Pricing Settings")
        settings_grid = tk.Frame(settings_frame, bg=THEME["panel"])
        settings_grid.pack(fill="x", padx=16, pady=(0, 10))
        setting_defs = [
            ("Minimum price", self.minimum_price_var, 0, 0),
            ("Ignore changes under", self.ignore_changes_var, 0, 2),
            ("Max increase %", self.max_increase_var, 1, 0),
            ("Max decrease %", self.max_decrease_var, 1, 2),
            ("Flat shipping cost", self.flat_shipping_cost_var, 2, 0),
        ]
        for label, variable, row, column in setting_defs:
            tk.Label(
                settings_grid,
                text=label,
                bg=THEME["panel"],
                fg=THEME["muted"],
                font=("Segoe UI", 9, "bold"),
            ).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=4)
            tk.Entry(
                settings_grid,
                textvariable=variable,
                bg=THEME["panel_alt"],
                fg=THEME["text"],
                relief="flat",
                insertbackground=THEME["text"],
                font=("Segoe UI", 10),
                width=12,
            ).grid(row=row, column=column + 1, sticky="w", padx=(0, 18), pady=4, ipady=5)
        tk.Label(
            settings_grid,
            text="Shipping",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=2, sticky="w", padx=(0, 8), pady=4)
        shipping_box = ttk.Combobox(
            settings_grid,
            textvariable=self.shipping_assumption_var,
            values=["buyer_pays_shipping", "seller_pays_shipping", "mixed_shipping"],
            state="readonly",
            width=22,
        )
        shipping_box.grid(row=2, column=3, sticky="w", pady=4)
        for idx in range(4):
            settings_grid.columnconfigure(idx, weight=1 if idx in (1, 3) else 0)
        settings_actions = tk.Frame(settings_frame, bg=THEME["panel"])
        settings_actions.pack(fill="x", padx=16, pady=(0, 14))
        self.button(settings_actions, "Save Pricing Profile", self.save_pricing_settings).pack(side="left")
        tk.Label(
            settings_actions,
            text="Seller-paid shipping adds flat shipping cost into the recommendation basis. Mixed shipping makes no automatic adjustment.",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(10, 0))

        recent = load_recent_files()
        if recent:
            recent_frame = tk.Frame(content, bg=THEME["bg"])
            recent_frame.pack(fill="x", pady=(0, 12))
            tk.Label(recent_frame, text="Recent", bg=THEME["bg"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).pack(side="left")
            self.recent_var = tk.StringVar(value=recent[0])
            recent_box = ttk.Combobox(recent_frame, textvariable=self.recent_var, values=recent, state="readonly")
            recent_box.pack(side="left", fill="x", expand=True, padx=10)
            self.button(recent_frame, "Use Recent", lambda: self.input_path.set(self.recent_var.get())).pack(side="left")

        self.drop_frame = tk.Frame(content, bg=THEME["panel_alt"], highlightbackground=THEME["border"], highlightthickness=1)
        self.drop_frame.pack(fill="x", pady=(0, 10), ipady=5)
        tk.Label(
            self.drop_frame,
            text="Drop CSV Here",
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack()
        tk.Label(
            self.drop_frame,
            text="Drag an eBay Active Listings, CardUploader, or mapped custom CSV here.",
            bg=THEME["panel_alt"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
        ).pack(pady=(2, 0))
        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self.on_drop)

        summary_frame = self.card(content, "Report Summary")
        tk.Label(
            summary_frame,
            textvariable=self.summary,
            justify="left",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 14))

        review_frame = tk.Frame(content, bg=THEME["panel"], highlightbackground=THEME["border"], highlightthickness=1)
        review_frame.pack(fill="both", expand=True)
        review_header = tk.Frame(review_frame, bg=THEME["panel"])
        review_header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 8))
        tk.Label(
            review_header,
            text="Review Screen",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")
        tk.Label(
            review_header,
            text="Changed listings by default",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(12, 0))
        tk.Label(review_header, text="Filter", bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).pack(side="right", padx=(0, 8))
        self.review_filter = tk.StringVar(value="Changed Only")
        filter_box = ttk.Combobox(
            review_header,
            textvariable=self.review_filter,
            values=["Changed Only", "Review Required", "All Listings"],
            state="readonly",
            width=18,
        )
        filter_box.pack(side="right")
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.populate_tree(self.last_results))
        columns = (
            "item_id", "title", "current_price", "market_price", "market_source",
            "market_confidence", "recommended_price", "difference", "recommendation", "reason",
        )
        self.tree = ttk.Treeview(review_frame, columns=columns, show="headings", style="MI.Treeview")
        widths = {
            "item_id": 120,
            "title": 340,
            "current_price": 100,
            "market_price": 100,
            "market_source": 170,
            "market_confidence": 120,
            "recommended_price": 120,
            "difference": 90,
            "recommendation": 110,
            "reason": 320,
        }
        for column in columns:
            self.tree.heading(column, text=column.replace("_", " ").title())
            self.tree.column(column, width=widths[column], anchor="w")
        yscroll = ttk.Scrollbar(review_frame, orient="vertical", command=self.tree.yview, style="MI.Vertical.TScrollbar")
        xscroll = ttk.Scrollbar(review_frame, orient="horizontal", command=self.tree.xview, style="MI.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 0))
        yscroll.grid(row=1, column=1, sticky="ns", padx=(0, 16), pady=(0, 0))
        xscroll.grid(row=2, column=0, sticky="ew", padx=(16, 0), pady=(0, 14))
        review_frame.rowconfigure(1, weight=1)
        review_frame.columnconfigure(0, weight=1)
        self.tree.tag_configure("increase", background="#ECFDF5", foreground=THEME["success"])
        self.tree.tag_configure("decrease", background="#FEF2F2", foreground=THEME["danger"])
        self.tree.tag_configure("review", background="#FFFBEB", foreground=THEME["warning"])

        status_bar = tk.Label(
            root,
            textvariable=self.status,
            anchor="w",
            bg=THEME["navy"],
            fg="#CBD5E1",
            font=("Segoe UI", 9),
            padx=14,
            pady=7,
        )
        status_bar.pack(fill="x")

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select Listing CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.input_path.set(path)

    def on_drop(self, event):
        raw = str(event.data or "").strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        self.input_path.set(raw)

    def analyze(self):
        path = Path(self.input_path.get().strip().strip('"'))
        if not path.exists():
            messagebox.showinfo("Marketplace Intelligence", "Choose a valid listing CSV first.")
            return
        if not self.apply_pricing_settings(show_success=False):
            return
        self.status.set("Analyzing listings...")
        self.clear_tree()
        thread = threading.Thread(target=self._analyze_worker, args=(path,), daemon=True)
        thread.start()

    def _analyze_worker(self, path: Path):
        try:
            result = self.engine.analyze_file(
                path,
                analysis_only=self.analysis_only.get(),
                source_type=self.source_type_var.get(),
                source_profile=self.source_profile_var.get().strip() or None,
            )
            remember_recent_file(path)
            self.after(0, lambda: self.display_result(result))
        except Exception as exc:
            self.after(0, lambda: self.show_error(exc))

    def display_result(self, result: dict):
        self.output_dir = result["output_dir"]
        summary = result["summary"]
        reports = result["reports"]
        imported = result["import"]
        self.detected_source.set(f"Detected source: {imported.detected_format} ({imported.source_type})")
        self.last_results = result["results"]
        self.summary.set(
            "\n".join([
                (
                    f"Source: {imported.detected_format}   "
                    f"Imported: {summary.listings_imported}   "
                    f"Normalized: {summary.listings_normalized}   "
                    f"Matched: {summary.listings_matched}   "
                    f"Unmatched: {summary.listings_unmatched}   "
                    f"Increases: {summary.price_increases}   "
                    f"Decreases: {summary.price_decreases}   "
                    f"No Change: {summary.no_changes}   "
                    f"Review: {summary.review_required}   "
                    f"0.99 Review: {summary.zero_99_review_candidates}   "
                    f"Reference-only: {summary.reference_only_evidence}   "
                    f"Revenue Impact: ${summary.potential_revenue_impact}"
                ),
                f"Reports: {self.output_dir}",
            ])
        )
        if hasattr(self, "drop_frame"):
            self.drop_frame.pack_forget()
        self.populate_tree(result["results"])
        self.status.set(f"Complete. Analysis report: {reports['analysis_report']}")

    def populate_tree(self, results):
        self.clear_tree()
        current_filter = self.review_filter.get() if hasattr(self, "review_filter") else "Changed Only"
        for result in results:
            if current_filter == "Changed Only" and not result.decision.changed:
                continue
            if current_filter == "Review Required" and not result.decision.review_required:
                continue
            row = result_row(result)
            tag = ""
            if row["recommendation"] == "Increase":
                tag = "increase"
            elif row["recommendation"] == "Decrease":
                tag = "decrease"
            elif result.decision.review_required:
                tag = "review"
            self.tree.insert(
                "",
                "end",
                values=[
                    row["item_id"],
                    row["title"],
                    row["current_price"],
                    row["market_price"],
                    row["market_source"],
                    row["market_confidence"],
                    row["recommended_price"],
                    row["difference"],
                    row["recommendation"],
                    row["reason"],
                ],
                tags=(tag,) if tag else (),
            )

    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def show_error(self, exc: Exception):
        self.status.set("Analysis failed.")
        messagebox.showerror("Marketplace Intelligence", str(exc))

    def profile_from_settings(self) -> dict:
        profile = dict(self.pricing_profile)
        profile.update({
            "minimum_price": self.minimum_price_var.get().strip(),
            "ignore_changes_under": self.ignore_changes_var.get().strip(),
            "maximum_increase_percent": self.max_increase_var.get().strip(),
            "maximum_decrease_percent": self.max_decrease_var.get().strip(),
            "shipping_assumption": self.shipping_assumption_var.get().strip(),
            "flat_shipping_cost": self.flat_shipping_cost_var.get().strip() or "0.00",
        })
        return profile

    def validate_pricing_settings(self, profile: dict) -> None:
        numeric_fields = [
            "minimum_price",
            "ignore_changes_under",
            "maximum_increase_percent",
            "maximum_decrease_percent",
            "flat_shipping_cost",
        ]
        for field in numeric_fields:
            value = profile.get(field, "")
            try:
                amount = float(str(value))
            except Exception as exc:
                raise ValueError(f"{field} must be a number.") from exc
            if amount < 0:
                raise ValueError(f"{field} cannot be negative.")
        if profile.get("shipping_assumption") not in {"buyer_pays_shipping", "seller_pays_shipping", "mixed_shipping"}:
            raise ValueError("Shipping assumption must be buyer_pays_shipping, seller_pays_shipping, or mixed_shipping.")

    def apply_pricing_settings(self, show_success=True) -> bool:
        try:
            profile = self.profile_from_settings()
            self.validate_pricing_settings(profile)
            self.pricing_profile = profile
            config = load_app_config()
            config.pricing_profile = profile
            self.engine = MarketplaceIntelligenceEngine(config)
            if show_success:
                self.status.set("Pricing settings applied.")
            return True
        except Exception as exc:
            self.status.set("Pricing settings need review.")
            messagebox.showerror("Pricing Settings", str(exc))
            return False

    def save_pricing_settings(self):
        if not self.apply_pricing_settings(show_success=False):
            return
        save_pricing_profile(self.pricing_profile)
        self.status.set("Pricing profile saved.")
        messagebox.showinfo(
            "Pricing Settings",
            f"Pricing profile saved:\n{CONFIG_DIR / 'business_profile.json'}",
        )

    def open_output_folder(self):
        if not self.output_dir:
            messagebox.showinfo("Marketplace Intelligence", "Run an analysis first.")
            return
        try:
            os.startfile(self.output_dir)
        except Exception as exc:
            messagebox.showinfo("Marketplace Intelligence", f"Report folder:\n{self.output_dir}\n\nCould not open automatically:\n{exc}")


def main():
    app = MarketplaceIntelligenceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
