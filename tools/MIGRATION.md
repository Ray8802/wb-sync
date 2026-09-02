# 炒股工作台 · 跨电脑迁移指南（MIGRATION）

> 本目录（`tools/`）包含工作台的全部本地辅助脚本。迁移到新电脑时，
> clone 本仓库后即可获得完整环境。云端数据与部署**不依赖本机**，无需迁移。

## 一、架构总览（哪些在云端，哪些在本机）

| 组件 | 位置 | 换电脑是否受影响 |
| --- | --- | --- |
| 前端 + API（Cloudflare Pages） | GitHub `Ray8802/wb-sync` → `https://wb-sync.pages.dev` | 否，仓库自动构建 |
| 同步数据 sync-db.json（自选股清单） | Gitee `ray597/wb-sync`（私有）+ GitHub 镜像 | 否，云端存储 |
| 每日收盘财报自动化任务 | WorkBuddy 账号（automation id `automation-1788260309493`） | 否，登录同账号即有 |
| 本目录辅助脚本（行情抓取/报告生成/邮件发送） | 本机 + 本仓库 `tools/` | 需要在新电脑 clone |
| QQ 邮箱 Connector、Gitee/GitHub 令牌 | WorkBuddy Connector + 环境变量 | 需在新电脑重新配置 |

## 二、新电脑迁移步骤

### 1. 安装基础环境
- Python 3.10+（图表/数据处理），需 `pip install pandas matplotlib openpyxl pillow`
- Node.js 18+（如需要跑 sync-server / Pages Functions 本地调试）
- git（克隆仓库用）

### 2. 克隆仓库
```bash
git clone https://github.com/Ray8802/wb-sync.git
cd wb-sync
# tools/ 目录即本辅助脚本集
```

### 3. 配置云端令牌（环境变量）
复制 `.env.example`（仓库根目录）并按说明填写：
- `GITEE_TOKEN`：Gitee 私人令牌（同步数据落库用，仓库 `ray597/wb-sync`）
- `SYNC_TOKEN=wb-sync-ray-2026`：同步接口鉴权
- `GH_TOKEN`：GitHub 令牌（更新 Pages 静态文件用）
> 令牌请勿写入公开仓库。可在新电脑系统环境变量或 WorkBuddy 环境变量中配置。

### 4. 连接 QQ 邮箱 Connector
- 打开 WorkBuddy → 连接管理 → QQ 邮箱（agent-mail/qq-mail），用同一 QQ 账号授权
- 验证：发一封测试邮件到 1635661684@qq.com

### 5. 确认自动化任务
- 登录 WorkBuddy 同一账号 → 自动化 → 查看「每日收盘财报」任务（`automation-1788260309493`）
- 任务在云端运行，新电脑无需重复创建

### 6. 验证
- 打开 https://wb-sync.pages.dev 确认工作台在线
- 手动跑一次：`python tools/fetch_news_3src.py && python tools/filter_news_v6.py && python tools/build_email_v6.py`

## 三、每日收盘财报生产流程（tools/）

```bash
# 1) 抓取行情 + 自选股数据（腾讯行情 + 资金流）
python tools/watchlist_review.py          # 输出 watchlist_data/quotes.json
python tools/watchlist_charts.py          # 输出 3 张自选股图表 PNG

# 2) 抓取三源新闻（金十/财联社/东方财富，含翻页+签名）
python tools/fetch_news_3src.py           # 输出 news_raw_<date>.json
python tools/filter_news_v6.py            # 个股 top3 + 板块 top3
python tools/build_email_v6.py            # 生成邮件 HTML（report_cdn_v6.html）

# 3) 构建完整报告（HTML，图表 base64 内嵌）
python tools/build_watchlist_full.py      # 输出 watchlist_report_<date>.html

# 4) 发送邮件（通过 agent-mail MCP，正文内联图表用 CDN 图）
#    图表 PNG 需先上传到 GitHub charts/ 目录（Pages CDN 自动构建）
```

## 四、三源新闻接口速查（脚本已实现，此处备忘）

| 源 | 接口 | 要点 |
| --- | --- | --- |
| 金十 | `flash-api.jin10.com/get_flash_list` | `max_time` 传 **URL 编码的字符串时间**（非时间戳）；header `x-app-id: bVBF4FyRTn5NJF5n`、`x-version: 1.0.0` |
| 财联社 | `www.cls.cn/v1/roll/get_roll_list` | **sign = md5(sha1(query_string))**；条目时间字段为 `ctime`（秒）；rn≤30 |
| 东财 | `np-listapi.eastmoney.com/comm/web/getFastNewsList` | `sortEnd` 游标翻页；`showTime` 为 "YYYY-MM-DD HH:MM:SS" |

## 五、邮件正文注意事项（重要）

- QQ 邮箱会剥离 `<style>` 块 → 邮件 HTML **全部用内联 style**
- 正文禁裸换行（会渲染成可见 `\n`）→ 生成紧凑单行 HTML，属性引号用单引号
- 图表正文内联用 **CDN 远程图**（`https://wb-sync.pages.dev/charts/*.png`），用户点一次【显示图片】后自动显示；CID 内联在 QQ 邮箱无效
- 附件直发用 agent-mail `upload_attachment`（返回 file_id）+ SendMessage `file_refs`
