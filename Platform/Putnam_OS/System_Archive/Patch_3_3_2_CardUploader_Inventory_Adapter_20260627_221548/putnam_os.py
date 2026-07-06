import csv, json, os, shutil, sys, webbrowser, statistics, re, urllib.parse, urllib.request, subprocess
from datetime import datetime
from pathlib import Path
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog

APP_VERSION = "3.3.1"
APP_NAME = "Putnam OS"
FLOOR = 0.99
REVIEW_THRESHOLD = 20.00

BRAND = {
    "bg": "#080A0F",
    "panel": "#0B1426",
    "panel2": "#101B33",
    "sidebar": "#05070C",
    "blue": "#0077FF",
    "blue2": "#20A4FF",
    "gold": "#D8A72E",
    "gold_dark": "#8A6418",
    "text": "#F5F7FB",
    "muted": "#B9C4D8",
    "success": "#22C55E",
    "warning": "#FACC15",
    "danger": "#EF4444",
}

EXCLUDE_TERMS = [
    "world championship", "worlds", "world championship deck", " deck", "theme deck",
    "battle deck", "starter deck", "psa", "bgs", "cgc", "sgc", "ace", "tag", "slab",
    "graded", "lot", "bundle", "playset", "4x", "x4", "pack", "booster", "wrapper",
    "sealed", "proxy", "custom", "reprint", "metal", "gold foil", "jumbo", "oversized",
    "complete set", "binder", "master set"
]


def user_root() -> Path:
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)
    fallback = Path.home() / "OneDrive" / "PutnamCollectibles"
    if fallback.exists():
        os.environ["USERENVIRONMENT"] = str(fallback)
        return fallback
    raise RuntimeError("Could not locate PutnamCollectibles root. Set USERENVIRONMENT.")


ROOT = user_root()
OS_DIR = ROOT / "Putnam_OS"
SYSTEM = OS_DIR / "System"
APP_DIR = SYSTEM / "app"
CONFIG = SYSTEM / "config"
LOGS = SYSTEM / "logs"
CACHE = SYSTEM / "cache"
DATA = SYSTEM / "data"
INCOMING = OS_DIR / "Incoming Files"
COMPLETED = OS_DIR / "Completed Jobs"
IMPORTS = ROOT / "Imports"
EXPORTS = ROOT / "Exports"
MEDIA = ROOT / "Media"
COLLECTR = ROOT / "Collectr"
ROOT_SESSIONS = ROOT / "Work Sessions"
ARCHIVE = ROOT / "Archive"
DOCS = ROOT / "Docs"
DOWNLOADS = ROOT / "Downloads"
SESSIONS = ROOT_SESSIONS

PLATFORM = ROOT / "Putnam_Platform"
TOOLS = PLATFORM / "tools"
UTILITIES = PLATFORM / "utilities"
INSTALLERS = PLATFORM / "installers"

CONTENT = ROOT / "Putnam_Content"
CONTENT_IDEAS = CONTENT / "Ideas"
CONTENT_RECORDINGS = CONTENT / "Recordings"
CONTENT_CLIPS = CONTENT / "Clips"
CONTENT_EPISODES = CONTENT / "Episodes"

for p in [OS_DIR, SYSTEM, APP_DIR, CONFIG, LOGS, CACHE, DATA, INCOMING, COMPLETED,
          IMPORTS, EXPORTS, MEDIA, COLLECTR, ROOT_SESSIONS, ARCHIVE, DOCS,
          PLATFORM, TOOLS, UTILITIES, INSTALLERS, CONTENT, CONTENT_IDEAS, CONTENT_RECORDINGS,
          CONTENT_CLIPS, CONTENT_EPISODES]:
    p.mkdir(parents=True, exist_ok=True)


def nowstamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def today_id():
    return datetime.now().strftime("%Y-%m-%d")


def append_activity(message: str):
    LOGS.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}\n"
    with open(LOGS / "activity.log", "a", encoding="utf-8") as f:
        f.write(line)


def recent_activity(limit=8):
    path = LOGS / "activity.log"
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        return lines[-limit:][::-1]
    except Exception:
        return []


def money(v):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip() or 0)
    except Exception:
        return 0.0


