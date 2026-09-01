// Cloudflare Pages Functions · GET /api/quote?secid=177.000660,116.07709
// 行情代理：腾讯接口不支持港股/韩股，用东方财富 push2 服务端抓取（无 CORS 限制）
// 东方财富市场代码：1=沪A 0=深A 116=港股 177=韩股 105/106/107=美股
export async function onRequestGet(ctx) {
  const CORS = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' };
  const secids = (new URL(ctx.request.url).searchParams.get('secid') || '')
    .split(',').map(s => s.trim()).filter(Boolean).slice(0, 20);
  if (!secids.length) return new Response(JSON.stringify({ ok: false, quotes: {} }), { headers: CORS });

  const out = {};
  await Promise.all(secids.map(async sid => {
    try {
      const r = await fetch('https://push2.eastmoney.com/api/qt/stock/get?secid=' + encodeURIComponent(sid) + '&fields=f43,f44,f45,f46,f58,f60,f169,f170,f86&fltt=2&invt=2',
        { signal: AbortSignal.timeout(8000), headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/' } });
      const j = await r.json();
      const d = j && j.data;
      if (d && d.f43 != null) {
        out[sid] = { name: d.f58, price: d.f43, prev: d.f60, chg: d.f169, chgPct: d.f170, high: d.f44, low: d.f45, open: d.f46, ts: d.f86 };
      }
    } catch (e) {}
  }));
  return new Response(JSON.stringify({ ok: Object.keys(out).length > 0, quotes: out }), { headers: CORS });
}
