# Phase 5 CardVector/CardUploader Boundary

```text
CardVector desktop UI
  -> InventoryApplication
    -> CardUploaderInventoryService
      -> CardUploader export snapshot (read-only)
```

For legacy capture-location behavior:

```text
CardVector desktop UI
  -> InventoryApplication
    -> registered ETB projection delegates
      -> existing JSON/Supabase projection
```

Requests and results are synchronous in Phase 5. Snapshot provenance includes
source path, import timestamp, and source-row hash. Errors remain explicit.
Cancellation and events use the existing `ExecutionContext`; snapshot loads
publish `inventory.snapshot_loaded`.

Pagination, version tokens, conflict metadata, remote retries, and offline/live
sync status cannot be truthfully implemented without a supported CardUploader
API. Their absence is represented by provider capabilities, not silent local
behavior.
