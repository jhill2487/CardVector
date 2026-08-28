import Stripe from "npm:stripe@22.4.0";
import { createClient } from "npm:@supabase/supabase-js@2.45.4";

function env(name: string, fallbackName = ""): string {
  const value = Deno.env.get(name) || (fallbackName ? Deno.env.get(fallbackName) : "");
  if (!value) {
    throw new Error(`${fallbackName ? `${name} or ${fallbackName}` : name} is not configured`);
  }
  return value;
}

function consentStatus(session: Stripe.Checkout.Session): string {
  const value = String(session.consent?.promotions || "").trim();
  return value || "not_collected";
}

async function markEvent(status: string, eventId: string, errorMessage = "", orderId: string | null = null): Promise<void> {
  const supabase = createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { persistSession: false },
  });
  await supabase
    .from("cardvector_direct_store_checkout_events")
    .update({
      processing_status: status,
      processed_at: new Date().toISOString(),
      error_message: errorMessage,
      ...(orderId ? { order_id: orderId } : {}),
    })
    .eq("stripe_event_id", eventId);
}

async function enqueueMarketplaceReleaseJobs(
  supabase: ReturnType<typeof createClient>,
  order: { id: string; public_order_id: string },
): Promise<void> {
  const { data: items, error: itemsError } = await supabase
    .from("cardvector_direct_store_order_items")
    .select("id, item_id, title, quantity, source, source_listing_id, inventory_reference")
    .eq("order_id", order.id);
  if (itemsError) {
    throw itemsError;
  }
  const rows = (items || []).map((item) => ({
    order_id: order.id,
    order_item_id: item.id,
    public_order_id: order.public_order_id,
    target_system: "carduploader",
    target_marketplace: "ebay",
    release_action: "release_purchased_quantity",
    release_status: "pending",
    item_id: item.item_id,
    title: item.title,
    quantity: item.quantity,
    source: item.source || "",
    source_listing_id: item.source_listing_id || "",
    inventory_reference: item.inventory_reference || "",
    metadata: {
      queued_by: "stripe-webhook",
      checkout_session_confirmed_at: new Date().toISOString(),
    },
  }));
  if (!rows.length) {
    throw new Error(`No order items found for order ${order.public_order_id}`);
  }
  const { error: releaseError } = await supabase
    .from("cardvector_direct_store_release_jobs")
    .upsert(rows, { onConflict: "order_item_id", ignoreDuplicates: true });
  if (releaseError) {
    throw releaseError;
  }
}

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const stripe = new Stripe(env("STRIPE_RESTRICTED_KEY", "STRIPE_SECRET_KEY"), {
    apiVersion: "2026-07-29.dahlia",
  });
  const signature = req.headers.get("stripe-signature") || "";
  const rawBody = await req.text();
  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(rawBody, signature, env("STRIPE_WEBHOOK_SECRET"));
  } catch (_error) {
    return new Response("Invalid Stripe signature", { status: 400 });
  }

  const supabase = createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { persistSession: false },
  });

  const session = event.data.object as Stripe.Checkout.Session;
  const { error: recordEventError } = await supabase
    .from("cardvector_direct_store_checkout_events")
    .upsert({
      stripe_event_id: event.id,
      event_type: event.type,
      stripe_checkout_session_id: typeof session.id === "string" ? session.id : "",
      processing_status: "received",
      processed_at: null,
      error_message: "",
      payload: event as unknown as Record<string, unknown>,
    }, { onConflict: "stripe_event_id" });
  if (recordEventError) {
    console.error("webhook event recording failed", recordEventError);
    return new Response("Webhook event recording failed", { status: 500 });
  }

  try {
    if (event.type === "checkout.session.completed") {
      const customerEmail = String(session.customer_details?.email || session.customer_email || "").trim();
      const customerName = String(session.customer_details?.name || "").trim();
      const marketingStatus = consentStatus(session);
      const marketingOptIn = marketingStatus === "opt_in";
      let customerId: string | null = null;

      if (customerEmail) {
        const { data: customer, error: customerError } = await supabase
          .from("cardvector_direct_store_customers")
          .upsert({
            email: customerEmail,
            name: customerName,
            stripe_customer_id: typeof session.customer === "string" ? session.customer : "",
            marketing_opt_in: marketingOptIn,
            marketing_consent_status: marketingStatus,
            marketing_consent_source: "stripe_checkout",
            marketing_consent_at: marketingOptIn ? new Date().toISOString() : null,
            last_order_at: new Date().toISOString(),
          }, { onConflict: "normalized_email" })
          .select("id")
          .single();
        if (customerError) {
          throw customerError;
        }
        customerId = customer?.id || null;
      }

      const { data: order, error: orderError } = await supabase
        .from("cardvector_direct_store_orders")
        .update({
          order_status: "paid",
          payment_status: "paid",
          fulfillment_status: "ready_to_ship",
          marketplace_release_status: "automation_pending",
          ready_to_ship_at: new Date().toISOString(),
          paid_at: new Date().toISOString(),
          customer_id: customerId,
          customer_email: customerEmail,
          customer_name: customerName,
          stripe_payment_intent_id: typeof session.payment_intent === "string" ? session.payment_intent : "",
          stripe_customer_id: typeof session.customer === "string" ? session.customer : "",
          shipping_address: session.shipping_details || {},
          billing_address: session.customer_details?.address || {},
          marketing_opt_in: marketingOptIn,
          marketing_consent_status: marketingStatus,
          total_cents: session.amount_total ?? 0,
          shipping_cents: session.total_details?.amount_shipping ?? 0,
          tax_cents: session.total_details?.amount_tax ?? 0,
        })
        .eq("stripe_checkout_session_id", session.id)
        .select("id, public_order_id")
        .single();
      if (orderError || !order) {
        throw orderError || new Error(`No order found for checkout session ${session.id}`);
      }
      await enqueueMarketplaceReleaseJobs(supabase, order);
      await markEvent("processed", event.id, "", order.id);
    } else if (event.type === "checkout.session.expired") {
      const { data: order, error: expireError } = await supabase
        .from("cardvector_direct_store_orders")
        .update({ order_status: "expired", payment_status: "expired" })
        .eq("stripe_checkout_session_id", session.id)
        .select("id")
        .single();
      if (expireError) {
        throw expireError;
      }
      await markEvent("processed", event.id, "", order?.id || null);
    } else {
      await markEvent("ignored", event.id);
    }
  } catch (error) {
    console.error("stripe webhook processing failed", error);
    await markEvent("failed", event.id, error instanceof Error ? error.message : "Unknown webhook failure");
    return new Response("Webhook processing failed", { status: 500 });
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { "content-type": "application/json" },
  });
});
