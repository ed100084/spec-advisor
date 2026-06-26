"""LLM 服務 - 透過 CLIProxyAPI 接各 LLM"""
import httpx
from sqlalchemy import select

from app.config import settings

SYSTEM_PROMPT = """你是一位專業的採購規格書審查顧問。你的任務是分析規格書內容，依據相關法規與規章找出潛在問題並提供改善建議。
請以繁體中文回覆，使用結構化的 Markdown 格式（標題、表格、清單）。
重要：每項發現都必須引用具體的法規條文或規章依據，格式為【依據：○○○ 第○條】。"""

BINDING_CHECK_PROMPT = """請分析以下規格書內容，檢測是否有綁標或限制性條款。

## 審查依據
{knowledge_context}

## 檢測項目
請依據上述法規與規章，逐項檢查：

| 檢測項目 | 說明 |
|---------|------|
| 品牌指定 | 是否指定特定品牌而未加「或同等品」 |
| 獨家規格 | 是否有僅特定廠商才能符合的規格要求 |
| 不合理門檻 | 是否有不合理的資格條件或技術門檻 |
| 限制性條款 | 是否有限制競爭的條款 |

## 輸出格式
請對每個項目以表格呈現：

| 項目 | 風險等級 | 具體條款引用 | 法規依據 | 修改建議 |
|------|---------|------------|---------|---------|

最後給出綜合評估與建議。

## 規格書內容
{content}"""

REASONABILITY_PROMPT = """請分析以下規格書的合理性。

## 審查依據
{knowledge_context}

## 評估項目
請依據上述法規與規章，逐項評估：

| 評估項目 | 說明 |
|---------|------|
| 規格完整性 | 是否涵蓋所有必要的技術規格 |
| 數值合理性 | 規格數值是否在合理範圍內 |
| 一致性 | 各項規格之間是否有矛盾 |
| 可驗收性 | 規格是否可以客觀驗收 |
| 市場可行性 | 是否有足夠的產品/廠商可以符合 |

## 輸出格式
請以表格呈現各項評分：

| 評估項目 | 評分 (1-10) | 說明 | 法規依據 | 改善建議 |
|---------|------------|------|---------|---------|

最後給出總評與優先改善事項。

## 規格書內容
{content}"""

FULL_ANALYSIS_PROMPT = """請對以下規格書進行完整分析。

## 審查依據
{knowledge_context}

## 分析項目
請依據上述法規與規章，進行以下分析：

### 1. 摘要
規格書的主要內容概述

### 2. 綁標檢測
是否有綁標或限制性條款（以表格呈現）

### 3. 合理性評估
規格的合理性分析（以表格呈現各項評分 1-10）

### 4. 法規符合性
是否符合相關法規要求（逐條對照）

### 5. 風險評估
潛在的採購風險（以風險矩陣呈現）

### 6. 改善建議
具體的修改建議（依優先順序排列）

### 7. 總體評分
給出 1-100 分的總體評分與評語

每項發現都必須標註【依據：○○○ 第○條】。

## 規格書內容
{content}"""

TEMPLATE_PROMPT = """請根據以下需求產生一份規格書範本：

類別: {category}
需求描述: {description}

請產生一份完整的規格書範本，包含：
1. 品名及規格
2. 數量
3. 技術規格要求
4. 功能需求
5. 驗收標準
6. 保固及售後服務要求

請使用表格格式，並確保規格書不含綁標條款。"""

BID_NOTICE_PROMPT = """你是一位專業的政府採購投標須知填寫顧問。

## 任務
請依據下方的「規格書內容」，填寫「投標須知範本」中的各個欄位。

## 採購類別
{procurement_type}

## 填寫原則
1. 嚴格依照範本的格式和欄位結構填寫
2. 依據規格書內容推斷合理的填寫值
3. 無法從規格書推斷的欄位，標註【待確認】並給出建議值
4. 廠商資格條件應合理，不得有綁標嫌疑
5. 評選方式依規格書複雜度建議（簡單→最低標，複雜→最有利標）
6. 履約期限依規格書工作範圍合理估算

## 投標須知範本
{template_content}

## 規格書內容
{spec_content}

## 輸出格式
請直接輸出填寫完成的投標須知，保持範本原有格式。
對於 AI 填入的內容，用 **粗體** 標示。
對於需要人工確認的欄位，用 ⚠️【待確認】標示。
最後附上一段「填寫說明」，解釋各項填寫的依據。"""

COMPARE_PROMPT = """請比較以下兩份規格書的差異：

=== 規格書 A ===
{content_a}

=== 規格書 B ===
{content_b}

請分析：
1. **主要差異**: 兩份規格書的關鍵差異
2. **規格變更**: 具體的規格數值變更
3. **新增/刪除項目**: 哪些項目被新增或刪除
4. **影響評估**: 這些變更可能帶來的影響
"""


async def call_llm(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{settings.llm_api_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def get_knowledge_context(knowledge_ids: list[str] | None = None) -> str:
    """從資料庫取得知識庫內容。
    knowledge_ids=None: 用全部啟用的
    knowledge_ids=[]: 不用知識庫
    knowledge_ids=[id1, id2]: 只用指定的
    """
    from app.database import async_session
    from app.models import KnowledgeBase

    if knowledge_ids is not None and len(knowledge_ids) == 0:
        return "（未選擇知識庫，請依一般慣例進行審查）"

    async with async_session() as db:
        query = select(KnowledgeBase).order_by(KnowledgeBase.category)
        if knowledge_ids is not None:
            query = query.where(KnowledgeBase.id.in_(knowledge_ids))
        else:
            query = query.where(KnowledgeBase.enabled == True)
        result = await db.execute(query)
        items = result.scalars().all()

    if not items:
        return "（尚無知識庫資料，請依一般採購法規與慣例進行審查）"

    parts = []
    for item in items:
        truncated = item.content[:2000]
        if len(item.content) > 2000:
            truncated += "\n...（以下省略）"
        parts.append(f"### 【{item.name}】（{item.source}）\n{truncated}")

    return "\n\n".join(parts)


async def analyze_binding(content: str, knowledge_ids: list[str] | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids)
    return await call_llm(BINDING_CHECK_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_reasonability(content: str, knowledge_ids: list[str] | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids)
    return await call_llm(REASONABILITY_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_full(content: str, knowledge_ids: list[str] | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids)
    return await call_llm(FULL_ANALYSIS_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def generate_template(category: str, description: str) -> str:
    return await call_llm(TEMPLATE_PROMPT.format(category=category, description=description))


async def compare_documents(content_a: str, content_b: str) -> str:
    return await call_llm(COMPARE_PROMPT.format(
        content_a=content_a[:4000],
        content_b=content_b[:4000],
    ))


async def generate_bid_notice(spec_content: str, template_content: str, procurement_type: str) -> str:
    return await call_llm(BID_NOTICE_PROMPT.format(
        procurement_type=procurement_type,
        template_content=template_content[:6000],
        spec_content=spec_content[:6000],
    ))
