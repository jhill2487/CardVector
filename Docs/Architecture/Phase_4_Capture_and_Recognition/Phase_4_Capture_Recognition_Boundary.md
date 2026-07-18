# Phase 4 Capture And Recognition Boundary

## Permanent Boundary

```text
Desktop/mobile source
    -> cardvector.application.CaptureApplication
    -> cardvector.capture.CaptureService
    -> proven desktop/mobile capture implementation
    -> capture session + image references
    -> CardUploader recognition handoff adapter
    -> external CardUploader
    -> existing CardUploader CSV import
    -> Processing / Marketplace Intelligence
```

Capture ends when images, pairing metadata, session metadata, and a stable
capture folder are ready for downstream use.

Recognition begins outside CardVector when CardUploader receives those images.
CardVector resumes orchestration when the existing CardUploader CSV is imported.

## Capture Input and Output

Current inputs remain unchanged:

- desktop session start and explicit front/back/next-side operations;
- OBS screenshot bytes;
- mobile Supabase session/image rows;
- existing capture type and layout values;
- existing ETB/location metadata.

Current outputs remain unchanged:

- dated Capture folder;
- `000001_front.jpg` / `000001_back.jpg` naming;
- `capture_session.json`;
- `mobile_capture_manifest.json`;
- optional physical-inventory conversion metadata;
- existing status and error strings.

## Stable Identifiers

- `capture_session_id` remains the cloud/local correlation ID when present.
- Desktop sessions continue to use the dated folder and session metadata.
- `card_number` and `side` preserve image-pair identity.
- `capture_type` remains `NEW_CAPTURE` or `PHYSICAL_INVENTORY`.
- `capture_layout` remains `FRONT_ONLY` or `FRONT_BACK`.
- ETB/location values remain metadata owned by Inventory and carried by ID.

## Retry, Cancellation, and Progress

- Atomic mobile claim behavior remains in the proven queue implementation.
- Queue retry remains a controlled `FAILED` to `PENDING_CONVERSION` transition.
- Desktop retake continues moving the last image into `_retakes`.
- UI scheduling/cancellation remains Tkinter presentation behavior.
- Application execution context may publish progress/events but does not alter
  the underlying status or file lifecycle.

## Error Contract

Legacy exceptions and strings remain externally visible:

- `CaptureStudioError`;
- `MobileCaptureError`;
- OBS status/error strings;
- queue terminal status and sanitized error message;
- pair statuses `Complete`, `Waiting for Back`, and `Needs Front`.

The canonical facade must not translate these into new user-visible categories
during Phase 4.

## Recognition Handoff

The CardUploader adapter prepares descriptive handoff metadata only. It does not:

- invoke OCR;
- load a recognition database;
- rank candidates;
- calculate confidence;
- move images;
- open the browser itself;
- parse CardUploader results.

The desktop UI retains its current browser-open behavior and existing CSV import
workflow. This keeps external recognition ownership explicit and testable.
