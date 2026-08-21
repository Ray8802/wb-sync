#!/usr/bin/env node
/*
 * 炒股工作台 · 云端同步服务端（零依赖）
 * ------------------------------------------------------------
 * 让手机端与电脑端通过同一个端点实现真正的实时/定时同步。
 *
 * 协议（与前端 WBSync.cloudPush / cloudPull 对应）：
 *   GET  /sync?since=<version>   -> { ok, version, recs }
 *   POST /sync  body { base, patch } -> { ok, version, recs }  | 409 { version, recs }
 *
 * 合并规则（逐条 LWW：时间戳较新者胜；平局按 deviceId 字典序）：
 *   - POST 时若 base !== 当前 version，返回 409 让客户端先拉取再重试（并发安全）。
 *   - 每次成功写入 version 自增 1。
 *
 * 运行：
 *   node sync-server.js            # 默认 0.0.0.0:8787，数据存 ./sync-db.json
 *   PORT=9000 node sync-server.js
 *
 * 前端配置：把「云端端点」填为 http://<你的服务器IP或域名>:8787/sync
 * 鉴权（可选）：设置环境变量 SYNC_TOKEN 后，前端需在「同步面板-访问令牌」填同一值，
 *   请求头 X-Sync-Token 不匹配将返回 401（公网部署强烈建议开启）。
 */
const http = require('http');
const { DB_FILE, PORT } = process.env;

const fs = require('fs');
const path = require('path');

const port = parseInt(process.env.PORT || '8787', 10);
const dbFile = path.resolve(process.env.DB_FILE || 'sync-db.json');
const SYNC_TOKEN = process.env.SYNC_TOKEN || '';

// —— Gitee 持久化后端（免费云端存储，数据存于用户自己的 Gitee 仓库，天然带版本历史）——
// 启用条件：同时设置 GITEE_TOKEN + GITEE_REPO（如 ray597/wb-sync）
// 数据文件写入仓库的 GITEE_PATH（默认 sync-db.json，已在 .gitignore 排除，不会污染代码）
const GITEE_TOKEN = process.env.GITEE_TOKEN || '';
const GITEE_REPO = process.env.GITEE_REPO || '';
const GITEE_PATH = process.env.GITEE_PATH || 'sync-db.json';
const GITEE_BRANCH = process.env.GITEE_BRANCH || 'main';
const giteeMode = !!(GITEE_TOKEN && GITEE_REPO);

let memDb = { version:0, recs:{} };   // 内存权威数据
let giteeSha = null;                  // Gitee 上数据文件的 sha（更新文件必传）
let giteeDirty = false;
let giteeTimer = null;

function authOk(req){
  if(!SYNC_TOKEN) return true;                                  // 未配置令牌则不校验
  return req.headers['x-sync-token'] === SYNC_TOKEN;
}

function loadFile(){
  let d = { version:0, recs:{} };
  try{ const p = JSON.parse(fs.readFileSync(dbFile,'utf8')); d = { version: Number(p.version)||0, recs: p.recs||{} }; }catch(e){}
  return d;
}

async function fetchGiteeFile(){
  const r = await fetch(`https://gitee.com/api/v5/repos/${GITEE_REPO}/contents/${GITEE_PATH}?ref=${GITEE_BRANCH}`, { headers:{ Authorization:`token ${GITEE_TOKEN}` } });
  if (r.status === 404) return null;                            // 文件尚不存在
  if (!r.ok) throw new Error('gitee get '+r.status);
  const j = await r.json();
  if (!j || !j.content) return null;                            // Gitee 对不存在文件返回 200+[]（坑）
  return { sha: j.sha, db: JSON.parse(Buffer.from(j.content,'base64').toString('utf8')) };
}

async function initStorage(){
  if (!giteeMode) { memDb = loadFile(); return; }               // 本地文件模式
  try {
    const cur = await fetchGiteeFile();                          // 启动时从 Gitee 拉取最新数据
    if (cur) { memDb = { version:Number(cur.db.version)||0, recs: cur.db.recs||{} }; giteeSha = cur.sha; }
    console.log('[wb-sync] gitee storage ready, v'+memDb.version);
  } catch(e){ console.error('[wb-sync] gitee init failed (will retry on save):', e.message); }
}

function load(){ return memDb; }

function save(db){
  memDb = db;
  if (giteeMode) { giteeDirty = true; scheduleGiteeSave(); }     // 防抖异步写 Gitee
  else fs.writeFileSync(dbFile, JSON.stringify(db));             // 本地文件模式
}

