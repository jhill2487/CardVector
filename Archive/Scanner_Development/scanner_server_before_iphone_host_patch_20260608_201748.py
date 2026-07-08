#!/usr/bin/env python3
"""Putnam Scanner Studio local server - label+scan workflow.
Python 3.14 compatible. No cgi module.

Endpoints:
  GET  /                         -> scanner_studio.html
  POST /api/upload               -> save uploaded image only
  POST /api/save_label           -> save manual border JSON label
  POST /api/scan                 -> save image, optionally save current label_json, then run scanner_core_region_ocr.scan_image
  GET  /studio_uploads/<file>     -> uploaded image access
  GET  /studio_results/<file>     -> generated debug access
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "studio_uploads"
RESULT_DIR = ROOT / "studio_results"
LABEL_DIR = ROOT / "border_training_labels"
HTML_FILE = ROOT / "scanner_studio.html"
CONFIG_FILE = ROOT / "scanner_config.json"

for d in (UPLOAD_DIR, RESULT_DIR, LABEL_DIR):
    d.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "sqlite_path": "database/putnam_pokemon_cloud_ready.sqlite",
    "template_label": "known_good/IMG_7505.json",
    "target_labels": "border_training_labels",
    "strict_mode": True,
    "server_port": 8765,
}

if not CONFIG_FILE.exists():
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")


def load_config() -> dict:
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def safe_name(name: str) -> str:
    name = os.path.basename(name or "upload.jpg")
    keep = []
    for ch in name:
        if ch.isalnum() or ch in "._- ":
            keep.append(ch)
    out = "".join(keep).strip() or "upload.jpg"
    return out.replace(" ", "_")


def base_stem_from_filename(filename: str) -> str:
    """Return stable image base. IMG_7502_113000.JPG -> IMG_7502."""
    stem = Path(filename).stem
    m = re.match(r"^(IMG_\d+)", stem, flags=re.I)
    if m:
        return m.group(1)
    # remove trailing HHMMSS or YYYYMMDD-ish suffixes if present
    stem = re.sub(r"_\d{6,14}$", "", stem)
    return stem


def unique_target(folder: Path, filename: str) -> Path:
    target = folder / safe_name(filename)
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    return folder / f"{stem}_{datetime.now().strftime('%H%M%S')}{suffix}"


def write_json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    raw = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def serve_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    try:
        path = path.resolve()
        if not str(path).startswith(str(ROOT.resolve())):
            handler.send_error(403, "Forbidden")
            return
        if not path.exists() or not path.is_file():
            handler.send_error(404, "File not found")
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
    except Exception as exc:
        handler.send_error(500, str(exc))


def parse_multipart(body: bytes, content_type: str) -> dict:
    """Tiny multipart/form-data parser sufficient for local Studio uploads."""
    m = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type or "")
    if not m:
        raise ValueError("Missing multipart boundary")
    boundary = (m.group(1) or m.group(2)).encode("utf-8")
    delimiter = b"--" + boundary
    fields: dict[str, list[dict]] = {}
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].strip(b"\r\n")
        if b"\r\n\r\n" not in part:
            continue
        raw_headers, data = part.split(b"\r\n\r\n", 1)
        headers = raw_headers.decode("utf-8", "replace").split("\r\n")
        disp = next((h for h in headers if h.lower().startswith("content-disposition:")), "")
        name_m = re.search(r'name="([^"]+)"', disp)
        if not name_m:
            continue
        name = name_m.group(1)
        fn_m = re.search(r'filename="([^"]*)"', disp)
        filename = fn_m.group(1) if fn_m else None
        fields.setdefault(name, []).append({"filename": filename, "data": data})
    return fields


def save_label_payload(payload: dict, preferred_filename: str | None = None) -> Path:
    filename = preferred_filename or payload.get("filename") or "upload.jpg"
    base = base_stem_from_filename(filename)
    payload["filename"] = f"{base}{Path(filename).suffix or '.JPG'}"
    payload.setdefault("trainer_version", "studio_label_scan_patch")
    payload.setdefault("timestamp", datetime.now().isoformat())
    target = LABEL_DIR / f"{base}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def try_run_engine(image_path: Path) -> dict:
    cfg = load_config()
    scan_id = image_path.stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RESULT_DIR / scan_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import importlib.util
        engine_path = ROOT / "scanner_core_region_ocr.py"
        if not engine_path.exists():
            return {"status": "Needs Review", "message": "scanner_core_region_ocr.py not found", "output_dir": str(out_dir)}
        spec = importlib.util.spec_from_file_location("scanner_core_region_ocr", engine_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load scanner_core_region_ocr.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "scan_image"):
            return {"status": "Needs Review", "message": "scanner_core_region_ocr.py has no scan_image()", "output_dir": str(out_dir)}
        result = mod.scan_image(str(image_path), cfg, str(out_dir))
        if not isinstance(result, dict):
            result = {"status": "Needs Review", "message": "Engine returned non-dict", "raw": str(result)}
        result.setdefault("output_dir", str(out_dir))
        return result
    except Exception as exc:
        tb = traceback.format_exc()
        (out_dir / "server_engine_error.txt").write_text(tb, encoding="utf-8")
        return {
            "status": "Needs Review",
            "message": str(exc),
            "error_log": str(out_dir / "server_engine_error.txt"),
            "output_dir": str(out_dir),
            "traceback": tb,
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        if path in ("/", "/index.html", "/scanner_studio.html"):
            serve_file(self, HTML_FILE)
            return
        if path == "/api/config":
            write_json(self, load_config())
            return
        for prefix, folder in (("/studio_uploads/", UPLOAD_DIR), ("/studio_results/", RESULT_DIR)):
            if path.startswith(prefix):
                serve_file(self, folder / path[len(prefix):])
                return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        try:
            if self.path == "/api/config":
                length = int(self.headers.get("content-length", 0))
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                cfg = load_config(); cfg.update(data)
                CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                write_json(self, {"status": "saved", "config": cfg})
                return

            if self.path == "/api/save_label":
                length = int(self.headers.get("content-length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                label_path = save_label_payload(payload)
                write_json(self, {"status": "label_saved", "label_path": str(label_path), "filename": payload.get("filename")})
                return

            if self.path not in ("/api/upload", "/api/scan"):
                self.send_error(404, "Not found")
                return

            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length)
            fields = parse_multipart(body, self.headers.get("content-type", ""))
            image_field = (fields.get("image") or fields.get("file") or [None])[0]
            if not image_field:
                raise ValueError("No image/file multipart field found")
            filename = safe_name(image_field.get("filename") or "upload.jpg")
            target = unique_target(UPLOAD_DIR, filename)
            target.write_bytes(image_field["data"])

            saved_label_path = None
            label_items = fields.get("label_json") or []
            if label_items:
                raw_label = label_items[0]["data"].decode("utf-8", "replace").strip()
                if raw_label:
                    label_payload = json.loads(raw_label)
                    saved_label_path = save_label_payload(label_payload, preferred_filename=filename)

            if self.path == "/api/upload":
                write_json(self, {"status": "image_received", "filename": target.name, "saved_to": str(target), "bytes": len(image_field["data"])})
                return

            result = try_run_engine(target)
            result["upload"] = {"filename": target.name, "bytes": len(image_field["data"]), "saved_to": str(target)}
            if saved_label_path:
                result["saved_label_path"] = str(saved_label_path)
            write_json(self, result)
        except Exception as exc:
            write_json(self, {"status": "server_error", "message": str(exc), "traceback": traceback.format_exc()}, status=500)


def main() -> None:
    cfg = load_config()
    port = int(cfg.get("server_port", 8765))
    print(f"Putnam Scanner Studio label+scan server running at http://127.0.0.1:{port}")
    print("Python 3.14 compatible. Current manual border can be sent with /api/scan as label_json.")
    print(f"Root: {ROOT}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
