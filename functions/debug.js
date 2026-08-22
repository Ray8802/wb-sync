// Cloudflare Pages Functions · 诊断端点 GET /debug
// 返回各环境变量是否存在、长度、前后 4 位（中间打码），用于排查变量注入问题
export async function onRequestGet(ctx) {
  const { env } = ctx;
  const mask = (v) => {
    if (v === undefined || v === null || v === '') return '(空/未设置)';
    return `${String(v).length} 字符 · 前4:[${String(v).slice(0, 4)}] 后4:[${String(v).slice(-4)}]`;
  };
  const out = {
    GITEE_TOKEN: mask(env.GITEE_TOKEN),
    GITEE_REPO: mask(env.GITEE_REPO),
    GITEE_PATH: mask(env.GITEE_PATH),
    SYNC_TOKEN: mask(env.SYNC_TOKEN)
  };
  return new Response(JSON.stringify(out, null, 1), {
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
}
