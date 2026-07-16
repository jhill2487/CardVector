-- CardVector Mobile Capture Phase 2 capture-type contract.
--
-- Existing mobile capture sessions predate capture-type selection. Blank or
-- missing capture_type values default to PHYSICAL_INVENTORY so the desktop
-- queue can continue staging older sessions safely.

alter table public.mobile_capture_sessions
  add column if not exists capture_type text not null default 'PHYSICAL_INVENTORY';

update public.mobile_capture_sessions
   set capture_type = 'PHYSICAL_INVENTORY'
 where nullif(capture_type, '') is null;

do $$
begin
  if not exists (
    select 1
      from pg_constraint
     where conname = 'mobile_capture_sessions_capture_type_chk'
       and conrelid = 'public.mobile_capture_sessions'::regclass
  ) then
    alter table public.mobile_capture_sessions
      add constraint mobile_capture_sessions_capture_type_chk
      check (capture_type in ('NEW_CAPTURE', 'PHYSICAL_INVENTORY'));
  end if;
end;
$$;
