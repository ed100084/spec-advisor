"""LLM 服務 - 透過 CLIProxyAPI 接各 LLM"""
import httpx

from app.config import settings

SYSTEM_PROMPT = """你是一位專業的採購規格書審查顧問。你的任務是分析規格書內容，找出潛在問題並提供改善建議。
請以繁體中文回覆，使用結構化的格式。"""

BINDING_CHECK_PROMPT = """請分析以下規格書內容，檢測是否有綁標或限制性條款：

1. **品牌指定**: 是否指定特定品牌而未加「或同等品」
2. **獨家規格**: 是否有僅特定廠商才能符合的規格要求
3. **不合理門檻**: 是否有不合理的資格條件或技術門檻
4. **限制性條款**: 是否有限制競爭的條款

請對每個項目給出：
- 風險等級 (高/中/低/無)
- 具體條款引用
- 修改建議

規格書內容：
{content}"""

REASONABILITY_PROMPT = """請分析以下規格書的合理性：

1. **規格完整性**: 是否涵蓋所有必要的技術規格
2. **數值合理性**: 規格數值是否在合理範圍內
3. **一致性**: 各項規格之間是否有矛盾
4. **可驗收性**: 規格是否可以客觀驗收
5. **市場可行性**: 是否有足夠的產品/廠商可以符合

請對每個項目給出評分 (1-10) 和具體說明。

規格書內容：
{content}"""

FULL_ANALYSIS_PROMPT = """請對以下規格書進行完整分析，包含：

1. **摘要**: 規格書的主要內容概述
2. **綁標檢測**: 是否有綁標或限制性條款
3. **合理性評估**: 規格的合理性分析
4. **風險評估**: 潛在的採購風險
5. **改善建議**: 具體的修改建議
6. **總體評分**: 1-100 分

規格書內容：
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


async def analyze_binding(content: str) -> str:
    return await call_llm(BINDING_CHECK_PROMPT.format(content=content[:8000]))


async def analyze_reasonability(content: str) -> str:
    return await call_llm(REASONABILITY_PROMPT.format(content=content[:8000]))


async def analyze_full(content: str) -> str:
    return await call_llm(FULL_ANALYSIS_PROMPT.format(content=content[:8000]))


async def generate_template(category: str, description: str) -> str:
    return await call_llm(TEMPLATE_PROMPT.format(category=category, description=description))


async def compare_documents(content_a: str, content_b: str) -> str:
    return await call_llm(COMPARE_PROMPT.format(
        content_a=content_a[:4000],
        content_b=content_b[:4000],
    ))
