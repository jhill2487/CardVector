import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs"
MIGRATION = ROOT / "supabase" / "migrations" / "20260828120000_direct_store_checkout.sql"
RELEASE_JOB_MIGRATION = ROOT / "supabase" / "migrations" / "20260828163000_direct_store_release_jobs.sql"
CREATE_CHECKOUT = ROOT / "supabase" / "functions" / "create-checkout-session" / "index.ts"
STRIPE_WEBHOOK = ROOT / "supabase" / "functions" / "stripe-webhook" / "index.ts"
SUPABASE_CONFIG = ROOT / "supabase" / "config.toml"


class DirectStoreCheckoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js = (DOCS / "app.js").read_text(encoding="utf-8")
        cls.site_config = json.loads((DOCS / "site-config.json").read_text(encoding="utf-8"))
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.release_job_sql = RELEASE_JOB_MIGRATION.read_text(encoding="utf-8")
        cls.create_checkout = CREATE_CHECKOUT.read_text(encoding="utf-8")
        cls.webhook = STRIPE_WEBHOOK.read_text(encoding="utf-8")
        cls.supabase_config = SUPABASE_CONFIG.read_text(encoding="utf-8")

    def test_site_has_checkout_endpoint_and_no_browser_payment_collection(self):
        self.assertEqual(
            "https://iqdpfgpkagjxzedfxrvn.supabase.co/functions/v1/create-checkout-session",
            self.site_config["CHECKOUT_FUNCTION_URL"],
        )
        self.assertIn("createDirectStoreCheckoutSession", self.app_js)
        self.assertIn("Continue to Secure Checkout", self.app_js)
        self.assertIn("window.location.assign(result.checkout_url)", self.app_js)
        self.assertIn("checkoutSucceeded", self.app_js)
        self.assertIn("writeDirectStoreCart({ items: {} })", self.app_js)
        self.assertIn("Shipping and tracking messages are transactional order updates", self.app_js)
        self.assertNotIn("Promotional emails are optional in Stripe Checkout", self.app_js)
        self.assertNotIn("stripe.confirmPayment", self.app_js)
        self.assertNotIn("paypal.Buttons", self.app_js)

    def test_migration_creates_service_role_order_tables(self):
        for table in (
            "cardvector_direct_store_customers",
            "cardvector_direct_store_orders",
            "cardvector_direct_store_order_items",
            "cardvector_direct_store_checkout_events",
        ):
            self.assertIn(f"create table if not exists public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
            self.assertIn(f"revoke all on table public.{table} from anon", self.sql)
            self.assertIn(f"revoke all on table public.{table} from authenticated", self.sql)
            self.assertIn(f"on table public.{table}", self.sql)
            self.assertIn("to service_role", self.sql)
        self.assertIn("shipping_confirmation_sent_at", self.sql)
        self.assertIn("tracking_number", self.sql)
        self.assertIn("marketing_opt_in boolean not null default false", self.sql)
        self.assertIn("stripe_checkout_session_id text unique", self.sql)

    def test_release_job_migration_is_private_and_idempotent(self):
        table = "cardvector_direct_store_release_jobs"
        self.assertIn(f"create table if not exists public.{table}", self.release_job_sql)
        self.assertIn("order_id uuid not null references public.cardvector_direct_store_orders(id) on delete cascade", self.release_job_sql)
        self.assertIn("order_item_id uuid not null references public.cardvector_direct_store_order_items(id) on delete cascade", self.release_job_sql)
        self.assertIn("release_action text not null default 'release_purchased_quantity'", self.release_job_sql)
        self.assertIn("release_status text not null default 'pending'", self.release_job_sql)
        self.assertIn("target_system in ('carduploader')", self.release_job_sql)
        self.assertIn("target_marketplace in ('ebay')", self.release_job_sql)
        self.assertIn("cardvector_direct_store_release_jobs_order_item_idx", self.release_job_sql)
        self.assertIn("on public.cardvector_direct_store_release_jobs(order_item_id)", self.release_job_sql)
        self.assertIn(f"alter table public.{table} enable row level security", self.release_job_sql)
        self.assertIn(f"revoke all on table public.{table} from anon", self.release_job_sql)
        self.assertIn(f"revoke all on table public.{table} from authenticated", self.release_job_sql)
        self.assertIn(f"grant select, insert, update on table public.{table} to service_role", self.release_job_sql)

    def test_edge_functions_use_stripe_checkout_and_webhook(self):
        self.assertIn('npm:stripe@22.4.0', self.create_checkout)
        self.assertIn("STRIPE_RESTRICTED_KEY", self.create_checkout)
        self.assertIn("STRIPE_SECRET_KEY", self.create_checkout)
        self.assertIn("apiVersion: \"2026-07-29.dahlia\"", self.create_checkout)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", self.create_checkout)
        self.assertIn("stripe.checkout.sessions.create", self.create_checkout)
        self.assertIn("integration_identifier", self.create_checkout)
        self.assertIn('shipping_address_collection: { allowed_countries: ["US"] }', self.create_checkout)
        self.assertNotIn("consent_collection", self.create_checkout)
        self.assertIn("DIRECT_STORE_FEED_URL", self.create_checkout)
        self.assertIn("cardvector_direct_store_orders", self.create_checkout)
        self.assertIn("cardvector_direct_store_order_items", self.create_checkout)
        self.assertNotIn("consent_collection", self.webhook)

        self.assertIn("STRIPE_WEBHOOK_SECRET", self.webhook)
        self.assertIn('npm:stripe@22.4.0', self.webhook)
        self.assertIn("STRIPE_RESTRICTED_KEY", self.webhook)
        self.assertIn("apiVersion: \"2026-07-29.dahlia\"", self.webhook)
        self.assertIn("constructEventAsync", self.webhook)
        self.assertIn('onConflict: "stripe_event_id"', self.webhook)
        self.assertIn('processing_status: "received"', self.webhook)
        self.assertIn('event.type === "checkout.session.completed"', self.webhook)
        self.assertIn('fulfillment_status: "ready_to_ship"', self.webhook)
        self.assertIn('marketplace_release_status: "automation_pending"', self.webhook)
        self.assertIn("enqueueMarketplaceReleaseJobs", self.webhook)
        self.assertIn("cardvector_direct_store_release_jobs", self.webhook)
        self.assertIn('release_action: "release_purchased_quantity"', self.webhook)
        self.assertIn('release_status: "pending"', self.webhook)
        self.assertIn('onConflict: "order_item_id"', self.webhook)
        self.assertIn("ignoreDuplicates: true", self.webhook)
        self.assertIn("order_id: orderId", self.webhook)
        self.assertIn('marketing_consent_source: "stripe_checkout"', self.webhook)
        self.assertIn("shipping_details", self.webhook)

    def test_supabase_function_jwt_configuration_is_explicit(self):
        self.assertIn("[functions.create-checkout-session]", self.supabase_config)
        self.assertIn("[functions.stripe-webhook]", self.supabase_config)
        self.assertEqual(2, self.supabase_config.count("verify_jwt = false"))


if __name__ == "__main__":
    unittest.main()
