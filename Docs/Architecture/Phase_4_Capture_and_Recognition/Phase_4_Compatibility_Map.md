# Phase 4 Compatibility Map

| Compatibility surface | Canonical target | Why retained | Removal condition |
| --- | --- | --- | --- |
| `capture_studio.CaptureStudioService` | `cardvector.capture.CaptureService` | Proven image/session implementation | Physical relocation approved and parity suite passes |
| `mobile_capture_queue.MobileCaptureQueueService` and CLI | `cardvector.capture.CaptureService` | Proven cloud claim, download, and routing behavior | Automation and CLI use canonical bootstrap |
| Capture helper names in `putnam_os.py` | `cardvector.capture.pairing` and `.auto_capture` | Tests and presentation callbacks import legacy names | Presentation uses canonical imports directly |
| `self.capture_service` | `CaptureApplication` | Existing callbacks use this attribute | Desktop presentation migration |
| `self.mobile_capture_queue_service` | `CaptureApplication` | Existing queue callbacks use this attribute | Desktop presentation migration |
| Standalone Putnam Capture launcher | Unresolved | Separate operator surface and session contract | Operator decision and separately approved migration |
| CardUploader browser handoff | `cardvector.integrations.carduploader` | Browser action remains presentation responsibility | Future presentation migration |

No compatibility surface contains a second Phase 4 algorithm. Existing
implementations remain delegates until a separately approved physical
relocation.
