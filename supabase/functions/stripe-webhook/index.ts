import Stripe from "npm:stripe@22.0.0";
import { createClient } from "npm:@supabase/supabase-js@2.45.4";

function env(name: string): string {
  const value = Deno.env.get(name);
  if (!value) {
    throw new Error(`${name} is not configured`);
  }
  return value;
}

function consentStatus(session: Stripe.Checkout.Session): string {
  const value = String(session.consent?.promotions || "").trim();
  return value || "not_collected";
}

async function markEvent(status: string, eventId: string, errorMessage = ""): Promise<void> {
  const supabase = createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { persistSession: false },
  });
  await supabase
    .from("cardvector_direct_store_checkout_events")
    .update({ processing_status: status, processed_at: new Date().toISOString(), error_message: errorMessage })
    .eq("stripe_event_id", eventId);
}

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const stripe = new Stripe(env("STRIPE_SECRET_KEY"));
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
  const { error: insertEventError } = await supabase
    .from("cardvector_direct_store_checkout_events")
    .insert({
      stripe_event_id: event.id,
      event_type: event.type,
      stripe_checkout_session_id: typeof session.id === "string" ? session.id : "",
      payload: event as unknown as Record<string, unknown>,
    });
  if (insertEventError) {
    const message = String(insertEventError.message || "");
    if (message.includes("duplicate key")) {
      return new Response(JSON.stringify({ received: true, duplicate: true }), {
        headers: { "content-type": "application/json" },
      });
    }
    console.error("webhook event insert failed", insertEventError);
    return new Response("Webhook event insert failed", { status: 500 });
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

      const { error: orderError } = await supabase
        .from("cardvector_direct_store_orders")
        .update({
          order_status: "paid",
          payment_status: "paid",
          fulfillment_status: "ready_to_ship",
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
        .eq("stripe_checkout_session_id", session.id);
      if (orderError) {
        throw orderError;
      }
      await markEvent("processed", event.id);
    } else if (event.type === "checkout.session.expired") {
      const { error: expireError } = await supabase
        .from("cardvector_direct_store_orders")
        .update({ order_status: "expired", payment_status: "expired" })
        .eq("stripe_checkout_session_id", session.id);
      if (expireError) {
        throw expireError;
      }
      await markEvent("processed", event.id);
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
