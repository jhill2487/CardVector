# Supabase Capture/Location Registry Migration Paused Status

Status: Paused and archived

Decision: `Docs/Architecture/CV-ADR-026-pause-supabase-location-registry-and-retire-cardvector-operating-workflows.md`

Date: 2026-09-01

## Summary

The Supabase capture/location registry migration remains preserved as
historical and restartable work, but it is no longer the active next migration
path.

The project owner confirmed that CardVector is no longer used for capture,
listing, or pricing operating workflows. CardUploader now owns the active
capture, recognition, managed inventory, standardized listing, and automatic
eBay synchronization workflow.

## Operational Rule

Do not run production capture/location registry commands from this folder unless
a future ADR reactivates the migration and the project owner explicitly approves
the exact commands.

Blocked commands include:

```powershell
supabase db push
python Tools\migrate_legacy_registry_to_supabase.py --apply
```

## Preserved Value

These artifacts remain useful for:

- historical root-cause evidence,
- restart planning if CardVector-owned capture/location workflows return,
- schema and RLS reference,
- migration dry-run methodology,
- rollback and data-protection examples.

## Active Direction

Near-term work should focus on the CardUploader browser/helper workflow,
CardVector.app public content and storefront improvements, and read-only
business analysis where useful. Helper work must not create a competing
inventory, capture, listing, or pricing authority.
