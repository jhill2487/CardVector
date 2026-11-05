-- Deployed to CardVector Supabase as migration create_collector_profiles.
-- This standalone profile foundation intentionally excludes Want Lists and seller features.
create table public.cv_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '' check (char_length(display_name) <= 80),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.cv_profiles enable row level security;
create policy cv_profiles_select_own on public.cv_profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy cv_profiles_insert_own on public.cv_profiles for insert to authenticated with check ((select auth.uid()) = user_id);
create policy cv_profiles_update_own on public.cv_profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
revoke all on public.cv_profiles from anon;
grant select, insert, update on public.cv_profiles to authenticated;
create function public.cv_set_profile_updated_at() returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end; $$;
revoke all on function public.cv_set_profile_updated_at() from public, anon, authenticated;
create trigger cv_profiles_updated_at before update on public.cv_profiles for each row execute function public.cv_set_profile_updated_at();
