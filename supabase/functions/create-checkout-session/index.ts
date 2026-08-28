import Stripe from "npm:stripe@22.0.0";
import { createClient } from "npm:@supabase/supabase-js@2.45.4";

type DirectStoreItem = {
  id: string;
  title: string;
  game?: string;
  condition?: string;
  variant?: string;
  price: number;
  quantity_available: number;
  source?: string;
  source_listing_id?: string;
  inventory_reference?: string;
};

type DirectStoreFeed = {
  currency?: string;
  generated_at?: string;
  items?: DirectStoreItem[];
};

type CartPayload = {
  cart?: {
    items?: Record<string, { quantity?: number }>;
  };
};

const corsHeaders = {
  "access-control-allow-origin": Deno.env.get("CARDVECTOR_ALLOWED_ORIGIN") || "https://cardvector.app",
  "access-control-allow-headers": "authorization, x-client-info, apikey, content-type",
  "access-control-allow-methods": "POST, OPTIONS",
};

function jsonResponse(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "content-type": "application/json" },
  });
}

function cents(value: number): number {
  return Math.round(Number(value || 0) * 100);
}

async function sha256Hex(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function env(name: string): string {
  const value = Deno.env.get(name);
  if (!value) {
    throw new Error(`${name} is not configured`);
  }
  return value;
}

function orderPublicId(): string {
  const suffix = crypto.randomUUID().replace(/-/g, "").slice(0, 12).toUpperCase();
  return `CVD-${suffix}`;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") {
    return jsonResponse({ ok: false, error: "Method not allowed" }, 405);
  }

  try {
    const stripe = new Stripe(env("STRIPE_SECRET_KEY"));
    const supabase = createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
      auth: { persistSession: false },
    });
    const siteUrl = Deno.env.get("CARDVECTOR_SITE_URL") || "https://cardvector.app";
    const feedUrl = Deno.env.get("DIRECT_STORE_FEED_URL") || `${siteUrl}/content/shop/direct-inventory.json`;
    const payload = await req.json() as CartPayload;
    const requested = Object.entries(payload.cart?.items || {})
      .map(([itemId, line]) => ({
        itemId: String(itemId || "").trim(),
        quantity: Math.max(0, Math.floor(Number(line?.quantity) || 0)),
      }))
      .filter((line) => line.itemId && line.quantity > 0);

    if (!requested.length) {
      return jsonResponse({ ok: false, error: "Cart is empty." }, 400);
    }
    if (requested.length > 40 || requested.some((line) => line.quantity > 20)) {
      return jsonResponse({ ok: false, error: "Cart exceeds checkout limits." }, 400);
    }

    const feedResponse = await fetch(feedUrl, { cache: "no-store" });
    if (!feedResponse.ok) {
      return jsonResponse({ ok: false, error: "Inventory feed is unavailable." }, 503);
    }
    const feed = await feedResponse.json() as DirectStoreFeed;
    const catalog = new Map((feed.items || []).map((item) => [String(item.id || "").trim(), item]));
    const orderItems = [];
    let subtotalCents = 0;
    for (const line of requested) {
      const item = catalog.get(line.itemId);
      if (!item || !item.title || !Number.isFinite(Number(item.price))) {
        return jsonResponse({ ok: false, error: `Item is no longer available: ${line.itemId}` }, 409);
      }
      const available = Math.max(0, Math.floor(Number(item.quantity_available) || 0));
      if (line.quantity > available) {
        return jsonResponse({ ok: false, error: `Requested quantity exceeds availability for ${item.title}.` }, 409);
      }
      const unitAmount = cents(Number(item.price));
      const lineTotal = unitAmount * line.quantity;
      subtotalCents += lineTotal;
      orderItems.push({ line, item, unitAmount, lineTotal });
    }

    const cartHash = await sha256Hex(JSON.stringify(requested.sort((a, b) => a.itemId.localeCompare(b.itemId))));
    const publicOrderId = orderPublicId();
    const { data: order, error: orderError } = await supabase
      .from("cardvector_direct_store_orders")
      .insert({
        public_order_id: publicOrderId,
        order_status: "pending_payment",
        payment_status: "not_started",
        fulfillment_status: "not_ready",
        marketplace_release_status: "not_configured",
        currency: String(feed.currency || "USD").toUpperCase(),
        subtotal_cents: subtotalCents,
        total_cents: subtotalCents,
        cart_hash: cartHash,
        inventory_snapshot_generated_at: feed.generated_at || null,
        metadata: { feed_url: feedUrl },
      })
      .select("id, public_order_id")
      .single();
    if (orderError || !order) {
      throw orderError || new Error("Order insert failed");
    }

    const { error: itemsError } = await supabase
      .from("cardvector_direct_store_order_items")
      .insert(orderItems.map(({ line, item, unitAmount, lineTotal }) => ({
        order_id: order.id,
        item_id: line.itemId,
        title: item.title,
        game: item.game || "",
        condition: item.condition || "",
        variant: item.variant || "",
        quantity: line.quantity,
        unit_price_cents: unitAmount,
        line_total_cents: lineTotal,
        source: item.source || "",
        source_listing_id: item.source_listing_id || "",
        inventory_reference: item.inventory_reference || "",
      })));
    if (itemsError) {
      throw itemsError;
    }

    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: orderItems.map(({ item, line, unitAmount }) => ({
        quantity: line.quantity,
        price_data: {
          currency: String(feed.currency || "USD").toLowerCase(),
          unit_amount: unitAmount,
          product_data: {
            name: item.title,
            metadata: { cardvector_item_id: String(item.id || "") },
          },
        },
      })),
      billing_address_collection: "auto",
      shipping_address_collection: { allowed_countries: ["US"] },
      shipping_options: [{
        shipping_rate_data: {
          type: "fixed_amount",
          fixed_amount: { amount: 0, currency: String(feed.currency || "USD").toLowerCase() },
          display_name: "Standard shipping",
        },
      }],
      consent_collection: { promotions: "auto" },
      metadata: {
        cardvector_order_id: order.id,
        cardvector_public_order_id: order.public_order_id,
        cart_hash: cartHash,
      },
      success_url: `${siteUrl}/cart/?checkout=success&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${siteUrl}/cart/?checkout=cancelled`,
    });

    const { error: updateError } = await supabase
      .from("cardvector_direct_store_orders")
      .update({
        stripe_checkout_session_id: session.id,
        payment_status: "open",
        checkout_expires_at: session.expires_at ? new Date(session.expires_at * 1000).toISOString() : null,
      })
      .eq("id", order.id);
    if (updateError) {
      throw updateError;
    }

    return jsonResponse({
      ok: true,
      checkout_url: session.url,
      session_id: session.id,
      order_id: order.id,
      public_order_id: order.public_order_id,
    });
  } catch (error) {
    console.error("create-checkout-session failed", error);
    return jsonResponse({ ok: false, error: "Secure checkout is temporarily unavailable." }, 500);
  }
});
