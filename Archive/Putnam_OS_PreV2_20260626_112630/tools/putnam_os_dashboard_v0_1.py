import os
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

VERSION = "v0.1"

def find_root():
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".putnam_root").exists():
            return parent

    return Path.home() / "OneDrive" / "PutnamCollectibles"

ROOT = find_root()

BUTTONS = [
    ("📸 Start Photography Session", "Putnam_Content"),
    ("🃏 Process with CardUploader", None),
    ("📝 Review Listings", "Putnam_Listing_Optimizer"),
    ("📦 Shipping Workflow", "TCG_Automation"),
    ("🎥 Content Studio", "Putnam_Content"),
    ("📊 Reports / Dashboard", "docs"),
    ("📚 Standards", "Putnam_Standards"),
    ("📁 Open Putnam Root", "."),
]

def open_path(relative):
    if relative is None:
        messagebox.showinfo(
            "Manual Step",
            "Open CardUploader in your browser/app, then process today's photo batch."
        )
        return

    path = ROOT / relative
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    subprocess.Popen(f'explorer "{path}"')

def main():
    app = tk.Tk()
    app.title(f"Putnam OS Dashboard {VERSION}")
    app.geometry("620x620")
    app.configure(bg="#111111")

    title = tk.Label(
        app,
        text="PUTNAM OPERATING SYSTEM",
        font=("Arial", 22, "bold"),
        bg="#111111",
        fg="white"
    )
    title.pack(pady=(25, 5))

    subtitle = tk.Label(
        app,
        text=f"Root: {ROOT}",
        font=("Arial", 9),
        bg="#111111",
        fg="#aaaaaa"
    )
    subtitle.pack(pady=(0, 20))

    today = tk.Label(
        app,
        text="Today's Workflows",
        font=("Arial", 14, "bold"),
        bg="#111111",
        fg="#ffffff"
    )
    today.pack(pady=(0, 10))

    for label, rel in BUTTONS:
        btn = tk.Button(
            app,
            text=label,
            font=("Arial", 13),
            width=34,
            height=2,
            command=lambda r=rel: open_path(r)
        )
        btn.pack(pady=5)

    footer = tk.Label(
        app,
        text="v0.1 — workflow launcher only",
        font=("Arial", 9),
        bg="#111111",
        fg="#777777"
    )
    footer.pack(side="bottom", pady=15)

    app.mainloop()

if __name__ == "__main__":
    main()
