# Direct Store Checkout Foundation

CardVector.app uses a hybrid storefront model:

1. The public site loads a lightweight static inventory feed for browsing.
2. The cart posts item IDs and quantities to a Supabase Edge Function.
3. The Edge Function re-fetches the feed, validates prices and availability, creates a pending order, and redirects the customer to Stripe Checkout.
4. Stripe Checkout collects email, shipping address, and payment details.
5. The Stripe webhook marks the order paid and ready to ship in Supabase.
6. The webhook creates one private CardUploader/eBay release job per paid order
   item so the downstream helper can remove purchased inventory from the live
   marketplace workflow.

Transactional order, receipt, shipping, and tracking updates are not marketing
messages and do not require promotional opt-in. Promotional email consent is
disabled until Stripe Checkout marketing consent is approved in Stripe.

## Production Setup

Production checkout is not active until these steps are completed:

```powershell
supabase db push
supabase functions deploy create-checkout-session
supabase functions deploy stripe-webhook
supabase secrets set STRIPE_RESTRICTED_KEY=...
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

After Stripe redirects back with `checkout=success`, CardVector.app clears the
browser cart. Cancelled checkout returns keep the browser cart available.

## Safety Notes

- The browser never receives Stripe secret keys or Supabase service-role keys.
- Prefer a Stripe restricted API key (`STRIPE_RESTRICTED_KEY`) with the minimum
  Checkout Session and webhook-related permissions needed by these functions.
  `STRIPE_SECRET_KEY` remains a fallback name for local testing only.
- The browser does not collect card numbers.
- Checkout queues marketplace release jobs after payment. The trusted
  CardUploader executor must still be enabled separately before any live
  CardUploader or eBay inventory state is changed.
- CardUploader remains managed-inventory truth.
- Supabase direct-store order tables are service-role only.
- Supabase direct-store release jobs are service-role only until the private
  helper/executor is wired and validated.
- Shipping confirmation email delivery still needs a transactional email sender
  or a fulfillment workflow that records `tracking_number`, `shipping_carrier`,
  and `shipping_confirmation_sent_at`.
