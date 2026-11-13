// GA4 reporting adapter for the authenticated development dashboard.
const cors = {
  "Access-Control-Allow-Origin": "https://cardvector.app",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, x-client-info, content-type",
  "Vary": "Origin",
};
const metrics = ["totalUsers", "newUsers", "sessions", "screenPageViews"];
let cachedReport = null;
let pendingReport = null;

function response(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function base64url(bytes) {
  return btoa(String.fromCharCode(...bytes)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

async function loadReport() {
  const propertyId = Deno.env.get("GA4_PROPERTY_ID") || "";
  let credentials;
  try {
    credentials = JSON.parse(Deno.env.get("GA4_SERVICE_ACCOUNT_JSON") || "{}");
    if (!/^\d+$/.test(propertyId) || !credentials.client_email || !credentials.private_key) {
      throw new Error();
    }
  } catch {
    throw new Error("Check GA4_PROPERTY_ID and GA4_SERVICE_ACCOUNT_JSON in Supabase secrets.");
  }
  const now = Math.floor(Date.now() / 1000);
  const encode = value => base64url(new TextEncoder().encode(JSON.stringify(value)));
  const unsigned = encode({ alg: "RS256", typ: "JWT" }) + "." + encode({
    iss: credentials.client_email,
    scope: "https://www.googleapis.com/auth/analytics.readonly",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  });
  let signature;
  try {
    const pem = credentials.private_key.replace(/-----[^-]+-----|\s/g, "");
    const key = await crypto.subtle.importKey("pkcs8", Uint8Array.from(atob(pem), c => c.charCodeAt(0)),
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
    signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(unsigned));
  } catch {
    throw new Error("The GA4 service account private key could not be read. Check the saved JSON secret.");
  }
  const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: unsigned + "." + base64url(new Uint8Array(signature)),
    }),
    signal: AbortSignal.timeout(10000),
  });
  if (!tokenResponse.ok) throw new Error("Google rejected the service account credential. Check that its key is active.");
  const token = await tokenResponse.json();
  if (!token.access_token) throw new Error("Google authentication returned no access token.");
  const reportResponse = await fetch(`https://analyticsdata.googleapis.com/v1beta/properties/${propertyId}:runReport`, {
    method: "POST",
    headers: { Authorization: "Bearer " + token.access_token, "Content-Type": "application/json" },
    body: JSON.stringify({
      dateRanges: [{ startDate: "7daysAgo", endDate: "yesterday" }],
      metrics: metrics.map(name => ({ name })),
    }),
    signal: AbortSignal.timeout(15000),
  });
  if (reportResponse.status === 403) throw new Error("Check service account Viewer access and that the Analytics Data API is enabled.");
  if (reportResponse.status === 429) throw new Error("Google Analytics quota reached. Try again later.");
  if (!reportResponse.ok) throw new Error("Google Analytics could not return the report. Check the property ID and retry.");
  const report = await reportResponse.json();
  const values = {};
  for (const name of metrics) {
    const index = report.metricHeaders?.findIndex(header => header.name === name) ?? -1;
    if (index < 0) throw new Error("Google Analytics returned an unexpected report format.");
    const value = Number(report.rows?.[0]?.metricValues?.[index]?.value ?? 0);
    if (!Number.isFinite(value) || value < 0) throw new Error("Google Analytics returned an invalid metric.");
    values[name] = value;
  }
  return {
    propertyId,
    period: "Last 7 complete days",
    timeZone: report.metadata?.timeZone || "Property time zone",
    fetchedAt: new Date().toISOString(),
    metrics: values,
    empty: !report.rows?.length,
    thresholded: Boolean(report.metadata?.subjectToThresholding),
  };
}

Deno.serve(async request => {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (request.method !== "POST") return response({ error: "POST required" }, 405);
  const authorization = request.headers.get("Authorization") || "";
  if (!authorization.startsWith("Bearer ")) return response({ error: "Sign in required" }, 401);
  // Ask Auth to verify the current user before reading secrets or cached data.
  let user;
  try {
    const authResponse = await fetch(Deno.env.get("SUPABASE_URL") + "/auth/v1/user", {
      headers: { Authorization: authorization, apikey: Deno.env.get("SUPABASE_ANON_KEY") || "" },
      signal: AbortSignal.timeout(10000),
    });
    if (!authResponse.ok) return response({ error: "Sign in required" }, 401);
    user = await authResponse.json();
  } catch {
    return response({ error: "Account verification unavailable. Please retry." }, 503);
  }
  if (user.email?.toLowerCase() !== "jhill2487@gmail.com" || !user.email_confirmed_at) {
    return response({ error: "Administrator only" }, 403);
  }
  try {
    if (cachedReport && Date.now() - Date.parse(cachedReport.fetchedAt) < 300000) {
      return response(cachedReport);
    }
    if (!pendingReport) {
      pendingReport = loadReport().then(report => { cachedReport = report; return report; })
        .finally(() => { pendingReport = null; });
    }
    return response(await pendingReport);
  } catch (error) {
    const message = error.name === "TimeoutError" ? "Analytics request timed out. Please retry." : error.message;
    return response({ error: message || "Analytics unavailable. Please retry." }, 502);
  }
});
