"""LLM 服務 - 透過 CLIProxyAPI 接各 LLM"""
import json
import re

import httpx
from sqlalchemy import select

from app.config import settings

SYSTEM_PROMPT = """你是一位專業的採購規格書審查顧問。你的任務是分析規格書內容，依據相關法規與規章找出潛在問題並提供改善建議。
請以繁體中文回覆，使用結構化的 Markdown 格式（標題、表格、清單）。
重要：每項發現都必須引用具體的法規條文或規章依據，格式為【依據：○○○ 第○條】。"""

JSON_SYSTEM_PROMPT = """你是一位專業的採購規格書審查顧問。請只輸出有效 JSON，不要使用 Markdown code fence，不要輸出 JSON 以外的文字。"""

STRUCTURED_OUTPUT_INSTRUCTIONS = """請只輸出以下 JSON 結構：
{
    "summary": "整體摘要，繁體中文",
    "overall_score": 0,
    "findings": [
        {
            "item": "檢查項目",
            "status": "符合/部分符合/缺漏/高風險/中風險/低風險/建議",
            "evidence": "引用規格書中的具體內容或說明未提及",
            "basis": "引用法規、院內規章或知識庫依據；沒有依據時填一般審查原則",
            "suggestion": "具體改善建議"
        }
    ],
    "recommendations": ["優先改善事項"]
}
"""


def format_security_profile(document_meta: dict | None = None) -> str:
    meta = document_meta or {}
    return f"""## 資通訊系統導入分級資訊
- 是否為資通系統：{'是' if meta.get('is_information_system') else '否'}
- 組織資安責任等級：{meta.get('security_responsibility_level', 'A')}
- 機密性防護需求：{meta.get('confidentiality_level', '普')}
- 完整性防護需求：{meta.get('integrity_level', '普')}
- 可用性防護需求：{meta.get('availability_level', '普')}
- 法律遵循性防護需求：{meta.get('legal_compliance_level', '普')}
- 推導後資通系統防護需求等級：{meta.get('protection_level', '普')}
- 系統重要性 / 判斷原因：{meta.get('system_importance', '未填寫')}
- 是否處理個人資料：{'是' if meta.get('processes_personal_data') else '否'}
- 個資處理說明：{meta.get('personal_data_description', '未填寫')}

法源定義：
- 《資通安全管理法》第3條第1款：資通系統係指「用以蒐集、控制、傳輸、儲存、流通、刪除資訊或對資訊為其他處理、使用或分享之系統。」
- 《個人資料保護法》第2條第1款：個人資料係指自然人之姓名、出生年月日、國民身分證統一編號、護照號碼、特徵、指紋、婚姻、家庭、教育、職業、病歷、醫療、基因、性生活、健康檢查、犯罪前科、聯絡方式、財務情況、社會活動及其他得以直接或間接方式識別該個人之資料。

判斷原則：資通系統之防護需求等級，以與該系統相關之機密性、完整性、可用性及法律遵循性構面中，任一構面之防護需求等級之最高者定之。
控制措施套用原則：若防護需求等級為「高」，應檢視「高」之控制措施，且高等級要求含「中」之所有控制措施；「中」又含「普」之所有控制措施。若為「中」，應檢視「中」及「普」控制措施；若為「普」，檢視「普」控制措施。
"""


async def get_control_measure_context(document_meta: dict | None = None) -> str:
    from app.database import async_session
    from app.models import ControlBaselineVersion, ControlMeasure

    level = (document_meta or {}).get("protection_level", "普")
    level_order = {"普": 0, "中": 1, "高": 2}
    max_rank = level_order.get(level, 0)
    included_levels = [name for name, rank in level_order.items() if rank <= max_rank]

    async with async_session() as db:
        version_result = await db.execute(
            select(ControlBaselineVersion)
            .where(ControlBaselineVersion.status == "active")
            .order_by(ControlBaselineVersion.created_at.desc())
        )
        version = version_result.scalars().first()
        if not version:
            return "（尚未匯入資通系統防護基準控制措施；請先到控制措施匯入頁面上傳正式文件）"

        measure_result = await db.execute(
            select(ControlMeasure)
            .where(ControlMeasure.version_id == version.id)
            .where(ControlMeasure.level.in_(included_levels))
            .order_by(ControlMeasure.domain, ControlMeasure.item, ControlMeasure.sort_order)
        )
        measures = measure_result.scalars().all()

    if not measures:
        return f"（目前版本 {version.name} 未找到防護需求等級 {level} 對應控制措施）"

    lines = [f"使用基準版本：{version.name}", f"本次防護需求等級：{level}；應納入等級：{', '.join(included_levels)}"]
    for measure in measures[:80]:
        lines.append(f"- [{measure.level}] {measure.domain} / {measure.item}: {measure.requirement}")
    if len(measures) > 80:
        lines.append(f"...另有 {len(measures) - 80} 項控制措施未列入 prompt")
    return "\n".join(lines)

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

