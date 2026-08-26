// Cloudflare Pages Functions · GET /api/news
// 财经资讯代理：浏览器无法跨域直连新闻源（CORS 拦截），由本函数服务端抓取后返回
// 主源：新浪财经 7x24 快讯；兜底：新浪滚动新闻
export async function onRequestGet() {
  const CORS = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' };
  const pick = (s) => String(s || '').replace(/\s+/g, ' ').trim();

  // 主源：新浪 7x24 财经快讯
  try {
    const r = await fetch('https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=30&zhibo_id=152', { signal: AbortSignal.timeout(12000) });
    const j = await r.json();
    const list = (j && j.result && j.result.data && j.result.data.feed && j.result.data.feed.list) || [];
    const items = list.filter(x => x && x.rich_text).map(x => ({
      id: x.id, text: pick(x.rich_text), time: (x.create_time || '').slice(11, 16),
      date: (x.create_time || '').slice(0, 10),
      tag: (x.tag && x.tag[0] && x.tag[0].name) || '', url: x.docurl || ''
    }));
    if (items.length) return new Response(JSON.stringify({ ok: true, src: 'sina7x24', items }), { headers: CORS });
  } catch (e) {}

  // 兜底：新浪滚动新闻
  try {
    const r = await fetch('https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=30&page=1', { signal: AbortSignal.timeout(12000) });
    const j = await r.json();
    const list = (j && j.result && j.result.data) || [];
    const items = list.filter(x => x && x.title).map(x => ({
      id: x.ctime, text: pick(x.title), time: new Date(+x.ctime * 1000).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      date: new Date(+x.ctime * 1000).toLocaleDateString('zh-CN'), tag: '财经', url: x.url || ''
    }));
    if (items.length) return new Response(JSON.stringify({ ok: true, src: 'sinaRoll', items }), { headers: CORS });
  } catch (e) {}

  return new Response(JSON.stringify({ ok: false, error: 'news source unavailable' }), { status: 502, headers: CORS });
}
