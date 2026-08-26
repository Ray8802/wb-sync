// Cloudflare Pages Functions · GET /api/news
// 财经资讯聚合：综合 东方财富7x24 + 金十数据 + 新浪7x24 三源，
// 自动去重 + 重大度评分（多源交叉/重大关键词/金十important 字段），重大新闻优先展示
export async function onRequestGet() {
  const CORS = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' };
  const pick = (s) => String(s || '').replace(/\s+/g, ' ').trim();

  // 东方财富 7x24
  async function srcEm() {
    const r = await fetch('https://np-listapi.eastmoney.com/comm/web/getFastNewsList?client=web&biz=web_724&fastColumn=102&sortEnd=&pageSize=30&req_trace=1', { signal: AbortSignal.timeout(10000), headers: { 'User-Agent': 'Mozilla/5.0' } });
    const j = await r.json();
    const list = (j && j.data && j.data.fastNewsList) || [];
    return list.filter(x => x && x.summary).map(x => ({ src: 'em', id: 'em' + x.code, text: pick(x.summary), time: (x.showTime || '').slice(11, 16), date: (x.showTime || '').slice(0, 10), tag: '快讯', url: '', important: false }));
  }
  // 金十数据
  async function srcJin10() {
    const r = await fetch('https://flash-api.jin10.com/get_flash_list?channel=-8200&vip=1&max_time=', { signal: AbortSignal.timeout(10000), headers: { 'X-App-Id': 'bVBF4FyRTn5NJF5n', 'X-Version': '1.0.0', 'User-Agent': 'Mozilla/5.0' } });
    const j = await r.json();
    const list = (j && j.data) || [];
    return list.filter(x => x && x.data && (x.data.content || x.data.title)).map(x => ({
      src: 'jin10', id: 'j' + x.id, text: pick(x.data.content || x.data.title), time: (x.time || '').slice(11, 16), date: (x.time || '').slice(0, 10),
      tag: pick(x.data.source) || '金十', url: x.data.source_link || '', important: !!x.important
    }));
  }
  // 新浪 7x24
  async function srcSina() {
    const r = await fetch('https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=30&zhibo_id=152', { signal: AbortSignal.timeout(10000) });
    const j = await r.json();
    const list = (j && j.result && j.result.data && j.result.data.feed && j.result.data.feed.list) || [];
    return list.filter(x => x && x.rich_text).map(x => ({
      src: 'sina', id: 's' + x.id, text: pick(x.rich_text), time: (x.create_time || '').slice(11, 16), date: (x.create_time || '').slice(0, 10),
      tag: (x.tag && x.tag[0] && x.tag[0].name) || '', url: x.docurl || '', important: false
    }));
  }

  // 重大度关键词
  const KEY = ['央行', '降息', '加息', '降准', 'LPR', 'MLF', '国务院', '证监会', '财政部', '统计局', '商务部', '发改委', '美联储', '欧央行', '突发', '重磅', '重大', '紧急', '新规', '政策', '监管', '立案', '退市', '重组', '收购', '涨停', '跌停', 'CPI', 'PMI', 'GDP', '数据', '涨停'];

  // 去重 key：取文本去【】后前 16 字
  const normKey = t => t.replace(/【[^】]*】/g, '').replace(/金十数据[0-9月日]*讯/, '').slice(0, 16);

  try {
    const [emR, jR, sR] = await Promise.allSettled([srcEm(), srcJin10(), srcSina()]);
    const all = [...(emR.status === 'fulfilled' ? emR.value : []), ...(jR.status === 'fulfilled' ? jR.value : []), ...(sR.status === 'fulfilled' ? sR.value : [])];
    if (!all.length) return new Response(JSON.stringify({ ok: false, error: 'no news' }), { status: 502, headers: CORS });

    // 按去重 key 分组 → 多源交叉检测
    const groups = {};
    all.forEach(n => { const k = normKey(n.text); (groups[k] = groups[k] || []).push(n); });

    const items = Object.values(groups).map(g => {
      const first = g[0];
      let score = 0;
      if (g.length >= 2) score += 3;                       // 多源交叉 = 重大信号
      if (first.important) score += 2;                     // 金十 important 字段
      const t = first.text;
      KEY.forEach(k => { if (t.includes(k)) score += 1; }); // 重大关键词
      if (/突发|重磅|重大|紧急/.test(t)) score += 1;
      return {
        id: g.map(x => x.id).join('|'), text: first.text, time: first.time, date: first.date,
        tag: first.tag, url: first.url, src: g.map(x => x.src).join('+'), n: g.length, score
      };
    });

    items.sort((a, b) => (b.score - a.score) || (b.date + b.time).localeCompare(a.date + a.time));
    return new Response(JSON.stringify({
      ok: true, items: items.slice(0, 50),
      stats: { em: emR.status === 'fulfilled' ? emR.value.length : 0, jin10: jR.status === 'fulfilled' ? jR.value.length : 0, sina: sR.status === 'fulfilled' ? sR.value.length : 0 }
    }), { headers: CORS });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: 'aggregate failed' }), { status: 502, headers: CORS });
  }
}
