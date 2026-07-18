# Phase 4 Filesystem Side Effects

## Preserved Production Effects

| Workflow | Existing effect | Phase 4 behavior |
| --- | --- | --- |
| Desktop session start | Creates dated session folder and session JSON | Same delegate and path rules |
| Desktop capture | Writes six-digit front/back JPEG and updates JSON | Same delegate |
| Retake | Moves latest image into `_retakes` | Same delegate |
| Session finish | Persists finished timestamp | Same delegate |
| Mobile queue | Downloads to atomic staging, writes manifests, promotes to dated Capture folder | Same queue implementation |
| Physical inventory | Routes under `Physical_Inventory_Conversion` | Same queue/Capture Studio rules |
| Pair thumbnails | Reads session JSON and image metadata; scans JPEG fallback | Same fields, ordering, and fallback logging |
| Auto-capture settings | Reads/writes the same configured JSON path | Legacy wrapper supplies the same path |

All file-writing tests use `tempfile.TemporaryDirectory`. OBS and mobile network
operations use existing mocks. No test points at the repository `Capture`
folder, operator image folders, production queue data, or operational JSON.

The same proven delegates perform every production file write. Characterization
tests confirm exact session keys, filenames, record order, pair status, and
capture layout.
