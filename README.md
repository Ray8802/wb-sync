# 炒股工作台 · 云端同步（Cloudflare Pages 版）

手机**在任何网络（WiFi / 4G / 5G）**下都能打开工作台，并和电脑实时同步。
**完全免费 · 免绑卡 · 云端永远在线**（无需电脑常开）。

## 架构

```
手机/电脑浏览器 ──HTTPS──▶ https://xxx.pages.dev（Cloudflare Pages）
                              ├─ /          → 工作台前端页面（index.html）
                              └─ /sync      → 同步 API（functions/sync.js）
                                                   │ 数据持久化
                                                   ▼
                                        Gitee 仓库 sync-db.json（免费、版本历史）
```

- 前端页面：`index.html`（单文件工作台）
- 同步 API：`functions/sync.js`（Cloudflare Pages Functions）
- 数据：写入你自己的 Gitee 仓库 `sync-db.json`（每次同步自动生成一次 git 提交 = 版本历史）

## 部署（Cloudflare Pages，约 5 分钟）

1. 打开 https://dash.cloudflare.com → 注册（邮箱，**无需信用卡**）
2. 左侧 **Workers & Pages → Create → Pages → Connect to Git**
3. 授权 GitHub → 选择仓库 `Ray8802/wb-sync` → 分支 `main`
4. 构建配置：
   - **Framework preset**：None
   - **Build command**：留空（无需构建）
   - **Build output directory**：`/`（根目录）
5. **环境变量**（Production 下添加）：
   ```
   GITEE_TOKEN = 你的Gitee私人令牌
   GITEE_REPO  = ray597/wb-sync
   GITEE_PATH  = sync-db.json
   SYNC_TOKEN  = 自定义访问令牌（安全）
   ```
6. **Save and Deploy** → 1-2 分钟后得到 `https://wb-sync.pages.dev`
7. 验证：打开 `https://wb-sync.pages.dev/` 看到工作台；`/healthz`…（可选）打开 `/sync` 应 401（无令牌）

## 手机 / 电脑使用

| 项 | 填什么 |
|---|---|
| 访问地址 | `https://wb-sync.pages.dev` |
| 同步面板·端点 | `https://wb-sync.pages.dev/sync` |
| 同步面板·令牌 | 你设置的 `SYNC_TOKEN` |

任一端增删自选股 → 另一端 30 秒内自动同步。

## 本地测试（可选）

```bash
# 用 node 直接模拟调用 functions/sync.js（需设置环境变量）
GITEE_TOKEN=xxx GITEE_REPO=ray597/wb-sync node -e "…"
```

## 免费额度（Cloudflare Pages）

- Pages 静态托管：无限请求
- Pages Functions：免费 100,000 次/天（个人使用绰绰有余）
- 数据存储：Gitee 免费仓库（每次同步一次 commit，频率足够低不会触发限流）