function scheduleGiteeSave(){
  if (giteeTimer) return;
  giteeTimer = setTimeout(flushGitee, 500);
}
async function flushGitee(){
  giteeTimer = null;
  if (!giteeDirty) return;
  giteeDirty = false;
  const snapshot = JSON.parse(JSON.stringify(memDb));
  try{
    const url = `https://gitee.com/api/v5/repos/${GITEE_REPO}/contents/${GITEE_PATH}`;
    const body = {
      access_token: GITEE_TOKEN,
      content: Buffer.from(JSON.stringify(snapshot)).toString('base64'),
      message: `sync v${snapshot.version}`,
      branch: GITEE_BRANCH
    };
    if (giteeSha) body.sha = giteeSha;
    const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    const j = await r.json().catch(()=>({}));
    if (j.content && j.content.sha){ giteeSha = j.content.sha; return; }
    if (r.status === 409 || (j && j.message && /sha|conflict/i.test(j.message))){  // sha 过期 → 重读后重试
      try{ const cur = await fetchGiteeFile(); if (cur) giteeSha = cur.sha; }catch(e){}
      giteeDirty = true; scheduleGiteeSave(); return;
    }
    // 其他失败（限流/网络）：保留待写，5s 后重试
    giteeDirty = true; setTimeout(scheduleGiteeSave, 5000);
  }catch(e){
    giteeDirty = true; setTimeout(scheduleGiteeSave, 5000);
  }
}

const server = http.createServer((req, res) => {
  // CORS（演示用 *，生产请限定来源并启用鉴权）
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Sync-Token');
  if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }

  const url = new URL(req.url, 'http://localhost');

  if (req.method === 'GET' && url.pathname === '/sync') {
    if (!authOk(req)) { return err(res, 401, 'unauthorized'); }
    const db = load();
    const since = parseInt(url.searchParams.get('since') || '0', 10);
    // 无变化优化：since 与当前版本一致时返回空 recs
    const recs = (since === db.version) ? {} : db.recs;
    return ok(res, { ok:true, version: db.version, recs });
  }

  if (req.method === 'POST' && url.pathname === '/sync') {
    if (!authOk(req)) { return err(res, 401, 'unauthorized'); }
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      let payload; try{ payload = JSON.parse(body || '{}'); }catch(e){ return err(res, 400, 'bad json'); }
      const db = load();
      if (payload.base !== db.version) {
        // 并发冲突：返回 409 + 当前状态，让客户端重新拉取合并
        res.writeHead(409, {'Content-Type':'application/json'});
        return res.end(JSON.stringify({ version: db.version, recs: db.recs }));
      }
      const patch = payload.patch || {};
      for (const [id, rr] of Object.entries(patch)) {
        const cur = db.recs[id];
        const adopt = !cur
          || rr.ts > cur.ts
          || (rr.ts === cur.ts && rr.device > cur.device);
        if (adopt) db.recs[id] = rr;
      }
      db.version += 1;
      save(db);
      return ok(res, { ok:true, version: db.version, recs: db.recs });
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/') {
    // 同源托管前端页面：手机/电脑访问 http://<IP>:8787/ 即为完整工作台，
    // 与 /sync 同源，天然规避 https 页面 fetch http 端点的混合内容拦截。
    try{
      const html = fs.readFileSync(path.resolve(process.env.STATIC_FILE || 'index.html'), 'utf8');
      res.writeHead(200, {'Content-Type':'text/html; charset=utf-8'});
      return res.end(html);
    }catch(e){ res.writeHead(500); return res.end('static file not found (set STATIC_FILE)'); }
  }

  if (url.pathname === '/healthz') { return ok(res, { ok:true }); }
  res.writeHead(404); res.end('not found');
});

function ok(res, obj){ res.writeHead(200, {'Content-Type':'application/json'}); res.end(JSON.stringify(obj)); }
function err(res, code, msg){ res.writeHead(code, {'Content-Type':'application/json'}); res.end(JSON.stringify({ error:msg })); }

initStorage().then(()=>{
  server.listen(port, '0.0.0.0', () => {
    console.log(`[wb-sync] listening on http://0.0.0.0:${port}/sync  (storage: ${giteeMode?('gitee '+GITEE_REPO+'/'+GITEE_PATH):dbFile})`);
  });
});
