# Phase 4 Database Dependencies

Desktop Capture Studio uses session JSON and image files; it does not use a
database.

Mobile capture uses Supabase tables, Storage, RLS, and RPC contracts through the
existing queue implementation. Phase 4 does not change schema, credentials,
queries, atomic claim predicates, or write behavior.

CardVector has no production recognition database. CardUploader remains
external. The Phase 4 adapter does not connect to a database and does not
inspect recognition data.

Archived scanner experiments reference varying SQLite/CSV/XLSX schemas and
machine-specific datasets. They are not production dependencies and were not
opened, copied, migrated, or imported.

Validation used mocked mobile HTTP behavior and temporary Capture directories.
No schema migration was created or applied, and no production database was
opened for write.