def read_csv(path):
    for enc in ["utf-8-sig", "utf-8", "cp1252"]:
        try:
            with open(path, newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fields:
        fields = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def count_files(folder, pattern="*"):
    try:
        return len([p for p in Path(folder).glob(pattern) if p.is_file()])
    except Exception:
        return 0


def todays_jobs_count():
    today = datetime.now().strftime("%Y%m%d")
    try:
        return len([p for p in COMPLETED.iterdir() if p.is_dir() and today in p.name])
    except Exception:
        return 0


def latest_completed_job():
    try:
        jobs = [p for p in COMPLETED.iterdir() if p.is_dir()]
        if not jobs:
            return None
        return max(jobs, key=lambda p: p.stat().st_mtime)
    except Exception:
        return None


def unique_path(path: Path) -> Path:
    path = Path(path)
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i:02d}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def copy_to_folder(source: Path, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    destination = unique_path(folder / source.name)
    if source.resolve() == destination.resolve():
        return destination
    shutil.copy2(source, destination)
    return destination


def latest_carduploader_export():
    search_dirs = [IMPORTS, INCOMING, DOWNLOADS]
    preferred_terms = ["ebay", "carduploader", "pokemon-english"]
    candidates = []
    for folder in search_dirs:
        if not folder.exists():
            continue
        try:
            for path in folder.glob("*.csv"):
                if not path.is_file():
                    continue
                lower = path.name.lower()
                preferred = any(term in lower for term in preferred_terms)
                candidates.append({
                    "path": path,
                    "preferred": preferred,
                    "mtime": path.stat().st_mtime,
                })
        except Exception:
            continue
    if not candidates:
        return None
    preferred = [c for c in candidates if c["preferred"]]
    pool = preferred or candidates
    return max(pool, key=lambda c: c["mtime"])["path"]


def detect_type(rows):
    if not rows:
        return "unknown"
    cols = set(rows[0].keys())
    if "*Title" in cols and "*StartPrice" in cols:
        return "carduploader_new"
    if any(c.lower() == "itemid" for c in cols) and any("price" in c.lower() for c in cols):
        return "active_listings"
    if "Item number" in cols and any("price" in c.lower() for c in cols):
        return "active_listings"
    return "unknown"


def card_fields(row):
    title = row.get("*Title") or row.get("Title") or row.get("title") or ""
    name = row.get("*C:Card Name") or row.get("Card Name") or ""
    setname = row.get("*C:Set") or row.get("Set") or ""
    number = row.get("*C:Card Number") or row.get("Card Number") or ""
    price = money(row.get("*StartPrice") or row.get("StartPrice") or row.get("Price") or row.get("BuyItNowPrice"))
    return title, name, setname, number, price


def build_query(row):
    title, name, setname, number, price = card_fields(row)
    parts = []
    if name:
        parts.append(name)
    if setname:
        parts.append(setname)
    if number:
        parts.append(number)
    if not parts:
        parts = [title]
    return " ".join(parts).strip()


def cache_file(q):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", q)[:120]
    return CACHE / (safe + ".json")


def fetch_carduploader_sales(q):
    cf = cache_file(q)
    if cf.exists():
        try:
            data = json.loads(cf.read_text(encoding="utf-8-sig"))
            if data.get("cached_at"):
                return data
        except Exception:
            pass
    url = "https://carduploader.com/backend/sales/search?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PutnamOS/3.3 market intelligence", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    data["cached_at"] = datetime.now().isoformat()
    cf.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def comparable_reason(title, name, setname, number):
    t = title.lower()
    for term in EXCLUDE_TERMS:
        if term.strip() and term.strip() in t:
            return False, f"excluded term: {term.strip()}"
    if name and name.lower() not in t:
        return False, "card name not in title"
    if number:
        n = number.lower().replace(" ", "")
        t2 = t.replace(" ", "")
        if n not in t2 and n.lstrip("0") not in t2:
            return False, "card number not in title"
    if setname:
        words = [w for w in re.split(r"\W+", setname.lower()) if len(w) > 3]
        if words and not any(w in t for w in words):
            return False, "set not evident in title"
    return True, "accepted"


def market_analyze(rows):
    reports = []
    rejected = []
    for i, row in enumerate(rows, 1):
        title, name, setname, number, current = card_fields(row)
        q = build_query(row)
        rec = {
            "row": i, "title": title, "card_name": name, "set": setname, "number": number,
            "current_price": current, "query": q, "status": "NO_DATA", "accepted_count": 0,
            "rejected_count": 0, "last_sale": "", "last3_avg": "", "median": "", "confidence": 0,
            "reason": "",
        }
        try:
            data = fetch_carduploader_sales(q)
            results = data.get("results", [])
            accepted = []
            for r in results:
                ok, reason = comparable_reason(r.get("title", ""), name, setname, number)
                if ok:
                    accepted.append(r)
                else:
                    rr = dict(rec)
                    rr.update({
                        "candidate_title": r.get("title", ""),
                        "candidate_price": r.get("price", ""),
                        "reject_reason": reason,
                    })
                    rejected.append(rr)
            prices = [money(r.get("price")) for r in accepted if money(r.get("price")) > 0]
            rec["accepted_count"] = len(accepted)
            rec["rejected_count"] = max(0, len(results) - len(accepted))
            if prices:
                last3 = prices[:3]
                rec["last_sale"] = prices[0]
                rec["last3_avg"] = round(sum(last3) / len(last3), 2)
                rec["median"] = round(statistics.median(prices[:min(20, len(prices))]), 2)
                # Conservative confidence for review only.
                count_score = min(40, len(prices) * 4)
                spread_score = 20
                if len(last3) == 3:
                    avg = rec["last3_avg"]
                    spread = max(last3) - min(last3)
                    spread_score = max(0, 25 - int((spread / max(avg, 0.01)) * 25))
                query_score = 20 if (name and number and setname) else 10
                rec["confidence"] = min(100, count_score + spread_score + query_score)
                if current <= FLOOR and len(prices) >= 3 and rec["last3_avg"] >= 2 * FLOOR and rec["confidence"] >= 70:
                    rec["status"] = "MARKET_OPPORTUNITY_REVIEW"
                    rec["reason"] = f"Last 3 avg ${rec['last3_avg']:.2f} is >= 2x floor after validation."
                else:
                    rec["status"] = "NO_CHANGE"
                    rec["reason"] = "Market data did not exceed opportunity threshold."
            else:
                rec["reason"] = "No accepted comparables after validation."
        except Exception as e:
            rec["status"] = "ERROR"
            rec["reason"] = str(e)[:200]
        reports.append(rec)
    return reports, rejected


def audit_new_listing(path, use_market=True):
    rows = read_csv(path)
    typ = detect_type(rows)
    if typ != "carduploader_new":
        raise ValueError("This does not appear to be a CardUploader/eBay new-listing CSV.")
    job = COMPLETED / f"Pricing_Analysis_{nowstamp()}"
    (job / "source_backup").mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, job / "source_backup" / Path(path).name)
    out_rows = []
    changes = 0
    for row in rows:
        r = dict(row)
        p = money(r.get("*StartPrice"))
        if p < FLOOR:
            r["*StartPrice"] = f"{FLOOR:.2f}"
            changes += 1
        out_rows.append(r)
    ebay_ready = job / "ebay_upload_ready.csv"
    write_csv(ebay_ready, out_rows, list(rows[0].keys()))
    write_csv(job / "review.csv", out_rows, list(rows[0].keys()))
    export_copy = copy_to_folder(ebay_ready, EXPORTS)
    processed_source = copy_to_folder(Path(path), IMPORTS / "Processed")
    market_reports = []
    rejected = []
    if use_market:
        market_reports, rejected = market_analyze(out_rows)
        write_csv(job / "market_report.csv", market_reports)
        if rejected:
            write_csv(job / "rejected_comps.csv", rejected)
    opp = sum(1 for r in market_reports if r.get("status") == "MARKET_OPPORTUNITY_REVIEW")
    summary = job / "summary.txt"
    summary.write_text(
        f"Putnam OS v{APP_VERSION}\nRows: {len(rows)}\nFloor changes: {changes}\nMarket opportunities: {opp}\nOutput: {job}\nExport copy: {export_copy}\nProcessed source copy: {processed_source}\n",
        encoding="utf-8",
    )
    append_activity(f"Pricing analysis complete: {len(rows)} rows, {opp} market opportunities, export copied to Exports")
    attach_job_to_session(job, rows=len(rows), opportunities=opp)
    return job, len(rows), changes, opp


