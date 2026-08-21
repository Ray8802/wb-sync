# 炒股工作台 · 云端同步服务端（公网部署包）

把同步服务端部署到公网后，手机**在任何网络（WiFi / 4G / 5G 流量）**下都能和电脑实时同步。
本目录内的 `sync-server.js` 已内置：

- GET/POST `/sync`（LWW 合并 + 版本号 + 409 并发回拉）
- 同源托管前端页面（访问 `https://你的域名/` 就是完整工作台，无需单独部署前端）
- 可选访问令牌（`SYNC_TOKEN` 环境变量，公网部署强烈建议开启）
- **Gitee 持久化后端**（`GITEE_TOKEN + GITEE_REPO`）：数据自动存进你自己的 Gitee 仓库，免费、重启不丢、带版本历史
- 零依赖（纯 Node 标准库），任意 Node ≥ 18 平台可跑

---

## 方式一：Render（推荐，免费，约 3 分钟）

> 本目录已打好可直接上传的包：`wb-sync-deploy.zip`（上级目录）

### 路线 A：网页直接上传 zip（最快，无需 Git）

1. 打开 https://render.com → 注册（支持 GitHub / Google / 邮箱）
2. 右上角 **New → Blueprint**
3. 切到 **Upload** 标签页，把 `wb-sync-deploy.zip` 拖进去（或点击选择文件）
4. 页面识别出 `render.yaml` 后点 **Apply**，等 1-2 分钟部署完成
5. 得到地址 `https://wb-sync.onrender.com`（服务名可在 render.yaml 的 `name` 改）
6. 到 **Dashboard → 你的服务 → Environment** 查看自动生成的 `SYNC_TOKEN` 值

### 路线 B：Git 仓库（进阶）

1. 把本目录推到一个 Git 仓库（GitHub/GitLab 均可）
2. Render → **New → Blueprint** → 连接该仓库 → Apply

## 方式二：Railway（免费）

1. 打开 https://railway.com → 注册
2. **New Project → Deploy from GitHub**，选择包含本目录的仓库
3. 自动识别 `railway.toml`，等待部署
4. 在 Variables 里手动添加 `SYNC_TOKEN`（随意填一个长随机串，如 `wb-sync-8f3k2m...`）
5. 部署成功后得到地址 `https://xxx.up.railway.app`

## 方式三：任意云服务器 / 家里的电脑（有公网 IP）

```bash
node sync-server.js          # 或 PM2：pm2 start sync-server.js
# 记得设置环境变量：SYNC_TOKEN=你的密钥  PORT=8787
# 用 Nginx 反代到 443 + HTTPS 证书
```

---

## 手机/电脑如何连接

1. 打开工作台页面（访问部署后的 `https://你的域名/`，或本地文件）
2. 点击顶栏 **同步图标** → 打开同步面板
3. **云端端点**填：`https://你的域名/sync`
4. **访问令牌**填：Render/Railway 里那个 `SYNC_TOKEN` 值（若服务端未设置则留空）
5. 点 **立即同步** → 状态变为「已同步」

以后任一端增删自选股，另一端 30 秒内自动同步（或手动点立即同步）。

> 提示：端点填一次即可，浏览器会自动记住（localStorage）。

---

## 环境变量说明

| 变量 | 必填 | 说明 |
|---|---|---|
| `PORT` | 否 | 监听端口，默认 `8787`（平台会自动注入） |
| `SYNC_TOKEN` | 强烈建议 | 访问令牌；设置后前端必须填相同值，否则 401 |
| `GITEE_TOKEN` | 推荐（免费持久化） | Gitee 私人令牌；**设置后数据自动存入你的 Gitee 仓库**（免费、带版本历史、重启不丢） |
| `GITEE_REPO` | 推荐 | Gitee 仓库，如 `ray597/wb-sync` |
| `GITEE_PATH` | 否 | 数据文件在仓库中的路径，默认 `sync-db.json`（已被 .gitignore 排除，不污染代码） |
| `GITEE_BRANCH` | 否 | 数据写入的分支，默认 `main` |
| `STATIC_FILE` | 否 | 托管的前端 HTML，默认 `./index.html`（本目录已带） |

> **为什么推荐 Gitee 持久化**：免费云平台（如 Render 免费版）的磁盘是临时的，重启/重新部署会清空文件。
> 设置 `GITEE_TOKEN + GITEE_REPO` 后，服务每次保存数据都会（防抖 500ms）自动提交到你的 Gitee 仓库
> `sync-db.json` 文件——数据永远安全，还自带提交历史，服务重启/换机器都不丢。

## 本地开发测试

```bash
PORT=8787 node sync-server.js
# 浏览器打开 http://127.0.0.1:8787/ 即工作台；/sync 为同步接口

# 启用 Gitee 持久化：
GITEE_TOKEN=你的私人令牌 GITEE_REPO=你的名字/wb-sync PORT=8787 node sync-server.js
```
