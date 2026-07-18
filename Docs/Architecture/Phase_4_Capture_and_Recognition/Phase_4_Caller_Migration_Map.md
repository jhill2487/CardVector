# Phase 4 Caller Migration Map

| Caller | Old target | New target | Preserved contract | Validation |
| --- | --- | --- | --- | --- |
| `build_application_runtime` | Direct UI construction only | Registers `CaptureApplication(CaptureService(...))` | Same Capture Studio and mobile queue classes | Composition test passed |
| `PutnamOS.__init__` | Direct `CaptureStudioService` and `MobileCaptureQueueService` instances | Resolves one `CaptureApplication` | Existing attribute names alias the facade | Desktop contract and smoke tests passed |
| Desktop Capture callbacks | `CaptureStudioService` | `CaptureApplication` -> `CaptureService` -> same delegate | Session/result/error/file behavior | Capture Studio and characterization passed |
| Mobile queue callbacks | `MobileCaptureQueueService` | `CaptureApplication` -> `CaptureService` -> same delegate | Atomic claim, routing, status, manifests | 25 queue tests passed |
| Inventory conversion Capture factory | Direct `CaptureStudioService(...)` | `CaptureApplication.create_desktop_service(...)` | Same root, placeholder flag, OBS manager | Factory contract test passed |
| `open_carduploader` | Direct configuration lookup | `CaptureApplication.prepare_recognition_handoff` | Same URL and browser-open behavior | Handoff contract test passed |
| Pair/status helpers | Local algorithms in `putnam_os.py` | Canonical pairing functions | Same dictionaries and status vocabulary | Legacy/canonical tests passed |
| Auto-capture helpers | Local algorithms in `putnam_os.py` | Canonical auto-capture functions | Same normalization, thresholds, frame math | Legacy/canonical tests passed |

Tkinter methods still use `self.capture_service` and
`self.mobile_capture_queue_service`. Both names now reference the same
`CaptureApplication` instance, preserving existing callbacks without moving
views.

The standalone `Putnam_Capture.py` and `obs_capture_autocrop.py` tools remain
unchanged. Their different paths and session formats require a separate
operator decision and characterization before migration.