def current_session_path():
    return DATA / "current_session.json"


def load_current_session():
    p = current_session_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        if data.get("active"):
            return data
    except Exception:
        return None
    return None


def save_current_session(data):
    DATA.mkdir(parents=True, exist_ok=True)
    current_session_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_work_session(goal="List new inventory", planned_cards="100", capture_method="iPhone camera"):
    stamp = nowstamp()
    folder = SESSIONS / f"Work_Session_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)
    data = {
        "active": True,
        "session_id": stamp,
        "folder": str(folder),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "ended_at": "",
        "goal": goal,
        "planned_cards": planned_cards,
        "completed_cards": "",
        "capture_method": capture_method,
        "recording_path": "",
        "pricing_jobs": [],
        "notes": [],
    }
    (folder / "session.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (folder / "session_notes.md").write_text(
        f"# Putnam Work Session {stamp}\n\n"
        f"Started: {data['started_at']}\n\n"
        f"Goal: {goal}\n\nCards planned: {planned_cards}\n\n"
        f"Capture method: {capture_method}\n\n"
        "## Notes\n\n- \n\n## Bottlenecks\n\n- \n\n## Content moments\n\n- \n",
        encoding="utf-8",
    )
    save_current_session(data)
    append_activity(f"Work session started: {folder.name}")
    return folder


