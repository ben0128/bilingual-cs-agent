# Nova Mart 中英雙語電商客服 Voice Agent

顧客打電話問「我的訂單到哪了？」或「可以退貨嗎？」，Agent 中英文都能接，顧客換語言它也跟著換。

- **語音**：ElevenAgents（辨識、LLM、合成、語言偵測）
- **訂單 API**：FastAPI，部署在 Cloudflare Workers（Python Workers）
- **Demo 頁**：同一個 Worker 提供的靜態頁面，內嵌 ElevenAgents widget

```text
bilingual-cs-agent/
├── order-api/                 # Cloudflare Worker（FastAPI）
│   ├── src/
│   │   ├── main.py            # Workers 入口
│   │   ├── api.py             # 路由：/tools/order-status、/tools/return-eligibility、/health
│   │   ├── auth.py            # X-Tool-Secret 驗證
│   │   ├── normalize.py       # 訂單編號正規化（中文數字、幺洞拐、全形、空白）
│   │   ├── repository.py      # 查詢（無狀態，每次請求換算日期）
│   │   ├── returns.py         # 退貨規則（純函式）
│   │   └── seed.py            # 6 筆假訂單
│   ├── public/index.html      # Demo 頁
│   ├── tests/test_api.py      # 28 個測試
│   ├── pyproject.toml
│   └── wrangler.jsonc
└── agent/                     # 要貼進 ElevenAgents 的內容
    ├── setup_agent.py         # 用 API 一次建好 Agent（第 5 步的自動版）
    ├── system-prompt.md
    ├── first-messages.md
    ├── language-detection-description.txt
    ├── knowledge/return-policy.md
    └── tools/*.json           # webhook tool 的參考設定
```

---

## 1. 安裝工具（個人電腦，只需一次）

| 工具 | 用途 | 安裝 |
| --- | --- | --- |
| uv | 管理 Python 3.13 與套件 | macOS / Linux：`curl -LsSf https://astral.sh/uv/install.sh \| sh`<br>Windows：`powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Node.js 20+ | wrangler（Cloudflare CLI）需要 | https://nodejs.org 下載 LTS |
| Cloudflare 帳號 | 部署 Worker | 免費方案即可 |
| ElevenLabs 帳號 | 建立 Agent | 免費方案每月 15 分鐘通話 |

Python 3.13 不用自己裝，`uv` 會自動下載。`pywrangler` 需要 **uv 0.12.3 以上**，已經裝過舊版的話先跑 `uv self update`。

第一次跑 `pywrangler dev` 時，它會從 Cloudflare 下載 Pyodide 執行環境，需要能連外網。

## 2. 跑測試

```bash
cd order-api
uv sync
uv run pytest
```

應該看到 `28 passed`。

## 3. 本機跑 Worker

```bash
# 產生共用密鑰（記下來，第 4、5 步也要用）
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"

cp .dev.vars.example .dev.vars      # 把密鑰貼進 .dev.vars
uv run pywrangler dev               # 跑在 http://localhost:8787
```

另開一個終端機測試（用中文數字也能查到）：

```bash
curl -X POST http://localhost:8787/tools/order-status \
  -H "Content-Type: application/json" \
  -H "X-Tool-Secret: <你的密鑰>" \
  -d '{"order_id":"五八二一零四七三","phone_last4":"0912"}'
```

## 4. 部署到 Cloudflare

```bash
npx wrangler login                  # 開瀏覽器登入 Cloudflare
uv run pywrangler deploy            # 部署，終端機會印出 https://nova-order-api.<你的子網域>.workers.dev
npx wrangler secret put TOOL_SECRET # 貼上同一把密鑰
```

用 workers.dev 網址再跑一次第 3 步的 `curl`。第一次請求如果比較慢，是 Python Worker 冷啟動，Demo 前先打一次 `/health` 暖機。

> ElevenAgents 只能打公開網址，所以不需要 ngrok：開發時直接部署到 workers.dev，部署只要幾秒。

## 5. 在 ElevenAgents 建 Agent

### 自動（建議）

`agent/setup_agent.py` 用 API 建好下面手動步驟的所有東西：secret、知識庫、兩支 webhook tool、Agent、中英文聲音，並限制只有你的 workers.dev 網域能開啟通話。只用 Python 標準函式庫，不用裝套件。

1. 在 ElevenLabs 建一把 API key，權限只開 **ElevenAgents 讀寫**、**Voices 讀寫**，其他全關。
2. 寫進 repo 根目錄的 `.env`（已在 `.gitignore`）：`ELEVENLABS_API_KEY=...`
3. 執行（`TOOL_SECRET` 從 `order-api/.dev.vars` 讀）：

```bash
WORKER_URL=https://nova-order-api.<你的子網域>.workers.dev python3 agent/setup_agent.py
```

最後一行會印出 Agent ID。改了 prompt 或知識庫之後重跑同一個指令即可，已存在的東西會沿用、Agent 會更新。

### 手動

1. 新增一支 Agent，主要語言選**中文**，Additional Languages 加**英文**。
2. 每種語言各選一個聲音：中文挑台灣口音，英文挑英文母語。
3. 首句照 `agent/first-messages.md` 設定，英文那句要手動改掉自動翻譯。
4. System prompt 貼上 `agent/system-prompt.md`。
5. LLM 選一個高能力模型（官方建議用 tool 時避開 Gemini 2.0 Flash）。
6. 知識庫上傳 `agent/knowledge/return-policy.md`，使用模式設成 **Prompt**。
7. 在 Secrets 新增 `TOOL_SECRET`（同一把密鑰）。
8. 新增兩支 **Webhook tool**，照 `agent/tools/*.json` 設定：
   - Method `POST`，URL 換成你的 workers.dev 網址
   - Body 參數 `order_id`、`phone_last4`（string，必填），描述照抄
   - Header `X-Tool-Secret` 綁定剛剛的 secret
9. 開啟 System tools：`language_detection`（描述換成 `agent/language-detection-description.txt` 的內容）和 `end_call`。
10. 在 dashboard 直接通話，先測「我的訂單 58210473 到哪了？」，再測中途改英文。

## 6. Demo 頁

1. 把 `order-api/public/index.html` 裡 `agent-id` 換成你的 Agent ID。
2. `uv run pywrangler deploy`
3. 打開 workers.dev 網址，右下角就是通話按鈕。

## 測試訂單

手機末 4 碼一律 `0912`。

| 訂單編號 | 情境 |
| --- | --- |
| 58210473 | 已出貨，明天到 |
| 58210488 | 3 天前送達，可退 |
| 58210491 | 超過 7 天，不能退 |
| 58210502 | 生鮮，不能退 |
| 58210515 | 處理中 |
| 58210520 | 已取消 |

## 安全

- `.dev.vars`、`.env` 已在 `.gitignore`，不要 commit。
- ElevenLabs API Key 不需要放進 Worker；只有用 ElevenLabs CLI 時才需要，放本機 `.env`。
- API 不記錄手機末 4 碼；末 4 碼錯誤與查無訂單回同一個錯誤碼。
