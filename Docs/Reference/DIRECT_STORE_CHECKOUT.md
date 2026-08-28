# Direct Store Checkout Foundation

CardVector.app uses a hybrid storefront model:

1. The public site loads a lightweight static inventory feed for browsing.
2. The cart posts item IDs and quantities to a Supabase Edge Function.
3. The Edge Function re-fetches the feed, validates prices and availability, creates a pending order, and redirects the customer to Stripe Checkout.
4. Stripe Checkout collects email, shipping address, payment details, and optional promotional-email consent.
5. The Stripe webhook marks the order paid and ready to ship in Supabase.

Transactional order, receipt, shipping, and tracking updates are not marketing
messages and do not require promotional opt-in. Promotional email consent is
collected separately through Stripe Checkout.

## Production Setup

Production checkout is not active until these steps are completed:

```powershell
supabase db push
supabase functions deploy create-checkout-session
supabase functions deploy stripe-webhook
supabase secrets set STRIPE_SECRET_KEY=...
supabase secrets set STRIPE_WEBHOOK_SECRET=...
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=...
supabase secrets set CARDVECTOR_SITE_URL=https://cardvector.app
supabase secrets set CARDVECTOR_ALLOWED_ORIGIN=https://cardvector.app
supabase secrets set DIRECT_STORE_FEED_URL=https://cardvector.app/content/shop/direct-inventory.json
```

The Stripe webhook endpoint should point to:

```text
https://iqdpfgpkagjxzedfxrvn.supabase.co/functions/v1/stripe-webhook
```

Listen for at least:

- `checkout.session.completed`
- `checkout.session.expired`

## Safety Notes

- The browser never receives Stripe secret keys or Supabase service-role keys.
- The browser does not collect card numbers.
- Checkout does not automatically remove marketplace availability.
- CardUploader remains managed-inventory truth.
- Supabase direct-store order tables are service-role only.
- Shipping confirmation email delivery still needs a transactional email sender
  or a fulfillment workflow that records `tracking_number`, `shipping_carrier`,
  and `shipping_confirmation_sent_at`.
