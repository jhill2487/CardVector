# Phase 5 Architecture Decision

The project owner superseded the prior target assumption that CardVector would
own inventory. Accepted ADR
[`CV-ADR-021`](../CV-ADR-021-carduploader-inventory-ownership.md) establishes:

- CardUploader owns managed inventory.
- CardVector owns inventory presentation and workflow orchestration.
- `cardvector.integrations.carduploader` is the provider boundary.
- `cardvector.application.InventoryApplication` is the UI-facing facade.
- `Platform/cardvector/inventory` must not be created.
- Existing ETB JSON/Supabase state is a temporary capture/location projection.

No live CardUploader inventory API was found in the repository. Phase 5
therefore exposes supported read-only snapshot capabilities and explicitly
reports unsupported mutation, reservation, allocation, pick confirmation, and
live synchronization capabilities.
