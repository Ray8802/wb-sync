// Cloudflare Pages Functions · Gitee contents API 探针（验证 UA 影响）
export async function onRequestGet(ctx) {
  const { env } = ctx;
  const url = `https://gitee.com/api/v5/repos/${env.GITEE_REPO}/contents/${env.GITEE_PATH || 'sync-db.json'}?ref=main`;
  const out = {};
  for (const [label, headers] of [
    ['无UA', { Authorization: `token ${env.GITEE_TOKEN}` }],
    ['有UA', { Authorization: `token ${env.GITEE_TOKEN}`, 'User-Agent': 'wb-sync-pages/1.0' }]
  ]) {
    try {
      const r = await fetch(url, { headers, signal: AbortSignal.timeout(15000) });
      out[label] = `HTTP ${r.status} · ${(await r.text()).slice(0, 80)}`;
    } catch (e) { out[label] = `ERR ${e.message}`; }
  }
  return new Response(JSON.stringify(out, null, 1), {
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
}
