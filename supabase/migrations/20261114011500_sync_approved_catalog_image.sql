-- Keep the private catalog synchronized with approved R2 review decisions.
-- Only authenticated CardVector admin may write review rows (existing RLS).
-- Catalog itself remains read-only to browsers; no public search publication.
create unique index if not exists cv_admin_image_reviews_unique_approved_path
  on public.cv_admin_image_reviews (candidate_path)
  where review_status = 'approved' and candidate_path is not null;

create schema if not exists cv_internal;
revoke all on schema cv_internal from public;
revoke all on schema cv_internal from anon, authenticated;

create or replace function cv_internal.sync_approved_catalog_image()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if new.review_status = 'approved' then
    -- Existing check constraints require a safe relative image path.
    update public.cv_admin_pokewallet_catalog
       set image_status = 'matched',
           image_path = new.candidate_path
     where provider_id = new.provider_id;
  elsif tg_op = 'UPDATE'
      and old.review_status = 'approved'
      and old.candidate_path is not null then
    -- A revoked/rejected decision restores the original missing state
    -- only when it still owns the catalog's image path.
    update public.cv_admin_pokewallet_catalog
       set image_status = 'missing', image_path = null
     where provider_id = new.provider_id
       and image_path = old.candidate_path;
  end if;
  return new;
end;
$function$;

revoke all on function cv_internal.sync_approved_catalog_image() from public;
revoke all on function cv_internal.sync_approved_catalog_image() from anon, authenticated;

drop trigger if exists cv_admin_image_review_catalog_sync on public.cv_admin_image_reviews;
create trigger cv_admin_image_review_catalog_sync
after insert or update of review_status, candidate_path
on public.cv_admin_image_reviews
for each row execute function cv_internal.sync_approved_catalog_image();

-- Backfill already approved images, including Perfect Order Spinarak/Ariados.
update public.cv_admin_pokewallet_catalog as catalog
   set image_status = 'matched', image_path = reviews.candidate_path
  from public.cv_admin_image_reviews as reviews
 where reviews.provider_id = catalog.provider_id
   and reviews.review_status = 'approved'
   and reviews.candidate_path is not null
   and (catalog.image_status is distinct from 'matched'
        or catalog.image_path is distinct from reviews.candidate_path);
