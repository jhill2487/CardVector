# Phase 6 Persistence Design

## Decision

Use a dedicated atomic JSON record per batch under:

`Platform/Putnam_OS/System/data/inventory_conversion/batch_workflows/`

This is an existing ignored runtime-data root. No production record is created
until an operator reaches an existing milestone callback.

## Contract

- filename: validated `batch_id` plus `.json`
- schema version: `1`
- encoding: UTF-8
- write: temporary sibling plus atomic replace
- duplicate create: explicit `DuplicateBatchError`
- missing record: explicit `BatchWorkflowNotFoundError`
- corrupt/read/write failure: sanitized `BatchWorkflowPersistenceError`
- list: newest `updated_at` first

The repository is injected into the service. Tests use temporary directories.
No SQLite/Supabase schema or production database is changed.

## Retention And Backup

Records follow current physical-conversion runtime retention. Git does not track
them. Existing backup policy for runtime data applies; Git history is not the
runtime backup.

## Migration

No legacy record is rewritten. `cardvector_workflow.json` remains a temporary
dashboard compatibility record until a later approved presentation/runtime
migration.