COST_ANALYSIS_PROMPT = """請分析以下規格書的成本合理性。

## 審查依據
{knowledge_context}

## 分析項目

| 分析項目 | 說明 |
|---------|------|
| 規格等級 | 規格是否 over-spec（超出實際需求） |
| 數量合理性 | 採購數量是否合理 |
| 預算估算 | 依市場行情估算合理預算範圍 |
| 替代方案 | 是否有更經濟的替代規格 |
| 維護成本 | 後續維護/耗材/授權的長期成本 |
| TCO 分析 | 總持有成本（Total Cost of Ownership）評估 |

## 輸出格式
請以表格呈現各項分析：

| 分析項目 | 評估結果 | 說明 | 建議 |
|---------|---------|------|------|

最後給出成本優化建議（依節省金額排序）。

## 規格書內容
{content}"""

SECURITY_CHECK_PROMPT = """請檢查以下規格書的資安合規性。

## 審查依據
{knowledge_context}

## 檢查項目

| 檢查項目 | 說明 |
|---------|------|
| 資通安全管理法 | 是否符合資通安全責任等級要求 |
| 個資保護 | 是否涉及個資處理，有無相關規範 |
| 資料落地 | 資料儲存位置是否符合規定（境內/境外） |
| 加密要求 | 傳輸與儲存加密是否有明確要求 |
| 存取控制 | 是否有身分驗證與權限管理要求 |
| 稽核日誌 | 是否要求系統操作日誌與稽核軌跡 |
| 弱點管理 | 是否要求定期弱點掃描與修補 |
| 資安認證 | 是否要求廠商具備 ISO 27001 等認證 |

## 輸出格式
請以表格呈現各項檢查結果：

| 檢查項目 | 狀態 | 現有規格描述 | 法規依據 | 改善建議 |
|---------|------|------------|---------|---------|

狀態：✅ 符合 / ⚠️ 部分符合 / ❌ 缺漏

最後給出資安合規總評與優先改善事項。

## 規格書內容
{content}"""

