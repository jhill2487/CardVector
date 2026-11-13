const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { webcrypto, generateKeyPairSync } = require('node:crypto');
const source = fs.readFileSync('supabase/functions/cardvector-analytics/index.ts', 'utf8');
const privateKey = generateKeyPairSync('rsa', { modulusLength: 2048 }).privateKey.export({ type: 'pkcs8', format: 'pem' });
function setup({ email = 'jhill2487@gmail.com', confirmed = true, reportStatus = 200, empty = false, secret = true } = {}) {
  let handler;
  const calls = [];
  const env = { SUPABASE_URL: 'https://example.supabase.co', SUPABASE_ANON_KEY: 'public',
    GA4_PROPERTY_ID: '546030311', GA4_SERVICE_ACCOUNT_JSON: secret ? JSON.stringify({ client_email: 'reader@example.com', private_key: privateKey }) : '' };
  const context = vm.createContext({ Response, Request, URLSearchParams, TextEncoder, Uint8Array, AbortSignal,
    Date, atob, btoa, crypto: webcrypto, Deno: { env: { get: name => env[name] }, serve: fn => { handler = fn; } },
    fetch: async (url, options) => {
      calls.push({ url, options });
      if (url.endsWith('/auth/v1/user')) return Response.json({ email, email_confirmed_at: confirmed ? '2026-01-01' : null });
      if (url.endsWith('/token')) {
        const assertion = options.body.get('assertion');
        const claims = JSON.parse(Buffer.from(assertion.split('.')[1], 'base64url'));
        assert.equal(claims.scope, 'https://www.googleapis.com/auth/analytics.readonly');
        return Response.json({ access_token: 'test-access-token' });
      }
      assert.equal(url, 'https://analyticsdata.googleapis.com/v1beta/properties/546030311:runReport');
      assert.deepEqual(JSON.parse(options.body).dateRanges, [{ startDate: '7daysAgo', endDate: 'yesterday' }]);
      if (reportStatus !== 200) return Response.json({ error: { message: 'PRIVATE UPSTREAM ERROR' } }, { status: reportStatus });
      return Response.json({ metricHeaders: ['totalUsers','newUsers','sessions','screenPageViews'].map(name => ({name})),
        rows: empty ? [] : [{ metricValues: [12,8,20,43].map(value => ({ value: String(value) })) }], metadata: { timeZone: 'America/New_York' } });
    } });
  vm.runInContext(source, context);
  const request = (token = 'valid-user') => handler(new Request('https://example.com', {
    method: 'POST', headers: token ? { Authorization: 'Bearer ' + token } : {} }));
  return { request, calls, context };
}
test('unauthenticated request never reaches Google or reads report', async () => {
  const s = setup(); assert.equal((await s.request('')).status, 401); assert.equal(s.calls.length, 0);
});
test('non-admin and unconfirmed users are denied before Google', async () => {
  for (const options of [{email:'other@example.com'}, {confirmed:false}]) {
    const s = setup(options); assert.equal((await s.request()).status, 403); assert.equal(s.calls.length, 1);
  }
});
test('admin receives exact GA totals and cached calls still reauthenticate', async () => {
  const s = setup(); const report = await (await s.request()).json();
  assert.deepEqual(report.metrics, { totalUsers:12,newUsers:8,sessions:20,screenPageViews:43 });
  assert.equal(report.timeZone,'America/New_York');
  await s.request(); assert.equal(s.calls.filter(c=>c.url.endsWith('/auth/v1/user')).length,2);
  assert.equal(s.calls.filter(c=>c.url.includes(':runReport')).length,1);
  assert.doesNotMatch(JSON.stringify(report), /PRIVATE KEY|test-access-token/);
});
test('empty report is zero and explicitly marked empty', async () => {
  const s=setup({empty:true}); const data=await (await s.request()).json();
  assert.equal(data.empty,true); assert.equal(data.metrics.totalUsers,0);
});
test('Google failures return actionable errors without upstream content or false zeros', async () => {
  for (const reportStatus of [403,429,500]) {
    const s=setup({reportStatus}); const result=await s.request();
    assert.equal(result.status,502); const data=await result.json();
    assert.ok(data.error); assert.equal(data.metrics,undefined); assert.doesNotMatch(data.error,/PRIVATE UPSTREAM/);
  }
});
test('missing secret fails safely', async () => {
  const s=setup({secret:false}); const result=await s.request();
  assert.equal(result.status,502); assert.match((await result.json()).error,/Supabase secrets/);
});
test('concurrent administrator refreshes share one Google report', async () => {
  const s=setup(); await Promise.all([s.request(),s.request(),s.request()]);
  assert.equal(s.calls.filter(c=>c.url.includes(':runReport')).length,1);
});
