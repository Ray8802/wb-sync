// Cloudflare Pages Functions · 诊断端点 GET /debug
// 返回各环境变量是否存在及其长度（不泄露值），用于排查变量注入问题
export async function onRequestGet(ctx) {
  const { env } = ctx;
  const mask = (v) => (v === undefined || v === null || v === '' ? '(空/未设置)' : String(v).length + ' 字符');
  const out = {
    GITEE_TOKEN: mask(env.GITEE_TOKEN),
    GITEE_REPO: mask(env.GITEE_REPO),
    GITEE_PATH: mask(env.GITEE_PATH),
    GITEE_BRANCH: mask(env.GITEE_BRANCH),
    SYNC_TOKEN: mask(env.SYNC_TOKEN)
  };
  return new Response(JSON.stringify(out, null, 1), {
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
}