def end_work_session(completed_cards="", recording_path="", notes=""):
    data = load_current_session()
    if not data:
        return None
    data["active"] = False
    data["ended_at"] = datetime.now().isoformat(timespec="seconds")
    if completed_cards:
        data["completed_cards"] = completed_cards
    if recording_path:
        data["recording_path"] = recording_path
    if notes:
        data.setdefault("notes", []).append(notes)
    folder = Path(data["folder"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "session.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        current_session_path().unlink()
    except Exception:
        pass
    append_activity(f"Work session ended: {folder.name}")
    return folder


def attach_job_to_session(job_path, rows=0, opportunities=0):
    data = load_current_session()
    if not data:
        return
    data.setdefault("pricing_jobs", []).append({
        "job_path": str(job_path),
        "rows": rows,
        "opportunities": opportunities,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    save_current_session(data)
    folder = Path(data["folder"])
    if folder.exists():
        (folder / "session.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def latest_sessions(limit=6):
    try:
        folders = [p for p in SESSIONS.iterdir() if p.is_dir()]
        folders = sorted(folders, key=lambda p: p.stat().st_mtime, reverse=True)
        return folders[:limit]
    except Exception:
        return []


BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk


class PutnamOS(BaseTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1240x800")
        self.minsize(1100, 720)
        self.configure(bg=BRAND["bg"])
        self.loaded = None
        self.rows = []
        self.detected = ""
        self.nav_buttons = {}
        self.status = tk.StringVar(value="Ready.")
        self.build_styles()
        self.build_ui()

    def build_styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Main.TFrame", background=BRAND["bg"])
        s.configure("Primary.TButton", font=("Segoe UI", 12, "bold"), padding=12)
        s.configure("Secondary.TButton", font=("Segoe UI", 10), padding=8)
        s.map("Primary.TButton", background=[("active", BRAND["blue2"])])
        s.map("Secondary.TButton", background=[("active", BRAND["panel2"])])

    def build_ui(self):
        side = tk.Frame(self, bg=BRAND["sidebar"], width=235)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="PUTNAM", bg=BRAND["sidebar"], fg=BRAND["text"],
                 font=("Segoe UI", 24, "bold")).pack(pady=(28, 0))
        tk.Label(side, text=f"OS v{APP_VERSION}", bg=BRAND["sidebar"], fg=BRAND["gold"],
                 font=("Segoe UI", 10, "bold")).pack(pady=(0, 22))

        for name in ["Home", "Pricing", "Sessions", "Content", "Inventory", "Shipping", "Analytics", "Settings"]:
            b = tk.Button(
                side, text=name.upper(), anchor="w", bg=BRAND["sidebar"], fg=BRAND["muted"],
                activebackground=BRAND["panel2"], activeforeground=BRAND["text"], relief="flat",
                font=("Segoe UI", 10, "bold"), padx=24, pady=11, command=lambda n=name: self.show_page(n)
            )
            b.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[name] = b

        bottom = tk.Frame(side, bg=BRAND["sidebar"])
        bottom.pack(side="bottom", fill="x", padx=14, pady=18)
        tk.Label(bottom, text="Root", bg=BRAND["sidebar"], fg=BRAND["gold"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(bottom, text=str(ROOT), bg=BRAND["sidebar"], fg=BRAND["muted"], font=("Segoe UI", 7),
                 wraplength=190, justify="left").pack(anchor="w")

        self.main = tk.Frame(self, bg=BRAND["bg"])
        self.main.pack(side="left", fill="both", expand=True)

        self.statusbar = tk.Label(self, textvariable=self.status, bg=BRAND["sidebar"], fg=BRAND["muted"],
                                  anchor="w", font=("Segoe UI", 9), padx=10)
        self.statusbar.pack(side="bottom", fill="x")
        self.show_page("Home")

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def show_page(self, name):
        for n, b in self.nav_buttons.items():
            if n == name:
                b.configure(bg=BRAND["panel2"], fg=BRAND["text"])
            else:
                b.configure(bg=BRAND["sidebar"], fg=BRAND["muted"])
        self.clear()
        if name == "Home":
            self.home_page()
        elif name == "Pricing":
            self.pricing_page()
        elif name == "Sessions":
            self.sessions_page()
        elif name == "Content":
            self.content_page()
        else:
            self.placeholder_page(name)

    def header(self, title, subtitle=""):
        tk.Label(self.main, text=title, bg=BRAND["bg"], fg=BRAND["text"], font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=34, pady=(28, 2))
        if subtitle:
            tk.Label(self.main, text=subtitle, bg=BRAND["bg"], fg=BRAND["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=34, pady=(0, 18))

    def card(self, parent, **pack):
        f = tk.Frame(parent, bg=BRAND["panel"], highlightbackground=BRAND["gold_dark"], highlightthickness=1)
        if pack is not None:
            f.pack(**pack)
        return f

    def label(self, parent, text, size=10, color=None, bold=False, bg=None, **pack):
        lbl = tk.Label(parent, text=text, bg=bg or BRAND["panel"], fg=color or BRAND["text"],
                       font=("Segoe UI", size, "bold" if bold else "normal"), justify="left")
        if pack is not None:
            lbl.pack(**pack)
        return lbl

    def metric_card(self, parent, title, value, subtitle=""):
        c = self.card(parent, side="left", fill="both", expand=True, padx=(0, 12), ipady=10)
        self.label(c, title, 9, BRAND["gold"], True, anchor="w", padx=16, pady=(12, 2))
        self.label(c, str(value), 22, BRAND["text"], True, anchor="w", padx=16)
        if subtitle:
            self.label(c, subtitle, 9, BRAND["muted"], False, anchor="w", padx=16, pady=(0, 8))
        return c

    def make_drop_zone(self, parent, text, command):
        zone = tk.Frame(parent, bg=BRAND["panel2"], highlightbackground=BRAND["blue"], highlightthickness=2)
        zone.pack(fill="x", pady=(0, 16), ipady=22)
        tk.Label(zone, text=text, bg=BRAND["panel2"], fg=BRAND["text"], font=("Segoe UI", 20, "bold")).pack(pady=(16, 4))
        tk.Label(zone, text="Drop CSV here or click to browse", bg=BRAND["panel2"], fg=BRAND["muted"], font=("Segoe UI", 10)).pack()
        tk.Button(zone, text="Browse for CSV", bg=BRAND["blue"], fg="white", activebackground=BRAND["blue2"],
                  relief="flat", font=("Segoe UI", 11, "bold"), padx=16, pady=8, command=command).pack(pady=14)
        zone.bind("<Button-1>", lambda e: command())
        for child in zone.winfo_children():
            child.bind("<Button-1>", lambda e: command())
        if DND_AVAILABLE:
            zone.drop_target_register(DND_FILES)
            zone.dnd_bind("<<Drop>>", self.on_drop)
            for child in zone.winfo_children():
                try:
                    child.drop_target_register(DND_FILES)
                    child.dnd_bind("<<Drop>>", self.on_drop)
                except Exception:
                    pass
        return zone

    def home_page(self):
        self.header("Home", "Mission control for Putnam Collectibles.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        mission = self.card(wrap, fill="x", pady=(0, 16), ipady=14)
        self.label(mission, "TODAY'S MISSION", 13, BRAND["gold"], True, anchor="w", padx=18, pady=(14, 4))
        cur = load_current_session()
        if cur:
            msg = f"Active work session: {Path(cur.get('folder','')).name}\nGoal: {cur.get('goal','')}"
        else:
            msg = "Analyze the next CardUploader export or start a tracked work session."
        self.label(mission, msg, 10, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 12))

        latest_card = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(latest_card, "ANALYZE LATEST CARDUPLOADER EXPORT", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        detected = latest_carduploader_export()
        detected_text = f"Detected: {detected}" if detected else "No CSV detected in Imports, Incoming Files, or Downloads."
        self.latest_csv_var = tk.StringVar(value=detected_text)
        tk.Label(latest_card, textvariable=self.latest_csv_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 9), justify="left", wraplength=820).pack(anchor="w", padx=18, pady=(0, 10))
        latest_buttons = tk.Frame(latest_card, bg=BRAND["panel"])
        latest_buttons.pack(anchor="w", padx=18, pady=(0, 14))
        tk.Button(latest_buttons, text="Analyze Latest CardUploader Export", bg=BRAND["blue"], fg="white",
                  activebackground=BRAND["blue2"], relief="flat", font=("Segoe UI", 11, "bold"),
                  padx=16, pady=9, command=self.analyze_latest_carduploader_export).pack(side="left")
        self.action_button(latest_buttons, "Browse for CSV", self.browse_and_run).pack(side="left", padx=10)

        self.make_drop_zone(wrap, "Drop CardUploader CSV Here", self.browse_and_run)

        actions = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(actions, "QUICK ACTIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        btns = tk.Frame(actions, bg=BRAND["panel"])
        btns.pack(anchor="w", padx=18, pady=(0, 14))
        self.action_button(btns, "Start Work Session", self.start_work_session).pack(side="left")
        self.action_button(btns, "Open Imports", lambda: os.startfile(IMPORTS)).pack(side="left", padx=8)
        self.action_button(btns, "Open Exports", lambda: os.startfile(EXPORTS)).pack(side="left", padx=8)
        self.action_button(btns, "Open Completed Jobs", lambda: os.startfile(COMPLETED)).pack(side="left", padx=8)
        self.action_button(btns, "Open Work Sessions", lambda: os.startfile(SESSIONS)).pack(side="left", padx=8)
        self.action_button(btns, "Split Recording", self.run_split_recording_tool).pack(side="left", padx=8)

        row = tk.Frame(wrap, bg=BRAND["bg"])
        row.pack(fill="x", pady=(0, 16))
        self.metric_card(row, "Pricing Jobs Today", todays_jobs_count(), "Completed job folders")
        self.metric_card(row, "Work Sessions", len(latest_sessions(99)), "Tracked sessions")
        self.metric_card(row, "Raw Recordings", count_files(CONTENT_RECORDINGS, "*"), "Saved footage")
        self.metric_card(row, "Content Ideas", count_files(CONTENT_IDEAS, "*"), "Backlog")

        lower = tk.Frame(wrap, bg=BRAND["bg"])
        lower.pack(fill="both", expand=True)
        activity = self.card(lower, side="left", fill="both", expand=True, padx=(0, 12), ipady=10)
        self.label(activity, "RECENT ACTIVITY", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        acts = recent_activity(7) or ["No activity recorded yet."]
        for a in acts:
            self.label(activity, "âœ“ " + a, 9, BRAND["muted"], False, anchor="w", padx=18, pady=2)

        content = self.card(lower, side="left", fill="both", expand=True, ipady=10)
        self.label(content, "CONTENT SNAPSHOT", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        lines = [
            f"Recordings saved: {count_files(CONTENT_RECORDINGS, '*')}",
            f"Clips captured: {count_files(CONTENT_CLIPS, '*')}",
            f"Episodes planned: {count_files(CONTENT_EPISODES, '*')}",
            "Current concept: 100-card listing workflow",
        ]
        for line in lines:
            self.label(content, line, 9, BRAND["muted"], False, anchor="w", padx=18, pady=2)
        self.action_button(content, "Open OBS Checklist", self.open_recording_checklist).pack(anchor="w", padx=18, pady=12)

    def action_button(self, parent, text, command):
        return tk.Button(parent, text=text, bg=BRAND["panel2"], fg=BRAND["text"],
                         activebackground=BRAND["blue"], activeforeground="white", relief="flat",
                         font=("Segoe UI", 10, "bold"), padx=14, pady=8, command=command)

    def browse_and_run(self):
        p = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not p:
            return
        self.load(p)
        self.auto_run()

    def analyze_latest_carduploader_export(self):
        latest = latest_carduploader_export()
        if not latest:
            try:
                self.latest_csv_var.set("No CSV found. Use Browse for CSV or drop a CardUploader CSV on Home.")
            except Exception:
                pass
            self.status.set("No CardUploader CSV found in Imports, Incoming Files, or Downloads.")
            messagebox.showinfo("Putnam OS", "No CSV found in Imports, Incoming Files, or Downloads.\nUse Browse for CSV or drop a CardUploader CSV on Home.")
            return
        try:
            self.latest_csv_var.set(f"Detected: {latest}\nRunning analysis now...")
        except Exception:
            pass
        self.status.set(f"Detected latest export: {latest}")
        self.update()
        self.load(latest)
        self.auto_run()

    def on_drop(self, event):
        raw = event.data
        # Handles {C:\path with spaces\file.csv}
        paths = self.tk.splitlist(raw)
        if not paths:
            return
        p = paths[0]
        if not str(p).lower().endswith(".csv"):
            messagebox.showwarning("Putnam OS", "Please drop a CSV file.")
            return
        self.load(p)
        self.auto_run()

    def start_work_session(self):
        goal = simpledialog.askstring("Work Session", "Goal:", initialvalue="List new inventory") or "List new inventory"
        planned = simpledialog.askstring("Work Session", "Planned cards:", initialvalue="100") or "100"
        method = simpledialog.askstring("Work Session", "Capture method:", initialvalue="iPhone camera") or "iPhone camera"
        folder = create_work_session(goal, planned, method)
        messagebox.showinfo("Putnam OS", f"Work session started:\n{folder}")
        try:
            os.startfile(folder)
        except Exception:
            pass
        self.show_page("Home")

    def end_current_session_ui(self):
        completed = simpledialog.askstring("End Session", "Cards completed:", initialvalue="")
        recording = filedialog.askopenfilename(title="Select raw recording or cancel", filetypes=[("Video files", "*.mp4 *.mkv *.mov"), ("All files", "*.*")])
        notes = simpledialog.askstring("End Session", "Session notes / bottlenecks:", initialvalue="")
        folder = end_work_session(completed or "", recording or "", notes or "")
        if folder:
            messagebox.showinfo("Putnam OS", f"Work session ended:\n{folder}")
            try:
                os.startfile(folder)
            except Exception:
                pass
        else:
            messagebox.showwarning("Putnam OS", "No active work session found.")
        self.show_page("Sessions")

    def run_split_recording_tool(self):
        tool = TOOLS / "Split_Putnam_Work_Session.ps1"
        if not tool.exists():
            messagebox.showwarning("Putnam OS", f"Split tool not found:\n{tool}")
            return
        try:
            subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(tool)], cwd=str(ROOT))
            append_activity("Launched split work session tool")
        except Exception as e:
            messagebox.showerror("Putnam OS", str(e))

    def sessions_page(self):
        self.header("Work Sessions", "Track production sessions, footage, bottlenecks, and metrics.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        current = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(current, "CURRENT SESSION", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        cur = load_current_session()
        if cur:
            txt = f"Active: {Path(cur.get('folder','')).name}\nStarted: {cur.get('started_at','')}\nGoal: {cur.get('goal','')}\nPlanned cards: {cur.get('planned_cards','')}"
        else:
            txt = "No active session."
        self.label(current, txt, 10, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 10))
        btns = tk.Frame(current, bg=BRAND["panel"])
        btns.pack(anchor="w", padx=18, pady=(0, 14))
        self.action_button(btns, "Start Session", self.start_work_session).pack(side="left")
        self.action_button(btns, "End Session", self.end_current_session_ui).pack(side="left", padx=8)
        self.action_button(btns, "Split Recording", self.run_split_recording_tool).pack(side="left", padx=8)
        self.action_button(btns, "Open Sessions Folder", lambda: os.startfile(SESSIONS)).pack(side="left", padx=8)

        history = self.card(wrap, fill="both", expand=True, ipady=12)
        self.label(history, "RECENT SESSIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        sessions = latest_sessions(8)
        if not sessions:
            self.label(history, "No sessions recorded yet.", 10, BRAND["muted"], False, anchor="w", padx=18, pady=4)
        for s in sessions:
            summary = s.name
            meta = s / "session.json"
            if meta.exists():
                try:
                    d = json.loads(meta.read_text(encoding="utf-8-sig"))
                    summary += f"  |  goal: {d.get('goal','')}  |  cards: {d.get('completed_cards','') or d.get('planned_cards','')}"
                    if d.get("pricing_jobs"):
                        summary += f"  |  pricing jobs: {len(d.get('pricing_jobs', []))}"
                except Exception:
                    pass
            row = tk.Frame(history, bg=BRAND["panel"])
            row.pack(fill="x", padx=18, pady=3)
            self.label(row, summary, 9, BRAND["muted"], False, side="left", fill="x", expand=True)
            self.action_button(row, "Open", lambda path=s: os.startfile(path)).pack(side="right")

    def content_page(self):
        self.header("Content", "Track recordings, clips, episode ideas, and publishing preparation.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        row = tk.Frame(wrap, bg=BRAND["bg"])
        row.pack(fill="x", pady=(0, 16))
        self.metric_card(row, "Recordings", count_files(CONTENT_RECORDINGS, "*"), "Raw footage")
        self.metric_card(row, "Clips", count_files(CONTENT_CLIPS, "*"), "Potential shorts")
        self.metric_card(row, "Ideas", count_files(CONTENT_IDEAS, "*"), "Backlog")
        self.metric_card(row, "Episodes", count_files(CONTENT_EPISODES, "*"), "Planned videos")
        panel = self.card(wrap, fill="x", ipady=12)
        self.label(panel, "QUICK ACTIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        btns = tk.Frame(panel, bg=BRAND["panel"])
        btns.pack(anchor="w", padx=18, pady=(0, 14))
        self.action_button(btns, "Open OBS Checklist", self.open_recording_checklist).pack(side="left")
        self.action_button(btns, "Open Content Folder", lambda: os.startfile(CONTENT)).pack(side="left", padx=10)
        self.action_button(btns, "Split Recording", self.run_split_recording_tool).pack(side="left", padx=10)

    def placeholder_page(self, name):
        self.header(name, "This workspace is under active development.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        panel = self.card(wrap, fill="x", ipady=18)
        self.label(panel, f"{name.upper()} WORKSPACE", 14, BRAND["gold"], True, anchor="w", padx=18, pady=(16, 6))
        self.label(panel, "This area will be built from real production bottlenecks, not guesses.", 10, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 16))

    def open_recording_checklist(self):
        checklist = CONTENT / "OBS_Workflow_Recording_Checklist.txt"
        if not checklist.exists():
            checklist.write_text("""Putnam Workflow Recording Checklist

1. Open OBS.
2. Select scene: Workflow Analysis.
3. Confirm desktop capture and cameras.
4. Confirm microphone levels.
5. Start Recording.
6. Work naturally. Do not stop for mistakes.
7. Stop recording when the session is done.
8. Use Putnam Platform splitter if the file is too large.
9. Record cards completed, bottlenecks, and notes.

Goal: Capture the real listing workflow for process improvement and content creation.
""", encoding="utf-8")
        append_activity("Opened OBS recording checklist")
        try:
            os.startfile(checklist)
        except Exception:
            messagebox.showinfo("OBS Checklist", str(checklist))

    def pricing_page(self):
        self.header("Pricing", "Analyze CardUploader exports, validate pricing, and prepare upload-ready eBay CSV files.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        note = self.card(wrap, fill="x", pady=(0, 12), ipady=8)
        self.label(note, "FAST PATH", 11, BRAND["gold"], True, anchor="w", padx=18, pady=(10, 2))
        self.label(note, "Home is now the fastest way to analyze a CardUploader export: use Analyze Latest CardUploader Export or drop the CSV there.", 9, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 10))
        self.make_drop_zone(wrap, "DROP CSV HERE", self.browse)

        info = self.card(wrap, fill="x", pady=(0, 16), ipady=10)
        self.info_var = tk.StringVar(value="No CSV loaded.")
        self.label(info, "LOADED FILE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 2))
        tk.Label(info, textvariable=self.info_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 10), justify="left").pack(anchor="w", padx=18, pady=(0, 12))

        flow = self.card(wrap, fill="x", pady=(0, 16), ipady=10)
        self.label(flow, "WORKFLOW", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 2))
        self.flow_var = tk.StringVar(value="1. Load CSV  â†’  2. Detect Type  â†’  3. Market Intelligence  â†’  4. Export")
        tk.Label(flow, textvariable=self.flow_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(0, 12))

        actions = tk.Frame(wrap, bg=BRAND["bg"])
        actions.pack(fill="x", pady=(2, 12))
        tk.Button(actions, text="â–¶ Analyze & Prepare eBay CSV", bg=BRAND["blue"], fg="white",
                  activebackground=BRAND["blue2"], relief="flat", font=("Segoe UI", 12, "bold"),
                  padx=18, pady=12, command=self.auto_run).pack(side="left")
        self.action_button(actions, "Open Completed Jobs", lambda: os.startfile(COMPLETED)).pack(side="left", padx=12)
        self.action_button(actions, "Open Incoming Files", lambda: os.startfile(INCOMING)).pack(side="left")
        self.result_var = tk.StringVar(value="")
        tk.Label(wrap, textvariable=self.result_var, bg=BRAND["bg"], fg=BRAND["muted"],
                 font=("Segoe UI", 10), justify="left").pack(anchor="w", pady=(4, 0))

    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not p:
            return
        self.load(p)

    def load(self, p):
        self.loaded = Path(p)
        self.rows = read_csv(p)
        self.detected = detect_type(self.rows)
        try:
            self.info_var.set(f"{self.loaded.name}\nDetected: {self.detected}\nRows: {len(self.rows)}")
        except Exception:
            pass
        self.status.set("CSV loaded. Ready to analyze.")

    def auto_run(self):
        if not self.loaded:
            self.browse()
            if not self.loaded:
                return
        try:
            if self.detected == "carduploader_new":
                self.status.set("Running price audit and market intelligence...")
                self.update()
                job, rows, changes, opp = audit_new_listing(self.loaded, use_market=True)
                try:
                    self.flow_var.set(f"âœ“ Loaded {rows} rows  â†’  âœ“ CardUploader export  â†’  âœ“ Market Intelligence complete  â†’  âœ“ Output ready")
                    self.result_var.set(f"Complete.\nRows: {rows}\nFloor changes: {changes}\nMarket opportunities: {opp}\nOutput: {job}")
                except Exception:
                    pass
                self.status.set(f"Complete. Floor changes: {changes}. Market opportunities: {opp}.")
                messagebox.showinfo("Putnam OS", f"Analysis complete.\nRows: {rows}\nFloor changes: {changes}\nMarket opportunities: {opp}\n\nOutput folder:\n{job}")
                os.startfile(job)
            else:
                messagebox.showwarning("Putnam OS", "This workflow currently analyzes CardUploader new-listing CSVs. Existing listing revision support remains available through the pricing engine.")
        except Exception as e:
            self.status.set("Error.")
            messagebox.showerror("Putnam OS", str(e))


if __name__ == "__main__":
    append_activity(f"Putnam OS launched v{APP_VERSION}")
    PutnamOS().mainloop()

