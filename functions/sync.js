// Cloudflare Pages Functions · GET/POST /sync
// 炒股工作台跨平台实时同步 API（数据持久化到 Gitee 仓库，免费+版本历史）
// 部署：Cloudflare Pages 连接 GitHub 仓库（functions/ 目录自动识别为 Functions）

const GITEE_API = 'https://gitee.com/api/v5/repos';

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
               'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
               'Access-Control-Allow-Headers': 'Content-Type, X-Sync-Token' }
  });
}

function authOk(env, req) {
  if (!env.SYNC_TOKEN) return true;
  return req.headers.get('x-sync-token') === env.SYNC_TOKEN;
}

function pathOf(env) { return env.GITEE_PATH || 'sync-db.json'; }

// 读 Gitee 数据文件；不存在返回 null
async function giteeGet(env) {
  const url = `${GITEE_API}/${env.GITEE_REPO}/contents/${pathOf(env)}?ref=${env.GITEE_BRANCH || 'main'}`;
  const r = await fetch(url, { headers: { Authorization: `token ${env.GITEE_TOKEN}` } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error('gitee get ' + r.status);
  const j = await r.json();
  if (!j || !j.content) return null;                    // Gitee 对不存在文件返回 200+[]（坑）
  return { sha: j.sha, db: JSON.parse(Buffer.from(j.content, 'base64').toString('utf8')) };
}

// 写 Gitee 数据文件；成功返回新 sha，失败返回 null
async function giteePut(env, db, sha) {
  const body = {
    access_token: env.GITEE_TOKEN,
    content: Buffer.from(JSON.stringify(db)).toString('base64'),
    message: `sync v${db.version}`,
    branch: env.GITEE_BRANCH || 'main'
  };
  if (sha) body.sha = sha;
  const r = await fetch(`${GITEE_API}/${env.GITEE_REPO}/contents/${pathOf(env)}`, {
    method: sha ? 'PUT' : 'POST',                        // 更新用 PUT，创建用 POST（Gitee 要求）
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  const j = await r.json().catch(() => ({}));
  if (j.content && j.content.sha) return j.content.sha;
  return null;                                          // 失败（sha 过期/限流）→ 由调用方重试
}

// 读最新 → 执行 fn(db) → 写回；并发写冲突自动重读重试（乐观锁，最多 5 次）
async function withGitee(env, fn) {
  for (let i = 0; i < 5; i++) {
    const cur = await giteeGet(env);
    const db = cur ? cur.db : { version: 0, recs: {} };
    const res = await fn(db);
    if (res.conflict) return res;                       // 版本不匹配 → 返回 409 语义
    const newSha = await giteePut(env, res.db, cur ? cur.sha : null);
    if (newSha) return res;
    await new Promise(r => setTimeout(r, 300 + Math.random() * 400));   // 写失败 → 重读重试
  }
  return { tooMany: true };
}

// GET /sync?since=<version>
export async function onRequestGet(ctx) {
  const { env, request } = ctx;
  if (!authOk(env, request)) return json({ error: 'unauthorized' }, 401);
  const url = new URL(request.url);
  const since = parseInt(url.searchParams.get('since') || '0', 10);
  try {
    const cur = await giteeGet(env);
    const db = cur ? cur.db : { version: 0, recs: {} };
    const recs = (since === db.version) ? {} : db.recs;   // 无变化优化
    return json({ ok: true, version: db.version, recs });
  } catch (e) { return json({ error: e.message }, 500); }
}

// POST /sync {base, patch} → 200 或 409 {version, recs}
export async function onRequestPost(ctx) {
  const { env, request } = ctx;
  if (!authOk(env, request)) return json({ error: 'unauthorized' }, 401);
  let payload;
  try { payload = await request.json(); } catch (e) { return json({ error: 'bad json' }, 400); }
  try {
    const res = await withGitee(env, (db) => {
      if (payload.base !== db.version) return { conflict: true, db };
      const patch = payload.patch || {};
      for (const [id, rr] of Object.entries(patch)) {
        const cur = db.recs[id];
        if (!cur || rr.ts > cur.ts || (rr.ts === cur.ts && rr.device > cur.device)) db.recs[id] = rr;
      }
      db.version += 1;
      return { db };
    });
    if (res.tooMany) return json({ error: 'busy, retry later' }, 503);
    if (res.conflict) return json({ version: res.db.version, recs: res.db.recs }, 409);
    return json({ ok: true, version: res.db.version, recs: res.db.recs });
  } catch (e) { return json({ error: e.message }, 500); }
}

// OPTIONS（CORS 预检）
export async function onRequestOptions() { return new Response(null, { status: 204 }); }
