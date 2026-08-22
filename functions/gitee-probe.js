// Cloudflare Pages Functions · Gitee API 连通性探针 GET /gitee-probe
export async function onRequestGet(ctx) {
  const { env } = ctx;
  const tryAuth = async (label, headers) => {
    try {
      const r = await fetch('https://gitee.com/api/v5/user', { headers, signal: AbortSignal.timeout(15000) });
      const t = await r.text();
      return `${label} → HTTP ${r.status} · ${t.slice(0, 120)}`;
    } catch (e) { return `${label} → ERR ${e.message}`; }
  };
  const out = {
    token_len: env.GITEE_TOKEN ? env.GITEE_TOKEN.length : 0,
    header_auth: await tryAuth('Authorization header', { Authorization: `token ${env.GITEE_TOKEN}`, 'User-Agent': 'wb-sync-pages/1.0' }),
    query_param: await tryAuth('access_token query', { 'User-Agent': 'wb-sync-pages/1.0' }, true)
  };
  // query 方式：access_token 作为参数（Gitee 也支持）
  try {
    const r = await fetch(`https://gitee.com/api/v5/user?access_token=${env.GITEE_TOKEN}`, { signal: AbortSignal.timeout(15000) });
    out.query_param = `access_token query → HTTP ${r.status} · ${(await r.text()).slice(0, 120)}`;
  } catch (e) { out.query_param = `access_token query → ERR ${e.message}`; }
  return new Response(JSON.stringify(out, null, 1), {
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
}
