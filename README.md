# Spec Advisor — 採購規格書 AI 審查助手

採購規格書審查輔助系統，讓採購人員上傳規格書（PDF/Word/Excel），由 AI 自動進行綁標檢測、法規合規、商務風險等 13 種審查，並產出結構化 Markdown 報告。

目前版本：**v1.9.2**

---

## 目錄

1. [系統架構](#系統架構)
2. [分析功能清單](#分析功能清單)
3. [知識庫清單](#知識庫清單)
4. [專案目錄結構](#專案目錄結構)
5. [開發指南](#開發指南)
6. [部署流程](#部署流程)
7. [版本歷程](#版本歷程)
8. [未來規劃 Phase 3](#未來規劃-phase-3)

---

## 系統架構

### 技術棧

| 層級 | 技術 |
|------|------|
| Frontend | React 18 + Vite 6 + TailwindCSS + react-markdown |
| Backend | Python 3.12 + FastAPI + uvicorn |
| Database | SQLite（aiosqlite 非同步驅動） |
| LLM | qwen3.6-35b-a3b-mtp via CLIProxyAPI |
| Embedding | fastembed + `BAAI/bge-small-zh-v1.5`（bake 進 image） |
| 容器化 | Docker Compose |

### 部署環境

- **主機**：Raspberry Pi 5（4GB RAM）
- **IP**：`192.168.88.115`
- **SSH**：`pi@192.168.88.115`
- **對外 Port**：`80`（frontend nginx → proxy 到 backend:8000）
- **LLM API**：`http://192.168.88.115:8317/v1`（CLIProxyAPI，本機端點）

### 服務拓撲

```
瀏覽器 :80
  └── spec-advisor-frontend (nginx)
        └── /api/* → spec-advisor-backend :8000
                        ├── SQLite  ./data/spec_advisor.db
                        ├── uploads ./uploads/
                        └── LLM     :8317/v1/chat/completions
```

### Embedding 機制

- 知識庫上傳時自動切 chunk（以「第○條」或雙換行為界，500 字 / chunk，80 字 overlap）並計算 embedding
- 分析時先以關鍵字組成 query，做 cosine similarity 搜索取 top-15 相關 chunk（相關度 > 0.3）
- 若無 embedding 資料，fallback 至關鍵字比對截取
- Model 檔案在 build 時預下載至 `/opt/models`，runtime 不需連網

---

## 分析功能清單

共 13 種分析 + 1 種文件比較。每種分析皆為非同步 Job（POST 觸發 → 輪詢 `/api/analysis/jobs/{job_id}`）。

### 📋 基礎審查

| 功能 | API Endpoint | 說明 |
|------|-------------|------|
| 綜合分析 | `POST /api/analysis/{doc_id}/full` | 一次涵蓋綁標、合理性、法規、SLA、供應商鎖定、ISMS、BCP-DR、互通性等全部面向 |
| 綁標檢測 | `POST /api/analysis/{doc_id}/binding` | 檢測品牌指定、獨家規格、不合理門檻、限制性條款 |
| 合理性分析 | `POST /api/analysis/{doc_id}/reasonability` | 評估規格完整性、數值合理性、一致性、可驗收性、市場可行性 |

### 🔒 法規合規

| 功能 | API Endpoint | 說明 |
|------|-------------|------|
| 資安合規 | `POST /api/analysis/{doc_id}/security` | 依資通安全責任等級分三段（個資治理 / 存取加密 / 稽核弱點）以結構化 JSON 輸出，自動套用防護基準控制措施 |
| 個資保護影響評估 (PIA) | `POST /api/analysis/{doc_id}/pia` | 蒐集目的限制、保存期限、跨境傳輸、去識別化、當事人權利、通報流程 |
| 智財授權檢視 | `POST /api/analysis/{doc_id}/intellectual-property` | 智財歸屬、授權範圍/期間/類型、開源元件、退場資料權利、稽核罰則 |
| ISMS 合規檢查 | `POST /api/analysis/{doc_id}/isms` | ISO 27001:2022 Annex A 管理面評估（組織/人員/實體/技術控制框架、認證要求、SoA、稽核義務） |

### 💰 商務風險

| 功能 | API Endpoint | 說明 |
|------|-------------|------|
| 成本合理性 | `POST /api/analysis/{doc_id}/cost` | 規格等級、數量、市場估算、替代方案、TCO |
| 服務水準分析 (SLA) | `POST /api/analysis/{doc_id}/sla` | 可用性承諾、MTTR/MTBF、效能指標、罰則、維護窗口、升級流程 |
| 供應商鎖定風險 | `POST /api/analysis/{doc_id}/vendor-lockin` | 資料可攜性、開放標準、退場條款、原始碼交付、移轉成本 |
| 營運持續/災難復原 | `POST /api/analysis/{doc_id}/bcp-dr` | RPO/RTO/MTPD、備援架構、備份策略、異地備份、DR 演練、ISO 22301 |

### 🏥 醫療專業

| 功能 | API Endpoint | 說明 |
|------|-------------|------|
| 醫療互通性檢查 | `POST /api/analysis/{doc_id}/interoperability` | HL7 FHIR/V2、DICOM、IHE Profile、HIS/PACS/LIS 整合、ICD-10/LOINC/SNOMED CT、電子病歷交換 |

### 📝 產出

| 功能 | API Endpoint | 說明 |
|------|-------------|------|
| 改善建議 | `POST /api/analysis/{doc_id}/improvement` | 產出修改後規格書草稿，修改處以 ✏️ 標示並附修改原因 |

### 其他

| 功能 | API Endpoint | 說明 |
|------|-------------|------|
| 文件比較 | `POST /api/analysis/compare` | 同步比較兩份規格書差異（主要差異 / 規格變更 / 新增刪除 / 影響評估） |

---

## 知識庫清單

知識庫存於 SQLite，上傳後自動建 embedding chunks。分析時依啟用狀態與類型自動檢索。

目前知識庫（依類別）：

**政府法規（law）**
- 個人資料保護法
- 個人資料保護法施行細則
- 政府採購法
- 資通安全管理法
- 資通安全管理法施行細則

**產業標準（standard）**
- ISO 27001 Annex A 控制措施
- 醫療資訊互通性標準
- 營運持續與災難復原管理

**院內規章（internal_rule）**
- 付款條件（院內）
- 資訊要求（院內）

> 知識庫可在 UI「知識庫」頁面新增/編輯/停用，或透過 `POST /api/knowledge/upload` API 上傳文件（PDF/Word/Excel/TXT）。

---

## 專案目錄結構

```
spec-advisor/
├── docker-compose.yml          # 容器服務定義（backend + frontend）
├── .env                        # 環境變數（LLM_API_BASE_URL, LLM_MODEL 等）
├── data/                       # SQLite DB（volume mount，持久化）
├── uploads/                    # 上傳的規格書暫存（volume mount）
├── models/                     # 備用 model 目錄（volume mount）
│
├── backend/
│   ├── Dockerfile              # python:3.12-slim，build 時預下載 embedding model
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app 入口，掛載所有 router
│       ├── config.py           # 環境變數設定（LLM URL / model / DB path 等）
│       ├── database.py         # SQLAlchemy async engine / session
│       ├── models.py           # ORM 資料模型（Document, KnowledgeBase, AnalysisJob...）
│       ├── routers/
│       │   ├── analysis.py     # 分析 API（13 種 + compare）
│       │   ├── documents.py    # 文件上傳 / 列表 / 刪除
│       │   ├── knowledge.py    # 知識庫 CRUD + 重建 embedding
│       │   ├── controls.py     # 資通系統防護基準控制措施匯入管理
│       │   ├── reviews.py      # 人工審閱記錄
│       │   ├── templates.py    # 規格書範本產生
│       │   └── bid.py          # 投標須知填寫輔助
│       └── services/
│           ├── llm.py          # 所有 LLM prompt 定義 + call_llm + embedding retrieval
│           ├── analysis_jobs.py # 非同步 Job runner（asyncio.create_task）
│           ├── embedding.py    # fastembed wrapper（chunk / embed / cosine search）
│           └── parser.py       # 文件解析（PDF/Word/Excel → 純文字）
│
└── frontend/
    ├── Dockerfile              # nginx，build 後 COPY dist
    ├── package.json            # 版本號在此（v1.9.1）
    ├── vite.config.js          # 從 package.json 讀版本號注入 __APP_VERSION__
    └── src/
        ├── App.jsx             # 路由 + 顯示版本號
        ├── api.js              # axios 封裝，所有 API 呼叫集中於此
        ├── pages/
        │   ├── AnalysisPage.jsx    # 主要分析 UI（分析按鈕分組、知識庫選擇、Job 輪詢）
        │   ├── DocumentsPage.jsx   # 文件上傳管理
        │   ├── KnowledgePage.jsx   # 知識庫管理
        │   ├── ControlsPage.jsx    # 資通系統防護基準匯入
        │   ├── ComparePage.jsx     # 文件比較
        │   ├── ReviewsPage.jsx     # 人工審閱
        │   ├── TemplatesPage.jsx   # 規格書範本
        │   └── BidNoticePage.jsx   # 投標須知產生
        └── components/
            └── MarkdownView.jsx    # react-markdown + remark-gfm + rehype-raw 渲染
```

---

## 開發指南

### 本機開發

**前置條件**：需能連到 `http://192.168.88.115:8317/v1`（Pi 上的 CLIProxyAPI）

```bash
# Backend（在另一個終端）
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev        # http://localhost:3000，自動 proxy /api → localhost:8000
```

`vite.config.js` 已設定 proxy，開發時 frontend 會把 `/api` 轉到 `localhost:8000`。

### 新增一種分析類型

需要修改以下 **4 個檔案**，依序操作：

**1. `backend/app/services/llm.py`**

新增 prompt 常數與 `analyze_xxx` 函式：

```python
XXX_PROMPT = """請對以下規格書進行 XXX 分析。

## 審查依據
{knowledge_context}

## 檢查項目
...

## 規格書內容
{content}"""

async def analyze_xxx(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "xxx")
    return await call_llm(XXX_PROMPT.format(knowledge_context=kb, content=content[:8000]))
```

也要在 `get_keywords_for_analysis()` 的 `keywords` dict 加入 `"xxx": [...]`，讓 embedding retrieval 的 query 更精準。

**2. `backend/app/services/analysis_jobs.py`**

```python
from app.services.llm import ..., analyze_xxx

ANALYSIS_HANDLERS = {
    ...
    "xxx": analyze_xxx,
}

ANALYSIS_LABELS = {
    ...
    "xxx": "XXX 分析",
}
```

**3. `backend/app/routers/analysis.py`**

```python
@router.post("/{doc_id}/xxx")
async def check_xxx(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "xxx", req, db)
```

**4. `frontend/src/pages/AnalysisPage.jsx`**

在 `analysisTypes` 陣列加入：

```javascript
{ key: 'xxx', label: 'XXX 分析', icon: SomeIcon, fn: analyzeXxx, color: 'blue' },
```

在 `analysisGroups` 的對應 group 的 `keys` 加入 `'xxx'`。

同時在 `frontend/src/api.js` 新增對應的 axios 函式：

```javascript
export const analyzeXxx = (docId, knowledgeIds) =>
  api.post(`/api/analysis/${docId}/xxx`, { knowledge_ids: knowledgeIds })
```

### 新增知識庫

**方式 A：UI 操作**（推薦）

前往「知識庫」頁面 → 「新增知識庫」→ 選擇類別（政府法規/院內規章/產業標準/自訂）→ 上傳 PDF/Word/Excel/TXT 或貼上文字。上傳後系統自動建立 embedding chunks。

**方式 B：API**

```bash
curl -X POST http://192.168.88.115/api/knowledge/upload \
  -F "name=XXX法" \
  -F "category=law" \
  -F "source=法規來源說明" \
  -F "file=@xxx.pdf"
```

**類別代碼**：`law`（政府法規）、`internal_rule`（院內規章）、`standard`（產業標準）、`custom`（自訂）

若更新知識庫內容後需重建 embedding，可呼叫：

```bash
curl -X POST http://192.168.88.115/api/knowledge/re-embed
```

---

## 部署流程

### 重要：程式碼 bake 進 image

`docker-compose.yml` 不使用 volume mount 掛載程式碼，程式碼在 `docker compose build` 時透過 `COPY . .` 打包進 image。**每次修改程式碼後都必須重新 build image 才會生效。**

持久化資料（DB / 上傳檔案）透過 volume mount：
- `./data` → `/app/data`（SQLite DB）
- `./uploads` → `/app/uploads`（規格書檔案）
- `./models` → `/app/models`（備用 model 目錄）

### 版本號更新

版本號只需改一個地方，其他自動讀取：

1. 修改 `frontend/package.json` 的 `"version"` 欄位
2. `vite.config.js` 會在 build 時讀取並注入為由 Vite define 注入的全域常數 `__APP_VERSION__`
3. `App.jsx` 讀取 `__APP_VERSION__` 顯示在 UI 右上角

### 部署步驟

從 Windows 開發機部署到 Pi，使用 `pscp`（PuTTY）：

```powershell
# 1. 把最新程式碼複製到 Pi
pscp -r D:\workspace\spec-advisor\backend pi@192.168.88.115:~/spec-advisor/
pscp -r D:\workspace\spec-advisor\frontend pi@192.168.88.115:~/spec-advisor/
pscp D:\workspace\spec-advisor\docker-compose.yml pi@192.168.88.115:~/spec-advisor/

# 2. SSH 進 Pi 重建 image 並重啟
plink pi@192.168.88.115 "cd ~/spec-advisor && docker compose build && docker compose up -d"
```

或用 `plink` 一行執行（需要 Pi 密碼）：

```powershell
plink -batch pi@192.168.88.115 "cd ~/spec-advisor && docker compose build --no-cache && docker compose up -d --force-recreate"
```

> `--no-cache` 確保 embedding model 不會被舊 layer 快取跳過；一般更新程式碼時可省略以節省時間。

### 查看 Log

```bash
# SSH 進 Pi
docker logs spec-advisor-backend -f
docker logs spec-advisor-frontend -f
```

---

## 版本歷程

| 版本 | 主要變更 |
|------|---------|
| **v1.8.0** | 初始 7 種分析（full / binding / reasonability / cost / security / intellectual_property / improvement） |
| **v1.8.x** | 資通安全分級欄位、Markdown 編排修正、機關類型選項補充 |
| **v1.8.8** | 新增智財授權檢視（intellectual_property） |
| **v1.8.9** | 文件上傳補充資通安全分級欄位 |
| **v1.9.0** | **Phase 1**：新增 PIA（個資保護影響評估）、SLA（服務水準分析）、Vendor Lock-in（供應商鎖定風險）<br>**Phase 2**：新增 Interoperability（醫療互通性）、ISMS（ISO 27001 合規）、BCP-DR（營運持續/災難復原）<br>Embedding retrieval 上線（fastembed + BAAI/bge-small-zh-v1.5） |
| **v1.9.1** | UI 分析按鈕依功能分組（📋 基礎審查 / 🔒 法規合規 / 💰 商務風險 / 🏥 醫療專業 / 📝 產出） |

---

## 未來規劃 Phase 3

| 功能 | 說明 | 狀態 |
|------|------|------|
| 歷史案件比對 | 將已分析的規格書結果做 embedding，新案上傳後搜索相似歷史案件供參考，降低重複審查成本 | 規劃中 |
| 價格合理性分析 | 串接政府電子採購網（https://web.pcc.gov.tw），比對同類採購歷史決標價格 | 規劃中 |
| TCO 總持有成本建模 | 結合規格書的維護條款、授權模式、替換成本，建立 5 年 TCO 預測模型 | 規劃中 |
