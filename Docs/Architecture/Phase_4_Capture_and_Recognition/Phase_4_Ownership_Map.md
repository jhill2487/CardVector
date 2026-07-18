# Phase 4 Ownership Map

| Responsibility | Canonical owner | Compatibility implementation | Phase 4 result |
| --- | --- | --- | --- |
| Workflow coordination | `Platform/cardvector/application/capture.py` | Tkinter callbacks in `putnam_os.py` | Application facade active; widgets remain |
| Desktop image acquisition | `Platform/cardvector/capture` | `capture_studio.py` | Delegated without relocation |
| Mobile queue intake | `Platform/cardvector/capture` | `mobile_capture_queue.py` | Delegated without changing atomic claim logic |
| OBS transport | Capture adapter boundary | `obs_connection_manager.py` | Retained unchanged |
| Auto-capture rules | `Platform/cardvector/capture/auto_capture.py` | Legacy names in `putnam_os.py` | Canonical implementation; forwarding wrappers retained |
| Pair metadata | `Platform/cardvector/capture/pairing.py` | Legacy names in `putnam_os.py` | Canonical implementation; forwarding wrappers retained |
| Thumbnail rendering | Future desktop presentation | `putnam_os.py` | Unchanged; it consumes canonical pair metadata |
| Card recognition | External CardUploader | CardUploader website/service | No in-repository engine created |
| Recognition handoff | `Platform/cardvector/integrations/carduploader` | Browser-open method in `putnam_os.py` | Typed adapter active; UI retains browser action |
| CardUploader CSV import | Existing Processing workflow | `putnam_os.py` and existing import services | Unchanged |
| Capture filesystem paths | Existing proven implementations | Capture Studio/mobile queue | Unchanged; Infrastructure migration deferred |
| Capture metadata persistence | Existing proven implementations | Session and manifest JSON | Unchanged |
| Inventory conversion rules | Inventory subsystem | Existing Inventory code | Not migrated |

## Boundary Enforcement

- Capture source modules do not import Tkinter, OCR, archived scanner code, or
  browser control.
- The CardUploader adapter does not import Capture implementations or open the
  browser.
- The Application layer owns sequencing but not subsystem algorithms.
- Marketplace Intelligence remains untouched and canonical for pricing.
