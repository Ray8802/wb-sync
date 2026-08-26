// Cloudflare Pages Functions · GET /api/news?src=em|jin10|sina
// 财经资讯代理：浏览器无法跨域直连新闻源（CORS 拦截），由本函数服务端抓取后返回
// 源：em=东方财富7x24快讯 | jin10=金十数据 | sina=新浪财经7x24
export async function onRequestGet(ctx) {
  const CORS = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' };
  const pick = (s) => String(s || '').replace(/\s+/g, ' ').trim();
  const src = new URL(ctx.request.url).searchParams.get('src') || 'em';

  // 东方财富 7x24 快讯
  async function srcEm() {
    const r = await fetch('https://np-listapi.eastmoney.com/comm/web/getFastNewsList?client=web&biz=web_724&fastColumn=102&sortEnd=&pageSize=30&req_trace=1', { signal: AbortSignal.timeout(12000), headers: { 'User-Agent': 'Mozilla/5.0' } });
    const j = await r.json();
    const list = (j && j.data && j.data.fastNewsList) || [];
    return list.filter(x => x && x.summary).map(x => ({
      id: x.code, text: pick(x.summary), time: (x.showTime || '').slice(11, 16), date: (x.showTime || '').slice(0, 10), tag: '快讯', url: ''
    }));
  }

  // 金十数据 快讯
  async function srcJin10() {
    const r = await fetch('https://flash-api.jin10.com/get_flash_list?channel=-8200&vip=1&max_time=', { signal: AbortSignal.timeout(12000), headers: { 'X-App-Id': 'bVBF4FyRTn5NJF5n', 'X-Version': '1.0.0', 'User-Agent': 'Mozilla/5.0' } });
    const j = await r.json();
    const list = (j && j.data) || [];
    return list.filter(x => x && x.data && (x.data.content || x.data.title)).map(x => ({
      id: x.id, text: pick(x.data.content || x.data.title), time: (x.time || '').slice(11, 16), date: (x.time || '').slice(0, 10),
      tag: pick(x.data.source) || '金十', url: x.data.source_link || ''
    }));
  }

  // 新浪 7x24 快讯
  async function srcSina() {
    const r = await fetch('https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=30&zhibo_id=152', { signal: AbortSignal.timeout(12000) });
    const j = await r.json();
    const list = (j && j.result && j.result.data && j.result.data.feed && j.result.data.feed.list) || [];
    return list.filter(x => x && x.rich_text).map(x => ({
      id: x.id, text: pick(x.rich_text), time: (x.create_time || '').slice(11, 16), date: (x.create_time || '').slice(0, 10),
      tag: (x.tag && x.tag[0] && x.tag[0].name) || '', url: x.docurl || ''
    }));
  }

  try {
    let items = [];
    if (src === 'jin10') items = await srcJin10();
    else if (src === 'sina') items = await srcSina();
    else items = await srcEm();
    if (items.length) return new Response(JSON.stringify({ ok: true, src, items }), { headers: CORS });
  } catch (e) {}

  return new Response(JSON.stringify({ ok: false, error: 'news source unavailable' }), { status: 502, headers: CORS });
}
