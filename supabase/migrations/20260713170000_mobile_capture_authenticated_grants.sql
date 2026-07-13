-- CardVector Mobile Capture authenticated table privileges.
--
-- RLS policies decide which rows authenticated operators may access. These
-- grants provide the table-level privileges Postgres requires before RLS can
-- evaluate those policies.

alter table public.mobile_capture_sessions enable row level security;
alter table public.mobile_capture_images enable row level security;

grant usage on schema public to authenticated;

grant select, insert, update
  on table public.mobile_capture_sessions
  to authenticated;

grant select, insert, update
  on table public.mobile_capture_images
  to authenticated;
