# Phase 6 Caller Migration Map

| Caller | Previous target | New target | Preserved behavior |
| --- | --- | --- | --- |
| Mobile queue staged callback | legacy workflow context | legacy context plus `BatchWorkflowApplication.mark_capture_complete` | Same folder, state, UI text, and queue drain |
| Physical conversion finish | conversion JSON and ETB projection | existing writes plus batch capture milestone | Same counts, location completion, and UI |
| Open CardUploader | browser handoff and legacy context | existing handoff plus upload-start milestone | Same URL, stage, and UI |
| CardUploader CSV import success | legacy context and Processing UI | existing flow plus upload-complete and CSV milestones | Same rows, paths, stage, and loaded file |
| New-listing price review launch | Marketplace Intelligence worker | existing worker plus review-start milestone | Same validation, prompt, and pricing |
| Price review success | pricing output and legacy context | existing output plus review-complete milestone | Same result, export, UI, and logging |
| Price review failure | existing status/log/dialog | existing failure plus failed milestone | Same error handling |

`main.py` contains a secondary pricing compatibility UI but no existing
batch-status caller. It remains unchanged.

New milestone persistence is non-blocking at the UI adapter: a repository error
is logged and the original workflow continues.
