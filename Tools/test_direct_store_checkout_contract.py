import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs"
MIGRATION = ROOT / "supabase" / "migrations" / "20260828120000_direct_store_checkout.sql"
CREATE_CHECKOUT = ROOT / "supabase" / "functions" / "create-checkout-session" / "index.ts"
STRIPE_WEBHOOK = ROOT / "supabase" / "functions" / "stripe-webhook" / "index.ts"
SUPABASE_CONFIG = ROOT / "supabase" / "config.toml"


class DirectStoreCheckoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js = (DOCS / "app.js").read_text(encoding="utf-8")
        cls.site_config = json.loads((DOCS / "site-config.json").read_text(encoding="utf-8"))
        cls.sql = MIGRATION.read_text(encoding="utf-8")
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
        self.assertIn("Shipping and tracking messages are transactional order updates", self.app_js)
        self.assertIn("Promotional emails are optional in Stripe Checkout", self.app_js)
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

    def test_edge_functions_use_stripe_checkout_and_webhook(self):
        self.assertIn('npm:stripe@22.4.0', self.create_checkout)
        self.assertIn("STRIPE_RESTRICTED_KEY", self.create_checkout)
        self.assertIn("STRIPE_SECRET_KEY", self.create_checkout)
        self.assertIn("apiVersion: \"2026-07-29.dahlia\"", self.create_checkout)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", self.create_checkout)
        self.assertIn("stripe.checkout.sessions.create", self.create_checkout)
        self.assertIn("integration_identifier", self.create_checkout)
        self.assertIn('shipping_address_collection: { allowed_countries: ["US"] }', self.create_checkout)
        self.assertIn('consent_collection: { promotions: "auto" }', self.create_checkout)
        self.assertIn("DIRECT_STORE_FEED_URL", self.create_checkout)
        self.assertIn("cardvector_direct_store_orders", self.create_checkout)
        self.assertIn("cardvector_direct_store_order_items", self.create_checkout)

        self.assertIn("STRIPE_WEBHOOK_SECRET", self.webhook)
        self.assertIn('npm:stripe@22.4.0', self.webhook)
        self.assertIn("STRIPE_RESTRICTED_KEY", self.webhook)
        self.assertIn("apiVersion: \"2026-07-29.dahlia\"", self.webhook)
        self.assertIn("constructEventAsync", self.webhook)
        self.assertIn('event.type === "checkout.session.completed"', self.webhook)
        self.assertIn('fulfillment_status: "ready_to_ship"', self.webhook)
        self.assertIn('marketing_consent_source: "stripe_checkout"', self.webhook)
        self.assertIn("shipping_details", self.webhook)

    def test_supabase_function_jwt_configuration_is_explicit(self):
        self.assertIn("[functions.create-checkout-session]", self.supabase_config)
        self.assertIn("[functions.stripe-webhook]", self.supabase_config)
        self.assertEqual(2, self.supabase_config.count("verify_jwt = false"))


if __name__ == "__main__":
    unittest.main()
