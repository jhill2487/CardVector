-- Deployed migration: private_collector_profile_details
alter table public.cv_profiles
 add column city text not null default '' check (char_length(city) <= 100),
 add column region text not null default '' check (char_length(region) <= 100),
 add column favorite_tcg text not null default '' check (char_length(favorite_tcg) <= 100),
 add column bio text not null default '' check (char_length(bio) <= 1000),
 add column avatar_path text check (avatar_path is null or (char_length(avatar_path) <= 250 and avatar_path like user_id::text || '/%')),
 add column onboarding_completed_at timestamptz;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('cv-private-avatars','cv-private-avatars',false,2097152,array['image/jpeg','image/png','image/webp'])
on conflict(id) do nothing;
create policy cv_avatar_owner_read on storage.objects for select to authenticated using (bucket_id='cv-private-avatars' and (storage.foldername(name))[1]=(select auth.uid())::text);
create policy cv_avatar_owner_insert on storage.objects for insert to authenticated with check (bucket_id='cv-private-avatars' and (storage.foldername(name))[1]=(select auth.uid())::text);
create policy cv_avatar_owner_update on storage.objects for update to authenticated using (bucket_id='cv-private-avatars' and (storage.foldername(name))[1]=(select auth.uid())::text) with check (bucket_id='cv-private-avatars' and (storage.foldername(name))[1]=(select auth.uid())::text);
create policy cv_avatar_owner_delete on storage.objects for delete to authenticated using (bucket_id='cv-private-avatars' and (storage.foldername(name))[1]=(select auth.uid())::text);
