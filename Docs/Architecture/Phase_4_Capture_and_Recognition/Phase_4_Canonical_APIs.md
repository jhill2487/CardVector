# Phase 4 Canonical APIs

## Public Capture API

`Platform.cardvector.capture` is the canonical Capture import path.

| API | Responsibility | Compatibility behavior |
| --- | --- | --- |
| `CaptureService` | Delegates desktop Capture and mobile queue operations | Returns the proven implementation's values and exceptions unchanged |
| `capture_pair_rows` | Builds ordered front/back display metadata | Preserves status, filenames, paths, ordering, and `latest` marker |
| `capture_pair_status` | Reports the current pair state | Preserves `Ready`, `Waiting for Back`, and `Ready for Next Card` |
| `capture_cards_completed` | Counts complete pair rows | Preserves front-only and front/back completion rules |
| `load_capture_session_file` | Reads capture session JSON defensively | Preserves empty-dictionary fallback |
| `resolve_capture_record_image` | Resolves metadata and filename paths | Accepts the legacy path resolver during migration |
| auto-capture functions | Load/save settings and calculate frame differences | Preserve exact defaults, bounds, thresholds, and errors |

The package exports protocols for the proven desktop and mobile delegates. It
does not define a speculative persistence model or duplicate the established
session dictionaries because no current caller needs a second representation.

## Application API

`Platform.cardvector.application.CaptureApplication` coordinates:

- desktop session start, capture, retake, finish, and OBS status;
- mobile queue listing, location synchronization, staging, completion, failure,
  retry, and local-folder lookup;
- creation of a desktop Capture delegate for inventory conversion;
- non-invasive progress and event publication;
- the external recognition handoff.

The Application layer does not implement image acquisition, queue claims,
filesystem writes, recognition, or inventory rules.

## Recognition API

`Platform.cardvector.integrations.carduploader` exposes:

- `CardUploaderRecognitionAdapter`;
- immutable `RecognitionHandoff`;
- `RecognitionHandoff.to_dict()`.

The handoff records the provider, status, capture folder, capture-session ID,
configured provider URL, timestamp, and carried metadata. It does not claim a
card identity, confidence, candidate, or OCR result.

## Exceptions And Serialization

Phase 4 intentionally preserves `CaptureStudioError`, `MobileCaptureError`, and
their existing call paths. The canonical facade does not translate errors.

Capture session and queue serialization remain owned by the proven delegates.
Recognition handoff serialization uses `RecognitionHandoff.to_dict()` and has
no side effects.
