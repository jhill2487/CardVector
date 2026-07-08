from pathlib import Path
import os
import stat
import json
import hashlib

TARGET = Path("scanner_studio.html")
BACKUP = Path("scanner_studio_before_copy_buttons_patch.html")

if not TARGET.exists():
    raise SystemExit("ERROR: scanner_studio.html not found. Run this from the PutnamCollectibles project folder.")

s = TARGET.read_text(encoding="utf-8")

if "copySummary" in s and "copyRaw" in s:
    print("Copy buttons already appear to be installed. No changes made.")
    raise SystemExit(0)

# Remove read-only flag if project locks marked the file read-only.
try:
    os.chmod(TARGET, stat.S_IWRITE | stat.S_IREAD)
except Exception:
    pass

BACKUP.write_text(s, encoding="utf-8")

old_result = '<div class="card"><b>Result</b><pre id="result">{}</pre></div>'
new_result = '''<div class="card"><b>Result</b>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;">
<button id="copySummary" type="button">Copy Summary</button>
<button id="copyRaw" type="button">Copy Raw JSON</button>
</div>
<pre id="result">{}</pre></div>'''

if old_result not in s:
    raise SystemExit("ERROR: Could not find Result panel markup. No changes made.")

s = s.replace(old_result, new_result, 1)

# Store the most recent JSON result when scan/save actions update the Result panel.
s = s.replace(
    "document.getElementById('result').textContent=JSON.stringify(j,null,2); links(j);",
    "window.lastScanResult=j; document.getElementById('result').textContent=JSON.stringify(j,null,2); links(j);"
)
s = s.replace(
    "document.getElementById('result').textContent=JSON.stringify(j,null,2); setStatus('Manual border label saved','ok')",
    "window.lastScanResult=j; document.getElementById('result').textContent=JSON.stringify(j,null,2); setStatus('Manual border label saved','ok')"
)

copy_js = r'''
<script>
window.lastScanResult = window.lastScanResult || null;

function studioResultValue(v) {
  return (v === undefined || v === null || v === "") ? "" : String(v);
}

function buildStudioSummary(j) {
  j = j || window.lastScanResult || {};
  const match = j.match || {};
  const ocr = j.ocr || {};
  const lines = [];

  lines.push("Status: " + studioResultValue(match.status || j.status || "Unknown"));

  if (match.card_name || match.set_name || match.card_number) {
    lines.push("Card: " + studioResultValue(match.card_name));
    lines.push("Set: " + studioResultValue(match.set_name));
    lines.push("Number: " + studioResultValue(match.card_number));
    lines.push("Confidence: " + studioResultValue(match.confidence));
    if (match.reason) lines.push("Reason: " + match.reason);
  } else {
    lines.push("Card: Needs Review");
    if (match.reason) lines.push("Reason: " + match.reason);
  }

  lines.push("OCR Name: " + studioResultValue(ocr.name));
  lines.push("OCR Number: " + studioResultValue(ocr.number));
  lines.push("OCR Set Code: " + studioResultValue(ocr.setcode));

  if (j.geometry_status) lines.push("Geometry: " + j.geometry_status);

  const candidates = j.candidates || [];
  if (candidates.length) {
    lines.push("");
    lines.push("Top Candidates:");
    candidates.slice(0, 5).forEach((c, i) => {
      lines.push(
        (i + 1) + ". " +
        studioResultValue(c.card_name) + " | " +
        studioResultValue(c.set_name) + " | " +
        studioResultValue(c.card_number) +
        (c.score !== undefined ? " | score " + c.score : "")
      );
    });
  }

  return lines.join("\n");
}

async function copyStudioText(text) {
  try {
    await navigator.clipboard.writeText(text);
    const st = document.getElementById("status");
    if (st) st.textContent = "Copied to clipboard.";
  } catch (err) {
    const fallback = document.createElement("textarea");
    fallback.value = text;
    document.body.appendChild(fallback);
    fallback.select();
    document.execCommand("copy");
    document.body.removeChild(fallback);
    const st = document.getElementById("status");
    if (st) st.textContent = "Copied to clipboard.";
  }
}

document.addEventListener("click", function(e) {
  if (e.target && e.target.id === "copySummary") {
    copyStudioText(buildStudioSummary(window.lastScanResult));
  }
  if (e.target && e.target.id === "copyRaw") {
    const raw = document.getElementById("result");
    copyStudioText(raw ? raw.textContent : JSON.stringify(window.lastScanResult || {}, null, 2));
  }
});
</script>
'''

if "</body>" in s:
    s = s.replace("</body>", copy_js + "\n</body>", 1)
else:
    s = s + copy_js

TARGET.write_text(s, encoding="utf-8")

print("SUCCESS: Copy Result buttons added to scanner_studio.html")
print(f"Backup created: {BACKUP}")
print("")
print("Added buttons:")
print("- Copy Summary")
print("- Copy Raw JSON")
print("")
print("Next:")
print("1. Refresh Studio with Ctrl+F5")
print("2. Run a scan")
print("3. Click Copy Summary or Copy Raw JSON")

# Optional: update lock manifest to the intentionally changed scanner_studio.html hash
manifest = Path("project_locks/locked_manifest.json")
if manifest.exists():
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        rel = "scanner_studio.html"
        digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()

        updated = False
        if isinstance(data, dict):
            if rel in data and isinstance(data[rel], dict):
                data[rel]["sha256"] = digest
                updated = True
            elif "files" in data and isinstance(data["files"], dict) and rel in data["files"]:
                if isinstance(data["files"][rel], dict):
                    data["files"][rel]["sha256"] = digest
                else:
                    data["files"][rel] = digest
                updated = True
            elif "files" in data and isinstance(data["files"], list):
                for item in data["files"]:
                    if isinstance(item, dict) and item.get("path") == rel:
                        item["sha256"] = digest
                        updated = True

        if updated:
            manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print("")
            print("Updated project_locks manifest for intentional scanner_studio.html layout change.")
        else:
            print("")
            print("NOTE: Could not auto-update lock manifest format. If verify_project_locks fails, rerun install_project_locks.py.")
    except Exception as exc:
        print("")
        print(f"NOTE: Could not update lock manifest automatically: {exc}")
        print("If verify_project_locks fails, rerun install_project_locks.py.")
