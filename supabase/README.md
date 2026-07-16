# CardVector Supabase Setup

Status: Production setup package

This folder contains the reproducible Supabase setup for CardVector Mobile Capture.

## Current Scope

Mobile Capture uses:

- Supabase Auth for operator sign-in.
- Postgres tables for capture-session and image metadata.
- A private Storage bucket for original images.
- Desktop queue access through a machine-local service-role key.

## Migration

Apply:

```text
supabase/migrations/20260713153000_mobile_capture.sql
supabase/migrations/20260713170000_mobile_capture_authenticated_grants.sql
supabase/migrations/20260716090000_mobile_capture_type.sql
```

The migration creates or safely reconciles:

- `public.mobile_capture_sessions`
- `public.mobile_capture_images`
- indexes and uniqueness constraints
- lifecycle status validation
- explicit `capture_type` validation for `NEW_CAPTURE` and `PHYSICAL_INVENTORY`
- `updated_at` trigger behavior
- RLS policies for authenticated operators
- private `mobile-capture-originals` bucket
- Storage policies for authenticated operator-owned paths

## Required Supabase Project Steps

1. Create or choose the CardVector Supabase project.
2. Create one operator Auth user for Jared through the Supabase dashboard or invite flow.
3. Run the migration SQL in the Supabase SQL editor, or install/login/link Supabase CLI and run:

```powershell
supabase link --project-ref <project-ref>
supabase db push
```

4. Confirm the private bucket exists:

```text
mobile-capture-originals
```

5. Confirm table RLS is enabled and policies exist.

## Browser Configuration

Only browser-safe values go in:

```text
Docs/mobile-capture-config.js
```

Allowed values:

- Supabase project URL
- Supabase anon/publishable key
- `mobile-capture-originals` bucket name

Never put a service-role key, database password, GitHub token, eBay credential, or private secret in this file.

## Desktop Configuration

Set these on each production workstation:

```text
CARDVECTOR_SUPABASE_URL
CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY
```

Temporary PowerShell session:

```powershell
$env:CARDVECTOR_SUPABASE_URL = "https://your-project-ref.supabase.co"
$env:CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY = "service-role-key-kept-private"
```

Persistent Windows user environment variables:

```powershell
[Environment]::SetEnvironmentVariable("CARDVECTOR_SUPABASE_URL", "https://your-project-ref.supabase.co", "User")
[Environment]::SetEnvironmentVariable("CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY", "service-role-key-kept-private", "User")
```

Close and reopen PowerShell after setting persistent variables.

## Validation Commands

List pending sessions:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py list
```

Process a pending session:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py process <capture_session_id>
```

Mark complete only after the staged Physical Inventory Conversion input is verified:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py complete <capture_session_id>
```

Mark failed if staging or conversion fails:

```powershell
py Platform\Putnam_OS\System\tools\mobile_capture_queue.py fail <capture_session_id> --message "reason"
```

## Storage Path Contract

The browser stores originals under:

```text
{operator_user_id}/{etb_location}/{capture_session_id}/{sequence}-{image_id}.{extension}
```

The bucket is private. Desktop downloads use the service-role key outside Git.

## First Production Validation

Use non-sensitive test images:

1. Open an existing `/location/{ETB}/{A-J}` QR route on the phone.
2. Choose `New Inventory Capture` or `Physical Inventory Conversion`.
3. Sign in as the operator.
4. Capture three test images with the custom shutter or choose from Photo Library.
5. Remove one image.
6. Finish the session and upload two images.
7. Confirm the session reaches `PENDING_CONVERSION` with the selected `capture_type`.
8. On the desktop, list and process the session.
9. Confirm originals download under `<USERENVIRONMENT>/MobileCapture/Processing/`.
10. Confirm `capture_session.json` is staged under `<USERENVIRONMENT>/Capture/` for `NEW_CAPTURE` or `<USERENVIRONMENT>/Capture/Physical_Inventory_Conversion/` for `PHYSICAL_INVENTORY`.
11. Confirm the ETB location ID survives in the staged conversion session.
12. Mark complete only after processing succeeds.
