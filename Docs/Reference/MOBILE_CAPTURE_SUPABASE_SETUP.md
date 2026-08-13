# Mobile Capture Supabase Setup

Status: Retired historical setup notes

Date: 2026-07-13

Retired: 2026-08-13

## Scope

CardVector Mobile Capture has been retired. Phone camera and camera-roll batch
creation now belong in CardUploader. This document remains historical context
for the old Supabase-backed implementation and should not be used to enable a
new public capture workflow.

Previously, Mobile Capture used Supabase for authenticated mobile uploads,
capture-session metadata, and original-image storage.

GitHub Pages remains the static host for `cardvector.app`, but the browser no
longer publishes `Docs/mobile-capture-config.js` or starts the mobile capture
camera flow. Service-role credentials remain desktop/server-only when retained
for migration, diagnostics, or historical cleanup.

## Required Supabase Resources

- Supabase Auth with operator accounts.
- Table: `mobile_capture_sessions`.
- Table: `mobile_capture_images`.
- Table: `cardvector_etbs`.
- Table: `cardvector_locations`.
- Table: `cardvector_location_operators`.
- Storage bucket: `mobile-capture-originals`.

## Environment Variables

Static web configuration:

- Retired. `Docs/mobile-capture-config.js` is no longer published.

Desktop queue processor:

- `CARDVECTOR_SUPABASE_URL`
- `CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY`

The service-role key must never be committed and must never be exposed in browser JavaScript.

## SQL Migration

The reproducible setup now lives in:

```text
supabase/migrations/20260713153000_mobile_capture.sql
supabase/migrations/20260716090000_mobile_capture_type.sql
supabase/migrations/20260716130000_mobile_location_registry.sql
```

Run those migrations in the Supabase SQL editor or through the Supabase CLI after linking the project. The base migration creates the tables, indexes, lifecycle checks, trigger-based compatibility aliases, RLS policies, private storage bucket, MIME/size limits, and storage object policies. The capture-type migration adds the explicit Phase 2 workflow field.

Supported `mobile_capture_sessions.capture_type` values:

- `NEW_CAPTURE`
- `PHYSICAL_INVENTORY`

Existing blank or older sessions default to `PHYSICAL_INVENTORY` for backward-compatible desktop staging.

The location migration adds private authenticated ETB/location reads and the
authorized, atomic `cardvector_create_next_location` RPC. Production requires an
explicit operator authorization row and an initial desktop `sync-locations`
run. See `Docs/Reference/MOBILE_LOCATION_SYNC.md`.

## Live Camera Viewport Contract

Live-camera stills use the same centered `object-fit: cover` viewport shown on
screen. CardVector reads the native video dimensions and rendered preview size,
then draws only the visible centered source rectangle to a JPEG canvas at up to
1800 pixels on its longest edge and quality 0.90.

The 63:88 card outline is a positioning guide layered over the video and is not
drawn into the saved image. Images selected through Photo Library are preserved
as selected and are not processed through the live-camera viewport crop.

Detailed setup and validation steps live in:

```text
supabase/README.md
```

The desktop processor uses the service-role key, which bypasses RLS for queue listing, atomic claim, image download, and status updates.

## Desktop Queue Commands

List pending sessions:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py list
```

Claim and stage one session:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py process <capture_session_id>
```

After the existing Physical Inventory Conversion workflow has processed the staged images:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py complete <capture_session_id>
```

If processing fails:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py fail <capture_session_id> --message "reason"
```

Synchronize ETB/location identity:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py sync-locations
```

## Runtime Paths

The desktop processor writes outside Git:

```text
<USERENVIRONMENT>/MobileCapture/Pending/
<USERENVIRONMENT>/MobileCapture/Processing/
<USERENVIRONMENT>/MobileCapture/Converted/
<USERENVIRONMENT>/MobileCapture/Failed/
<USERENVIRONMENT>/Capture/
<USERENVIRONMENT>/Capture/Physical_Inventory_Conversion/
```

Original uploaded images are retained in Supabase Storage and are also copied into the local processing folder when staged.

`NEW_CAPTURE` sessions stage under `<USERENVIRONMENT>/Capture/MM.DD.YY`. `PHYSICAL_INVENTORY` sessions stage under `<USERENVIRONMENT>/Capture/Physical_Inventory_Conversion/MM.DD.YY`. Additional same-day sessions use `.1`, `.2`, and so on.

The migration configures the bucket as private with a 25 MB object limit and allows common phone image formats: JPEG, PNG, HEIC, HEIF, and WebP.

Storage object paths are scoped by operator user ID:

```text
mobile-capture-originals/{operator_user_id}/{etb_location}/{capture_session_id}/{sequence_number}-{image_id}.{extension}
```
