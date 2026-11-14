-- Share one artwork image only among distinct printings of the same set + collector number.
-- Card identities (provider_id, card_name, variants) are not merged or modified.
-- Existing RLS on review/catalog tables remains unchanged.
create or replace function cv_internal.validate_shared_artwork_review()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  target_set text;
  target_number text;
begin
  if new.review_status <> 'approved' then
    return new;
  end if;
  if new.candidate_path is null or btrim(new.candidate_path) = '' then
    raise exception 'Approved images require a candidate path';
  end if;
  select set_id, card_number into target_set, target_number
    from public.cv_admin_pokewallet_catalog
   where provider_id = new.provider_id;
  if target_set is null or target_number is null then
    raise exception 'Approved artwork requires a known catalog card identity';
  end if;
  -- Serialize simultaneous approvals for the same R2 object to avoid races.
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.candidate_path,0));
  if exists (
    select 1 from public.cv_admin_image_reviews other
    join public.cv_admin_pokewallet_catalog sibling
      on sibling.provider_id = other.provider_id
    where other.candidate_path = new.candidate_path
      and other.review_status = 'approved'
      and other.provider_id <> new.provider_id
      and (sibling.set_id is distinct from target_set
        or sibling.card_number is distinct from target_number)
  ) then
    raise exception 'Image already belongs to another set or collector number';
  end if;
  return new;
end;
$function$;
revoke all on function cv_internal.validate_shared_artwork_review() from public, anon, authenticated;
drop trigger if exists cv_admin_review_same_artwork_guard on public.cv_admin_image_reviews;
create trigger cv_admin_review_same_artwork_guard
  before insert or update of review_status, candidate_path
  on public.cv_admin_image_reviews
  for each row execute function cv_internal.validate_shared_artwork_review();
-- Former global path uniqueness prevented valid same-artwork finish variants.
-- Cross-card safety is now enforced by the guarded trigger above.
drop index if exists public.cv_admin_image_reviews_unique_approved_path;
