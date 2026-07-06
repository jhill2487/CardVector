from pathlib import Path
import argparse, os
from bulk_price_engine import preview_file, run_revision, find_root
from Platform.putnam_paths import PUTNAM_OS_DIR

parser = argparse.ArgumentParser()
parser.add_argument("csv", nargs="?", help="Path to eBay Active Listings CSV")
parser.add_argument("--preview", action="store_true")
args = parser.parse_args()
root = find_root()
config = PUTNAM_OS_DIR / "System" / "config" / "pricing_ladder.json"
if not args.csv:
    print("Paste or drag your eBay CSV path here:")
    args.csv = input("CSV path: ").strip().strip('"')
if args.preview:
    summary, _, _ = preview_file(args.csv, root, config)
    print(summary)
else:
    summary = run_revision(args.csv, root, config, PUTNAM_OS_DIR / "Completed Jobs")
    print("Done")
    print(summary["job_dir"])
    try: os.startfile(summary["job_dir"])
    except Exception: pass