IMPROVEMENT_PROMPT = """請依據審查結果，產出改善後的規格書草稿。

## 審查依據
{knowledge_context}

## 任務
1. 分析原始規格書的問題（綁標、不合理、資安缺漏等）
2. 直接產出**修改後的規格書**，而非只列建議
3. 修改處用 ✏️ 標示，並在旁邊加註修改原因

## 輸出格式

### 修改摘要
以表格列出所有修改：

| 項次 | 原始內容 | 修改後內容 | 修改原因 | 法規依據 |
|------|---------|----------|---------|---------|

### 修改後規格書
（直接輸出完整的修改後規格書內容，保持原有格式）

## 原始規格書內容
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
    async with httpx.AsyncClient(timeout=600.0) as client:
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


async def call_llm_json(prompt: str) -> dict:
    text = await call_llm(prompt, system_prompt=JSON_SYSTEM_PROMPT)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise ValueError("LLM 未回傳有效 JSON")


def structured_to_markdown(data: dict) -> str:
    findings = data.get("findings") or []
    recommendations = data.get("recommendations") or []
    lines = ["## 分析摘要", str(data.get("summary") or "")]
    if data.get("overall_score") is not None:
        lines.extend(["", f"**整體評分：{data.get('overall_score')}**"])
    lines.extend([
        "",
        "## 分析結果",
        "| 項目 | 狀態 | 規格書依據 | 審查依據 | 建議 |",
        "|---|---|---|---|---|",
    ])
    for finding in findings:
        lines.append(
            "| {item} | {status} | {evidence} | {basis} | {suggestion} |".format(
                item=str(finding.get("item") or "").replace("|", "｜"),
                status=str(finding.get("status") or "").replace("|", "｜"),
                evidence=str(finding.get("evidence") or "").replace("|", "｜").replace("\n", "<br>"),
                basis=str(finding.get("basis") or "").replace("|", "｜").replace("\n", "<br>"),
                suggestion=str(finding.get("suggestion") or "").replace("|", "｜").replace("\n", "<br>"),
            )
        )
    if recommendations:
        lines.extend(["", "## 優先改善事項"])
        lines.extend(f"{index + 1}. {item}" for index, item in enumerate(recommendations))
    return "\n".join(lines)


def get_keywords_for_analysis(analysis_type: str) -> list[str]:
    keywords = {
        "binding_check": ["政府採購", "限制競爭", "綁標", "同等品", "廠牌", "資格", "規格"],
        "reasonability": ["驗收", "規格", "合理", "功能", "需求", "履約", "標準"],
        "cost": ["預算", "成本", "TCO", "維護", "授權", "耗材", "價格"],
        "security": ["資安", "資通安全", "個資", "加密", "日誌", "稽核", "權限", "備份", "弱點"],
        "improvement": ["政府採購", "限制競爭", "資安", "驗收", "履約", "規格"],
        "full": ["政府採購", "限制競爭", "資安", "驗收", "履約", "成本", "規格"],
    }
    return keywords.get(analysis_type, keywords["full"])


def extract_relevant_snippets(text: str, keywords: list[str], max_chars: int = 1800) -> str:
    if not text:
        return ""
    paragraphs = [part.strip() for part in re.split(r"\n{2,}|(?<=。)", text) if part.strip()]
    scored = []
    for paragraph in paragraphs:
        score = sum(1 for keyword in keywords if keyword.lower() in paragraph.lower())
        if score:
            scored.append((score, paragraph))
    if not scored:
        return text[:max_chars]
    scored.sort(key=lambda item: item[0], reverse=True)
    snippets = []
    current_len = 0
    for _, paragraph in scored:
        if current_len + len(paragraph) > max_chars:
            continue
        snippets.append(paragraph)
        current_len += len(paragraph)
        if current_len >= max_chars:
            break
    return "\n".join(snippets) or text[:max_chars]


async def get_knowledge_context(
    knowledge_ids: list[str] | None = None,
    analysis_type: str = "full",
) -> str:
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

    keywords = get_keywords_for_analysis(analysis_type)
    parts = []
    for item in items:
        snippet = extract_relevant_snippets(item.content, keywords)
        parts.append(f"### 【{item.name}】（{item.source}）\n{snippet}")

    return "\n\n".join(parts)


async def analyze_binding(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "binding_check")
    return await call_llm(BINDING_CHECK_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_reasonability(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "reasonability")
    return await call_llm(REASONABILITY_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_full(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "full")
    return await call_llm(FULL_ANALYSIS_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_cost(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "cost")
    return await call_llm(COST_ANALYSIS_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_security(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "security")
    security_profile = format_security_profile(document_meta)
    control_context = await get_control_measure_context(document_meta)
    sections = [
        ("個資與資料治理", "個資保護、資料落地、資料保存、資料備份，並依防護需求等級檢查對應控制措施"),
        ("存取控制與加密", "帳號管理、最小權限、身分驗證、權限控管、傳輸加密、儲存加密，並向下包含較低等級控制措施"),
        ("稽核與弱點管理", "稽核日誌、弱點掃描、修補時限、資安事件通報，並依防護需求等級檢查對應控制措施"),
    ]
    merged = {
        "summary": "資安合規分段分析彙整",
        "overall_score": None,
        "findings": [],
        "recommendations": [],
    }
    for section_name, section_scope in sections:
        prompt = f"""請針對「{section_name}」檢查規格書資安合規性。

檢查範圍：{section_scope}

{security_profile}

## 審查依據
{kb}

## 結構化控制措施
{control_context}

## 規格書內容
{content[:6000]}

{STRUCTURED_OUTPUT_INSTRUCTIONS}
"""
        data = await call_llm_json(prompt)
        for finding in data.get("findings", []):
            finding["item"] = f"{section_name} - {finding.get('item', '')}"
            merged["findings"].append(finding)
        merged["recommendations"].extend(data.get("recommendations", []))
    if merged["findings"]:
        missing = sum(1 for item in merged["findings"] if "缺" in str(item.get("status", "")) or "❌" in str(item.get("status", "")))
        partial = sum(1 for item in merged["findings"] if "部分" in str(item.get("status", "")) or "⚠" in str(item.get("status", "")))
        merged["overall_score"] = max(0, 100 - missing * 15 - partial * 8)
    return structured_to_markdown(merged)


async def analyze_improvement(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "improvement")
    return await call_llm(IMPROVEMENT_PROMPT.format(
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
