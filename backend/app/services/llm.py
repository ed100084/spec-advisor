"""LLM 服務 - 透過 CLIProxyAPI 接各 LLM"""
import json
import logging
import re

import httpx
from sqlalchemy import select

from app.config import settings

SYSTEM_PROMPT = """你是一位專業的採購規格書審查顧問。你的任務是分析規格書內容，依據相關法規與規章找出潛在問題並提供改善建議。
請以繁體中文回覆，使用結構化的 Markdown 格式（標題、表格、清單）。
重要規則：
1. 每項發現的法規依據，必須且只能來自下方「審查依據」章節中提供的知識庫內容，格式為【依據：○○○ 第○條】。
2. 若審查依據中未包含相關法規，請標註【依據：一般審查原則】，絕對不得自行引用未提供的法規條文。
3. 不可從你的訓練資料中自行補充法規（例如政府採購法、醫療器材管理法等），除非該法規明確出現在審查依據中。"""

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
- 是否套用資通系統導入分級：{'是' if meta.get('applies_system_introduction_grading', True) else '否'}
- 是否為關鍵基礎設施：{'是' if meta.get('is_critical_infrastructure') else '否'}
- 機關類型：{meta.get('organization_category', '特定非公務機關')}
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

### 5. 個資保護影響
若規格書涉及個人資料之蒐集、處理或利用，請評估：資料蒐集目的限制、保存期限、去識別化要求、當事人權利機制、跨境傳輸、資安事件通報。若無個資相關內容，請標註「本規格書不涉及個人資料處理，免評估」。

### 6. 服務水準評估
若規格書含有 SLA 或服務承諾，請評估：可用性承諾（99.x%）、回應/修復時間、效能指標、罰則補償、維護窗口、升級流程、報告機制。若無 SLA 條款，請標註「本規格書未包含 SLA 條款，建議補充」。

### 7. 供應商鎖定風險
評估：資料可攜性、開放標準使用情況、合約到期後移轉條款、第三方整合能力、替換成本、原始碼/設定檔交付、技術文件完整性（以表格呈現風險等級）。

### 8. 風險評估
潛在的採購風險（以風險矩陣呈現）

### 9. 改善建議
具體的修改建議（依優先順序排列）

### 10. 總體評分
給出 1-100 分的總體評分與評語

### 11. 醫療資訊互通性
評估 HL7 FHIR/V2 支援、DICOM 相容性、IHE Integration Profile 遵循、HIS/PACS/LIS/RIS 整合介面規格、標準代碼系統採用（ICD-10/LOINC/SNOMED CT）、電子病歷及健保資料交換規範（以表格呈現）。若非醫療系統，請標註「本規格書非醫療系統，免評估」。

### 12. ISMS 合規
評估是否符合 ISO 27001:2022 Annex A 控制框架：組織控制（政策/角色/供應商安全）、人員控制（篩選/訓練）、實體控制（機房/設備）、技術控制框架（SDL/弱點管理/SBOM）、是否要求 ISO 27001 認證、SoA 及稽核配合義務（以表格呈現）。

### 13. 營運持續/災難復原
評估 BCP/DR 相關要求：RPO/RTO/MTPD 定義是否明確合理、備援架構類型（Active-Active/Standby）、資料庫/應用/網路備援機制、備份策略（類型/頻率/保留期/加密）、異地備份、備份驗證測試、DRP 文件、DR 演練義務、廠商 BCP 能力（ISO 22301）、原始碼託管與退場條款（以表格呈現）。

每項發現都必須標註【依據：○○○ 第○條】。
僅引用知識庫中提供的法規條文，使用【依據：○○○ 第○條】格式，未提供的法規不得引用。

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

INTELLECTUAL_PROPERTY_PROMPT = """請檢查以下規格書的智財權與授權風險。

## 審查依據
{knowledge_context}

## 檢查項目

| 檢查項目 | 說明 |
|---------|------|
| 智財權歸屬 | 客製成果、文件、程式、報表、介面、資料模型、訓練成果或設定檔之權利歸屬是否清楚 |
| 授權範圍 | 使用者數、裝置數、院區數、併發數、CPU/Core、VM、Container、測試/備援/災復環境是否明確 |
| 授權期間 | 永久授權、訂閱、維護期、升級權、展延條件與終止後使用權是否明確 |
| 第三方與開源元件 | 是否要求揭露第三方元件、Open Source 授權、授權相容性與安全更新責任 |
| 維護與移轉 | 是否限制只能由原廠或特定廠商維護，或限制轉移、整合、接續維護 |
| 資料權利與退場 | 資料所有權、資料可攜性、匯出格式、刪除、返還、終止後轉移與協助義務是否明確 |
| 授權稽核與罰則 | 稽核權、補授權、違約金、停權、中止服務條款是否合理且不影響醫療營運 |
| 採購公平性 | 授權或智財條款是否造成限制競爭、指定廠商、排除同等品或不合理續約依賴 |

## 輸出格式
請以表格呈現各項檢查結果：

| 檢查項目 | 風險等級 | 現有規格描述 | 審查依據 | 改善建議 |
|---------|---------|------------|---------|---------|

風險等級：高 / 中 / 低 / 未提及 / 可接受

最後請提供：
1. 智財權與授權總評
2. 建議補強條款（可直接放入規格書或契約）
3. 需請法務或採購確認的事項

## 規格書內容
{content}"""

PIA_PROMPT = """請對以下規格書進行個資保護影響評估（Privacy Impact Assessment）。

## 審查依據
{knowledge_context}

## 檢查項目
請依據上述法規與規章，逐項檢查：

| 檢查項目 | 說明 |
|---------|------|
| 資料蒐集範圍與目的限制 | 是否明確界定蒐集的個資類型與特定目的 |
| 保存期限與銷毀機制 | 是否訂有保存年限及到期銷毀或去識別化的程序 |
| 跨境傳輸條款 | 資料是否跨境，是否符合境外傳輸規定 |
| 去識別化/匿名化處理 | 非必要使用時是否要求去識別化或匿名化 |
| 當事人權利行使機制 | 是否提供查詢、更正、刪除、停止處理等機制 |
| 資料處理者角色定義 | 委外廠商的個資處理角色與責任是否明確 |
| 資安事件通報流程 | 個資外洩或資安事件的通報時限與程序是否規定 |

## 輸出格式
請以表格呈現各項評估結果：

| 檢查項目 | 風險等級 | 現有規格描述 | 審查依據 | 改善建議 |
|---------|---------|------------|---------|---------|

風險等級：高 / 中 / 低 / 未提及 / 可接受

最後給出個資保護影響總評與優先補強事項。

僅引用知識庫中提供的法規條文，使用【依據：○○○ 第○條】格式，未提供的法規不得引用。

## 規格書內容
{content}"""

SLA_PROMPT = """請對以下規格書進行服務水準分析（Service Level Agreement Analysis）。

## 審查依據
{knowledge_context}

## 檢查項目
請依據上述法規與規章，逐項檢查：

| 檢查項目 | 說明 |
|---------|------|
| 系統可用性承諾 | 是否有 99.x% 可用性承諾及計算方式 |
| 回應/修復時間 | 是否明訂 MTTR（平均修復時間）與 MTBF（平均故障間隔） |
| 效能指標 | 回應速度、吞吐量、並發數等效能基準是否量化 |
| 罰則/補償機制 | 未達 SLA 時的懲罰條款、服務費扣減或補償方式 |
| 維護窗口與排除條件 | 計畫性維護時段及不計入 SLA 的排除條件是否合理 |
| 升級（Escalation）流程 | 問題升級的觸發條件、層級與時限是否明確 |
| 報告/監控機制 | 服務可用性報告頻率、監控方式與數據提供義務 |

## 輸出格式
請以表格呈現各項評估結果：

| 檢查項目 | 評估狀態 | 現有規格描述 | 審查依據 | 改善建議 |
|---------|---------|------------|---------|---------|

評估狀態：✅ 完整 / ⚠️ 部分 / ❌ 缺漏 / 📌 建議補充

最後給出 SLA 完整性總評與建議補充的條款文字。

僅引用知識庫中提供的法規條文，使用【依據：○○○ 第○條】格式，未提供的法規不得引用。

## 規格書內容
{content}"""

VENDOR_LOCKIN_PROMPT = """請對以下規格書進行供應商鎖定風險評估（Vendor Lock-in Risk Assessment）。

## 審查依據
{knowledge_context}

## 檢查項目
請依據上述法規與規章，逐項檢查：

| 檢查項目 | 說明 |
|---------|------|
| 資料可攜性 | 是否規定資料匯出格式（如 CSV/JSON/XML 等開放格式）及 API 介面 |
| 開放標準 vs 專有協定 | 系統介面、資料格式是否採用開放標準或依賴專有協定 |
| 合約到期後資料移轉條款 | 合約終止時資料返還、移轉協助與時限是否明確 |
| 第三方整合能力 | 是否支援與其他系統整合，是否有排他性整合限制 |
| 替換成本評估 | 技術、資料、人員重新培訓的替換成本是否有評估依據 |
| 原始碼/設定檔交付 | 客製化開發成果的原始碼、設定檔、部署文件是否要求交付 |
| 技術文件完整性 | 系統架構、API 文件、操作手冊是否要求完整交付 |

## 輸出格式
請以表格呈現各項風險評估：

| 檢查項目 | 鎖定風險 | 現有規格描述 | 審查依據 | 改善建議 |
|---------|---------|------------|---------|---------|

鎖定風險：高 / 中 / 低 / 未提及 / 可接受

最後給出供應商鎖定風險總評，並列出建議加入的退場（Exit）條款。

僅引用知識庫中提供的法規條文，使用【依據：○○○ 第○條】格式，未提供的法規不得引用。

## 規格書內容
{content}"""

INTEROPERABILITY_PROMPT = """請對以下規格書進行醫療資訊互通性分析。

## 審查依據
{knowledge_context}

## 檢查項目
請依據上述法規與規章，逐項檢查：

| 檢查項目 | 說明 |
|---------|------|
| HL7 FHIR/V2 支援 | 是否要求支援 FHIR R4 以上版本或 HL7 V2.x 訊息，是否遵循 TW Core IG |
| DICOM 相容性 | 影像系統是否要求 DICOM 3.0 標準，是否支援 DICOMweb（WADO-RS/STOW-RS/QIDO-RS）|
| IHE Integration Profile | 是否遵循 IHE PIX/PDQ/XDS/MHD/ATNA 等 Profile，跨系統病人識別與資料分享 |
| HIS/PACS/LIS/RIS 整合 | 系統整合介面是否有明確規格，HL7 訊息類型與 API 是否有說明 |
| 標準代碼系統 | 是否採用 ICD-10-CM/PCS、LOINC、SNOMED CT、ATC、健保代碼等標準 |
| 電子病歷交換 | 是否符合衛福部電子病歷製作及管理辦法，是否支援 CDA R2 或 FHIR Document |
| 健保資料交換 | 是否符合健保署規定之資料格式，是否支援健保雲端藥歷、健康存摺 |

## 輸出格式
請以表格呈現各項評估結果：

| 檢查項目 | 評估狀態 | 現有規格描述 | 審查依據 | 改善建議 |
|---------|---------|------------|---------|---------|

評估狀態：✅ 符合 / ⚠️ 部分符合 / ❌ 缺漏 / 📌 不適用

最後給出醫療資訊互通性總評，並列出建議補充的標準互通性條款。

僅引用知識庫中提供的法規條文，使用【依據：○○○ 第○條】格式，未提供的法規不得引用。

## 規格書內容
{content}"""

ISMS_PROMPT = """請對以下規格書進行 ISMS（資訊安全管理系統）合規分析，依照 ISO 27001:2022 Annex A 控制措施框架進行評估。

注意：本分析聚焦於管理制度面（政策、程序、組織、稽核、認證），不重複技術控制措施之細節（加密/存取控制等技術面已由資安合規分析涵蓋）。

## 審查依據
{knowledge_context}

## 檢查項目
請依據上述法規與規章，逐項檢查：

| 檢查項目 | 說明 |
|---------|------|
| 組織控制（A.5） | 資訊安全政策、角色責任、職責分離、威脅情資、供應商關係安全管理是否要求 |
| 人員控制（A.6） | 人員篩選查核、資安認知教育訓練是否有要求 |
| 實體控制（A.7） | 機房/設備實體安全、環境監控、設備報廢資料銷毀要求是否明確 |
| 技術控制框架（A.8） | 是否要求廠商建立安全開發生命週期（SDL）、弱點管理程序、SBOM、組態管理基準 |
| ISO 27001 認證 | 是否要求廠商具備 ISO 27001 認證或等同資安管理制度驗證 |
| 適用性聲明（SoA） | 是否要求廠商提供 ISO 27001 Annex A 適用性聲明 |
| 稽核配合義務 | 是否明確要求廠商配合機關執行資安稽核（年度/專案稽核）|
| 持續改善機制 | 是否要求廠商定期審查安全控制措施，提供改善計畫 |

## 輸出格式
請以表格呈現各項評估結果：

| 檢查項目 | 風險等級 | 現有規格描述 | 審查依據 | 改善建議 |
|---------|---------|------------|---------|---------|

風險等級：高 / 中 / 低 / 未提及 / 可接受

最後給出 ISMS 合規總評，並列出建議加入之資安管理制度條款。

僅引用知識庫中提供的法規條文，使用【依據：○○○ 第○條】格式，未提供的法規不得引用。

## 規格書內容
{content}"""

BCP_DR_PROMPT = """請對以下規格書進行營運持續與災難復原分析（Business Continuity & Disaster Recovery）。

## 審查依據
{knowledge_context}

## 檢查項目
請依據上述法規與規章，逐項檢查：

| 檢查項目 | 說明 |
|---------|------|
| RPO 定義 | 是否明確訂定復原點目標（Recovery Point Objective），資料遺失容忍量 |
| RTO 定義 | 是否明確訂定復原時間目標（Recovery Time Objective），服務中斷可忍受時間 |
| MTPD 定義 | 是否訂定最大可容忍中斷時間，是否合理（應大於 RTO）|
| 備援架構 | 是否明確要求備援架構類型（Active-Active/Active-Standby/Cold Standby）及自動切換機制 |
| 資料庫備援 | 是否要求資料庫複寫、叢集或鏡像機制，同步/非同步方式是否說明 |
| 應用程式備援 | 是否要求負載平衡、Session 持久化、健康檢查機制 |
| 網路備援 | 是否要求雙線路/多 ISP 接入、核心交換器備援、防火牆 HA |
| 備份策略 | 是否說明備份類型（完整/差異/增量）、頻率、保留期限與加密要求 |
| 異地備份 | 是否要求異地備份，地理距離與傳輸安全是否明確 |
| 備份驗證 | 是否要求定期執行備份還原測試並提供測試報告 |
| 災難復原計畫（DRP） | 是否要求廠商提供 DRP 文件，含災難分級、應變程序、演練計畫 |
| DR 演練 | 是否要求每年至少一次 DR 演練，並提供演練結果報告 |
| 廠商營運持續能力 | 是否評估廠商自身 BCP（含 ISO 22301 認證或自評）、關鍵人員備援 |
| 合約保障 | 是否有原始碼託管（Escrow）、廠商退場/倒閉移轉計畫、服務中斷罰則 |

## 輸出格式
請以表格呈現各項評估結果：

| 檢查項目 | 評估狀態 | 現有規格描述 | 審查依據 | 改善建議 |
|---------|---------|------------|---------|---------|

評估狀態：✅ 完整 / ⚠️ 部分 / ❌ 缺漏 / 📌 建議補充

最後給出營運持續/災難復原總評，並列出建議補充的 BCP/DR 條款。

僅引用知識庫中提供的法規條文，使用【依據：○○○ 第○條】格式，未提供的法規不得引用。

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
請直接輸出完整的修改後規格書內容，並務必使用標準 Markdown 編排：
- 第一層章節使用 `## 1. 章節名稱`
- 第二層章節使用 `### 1.1 小節名稱`
- 第三層章節使用 `#### 1.1.1 子項名稱`
- 條列內容使用 `-` 或 Markdown 編號清單，每個條列獨立一行
- 表格使用標準 Markdown table
- 每個章節、段落、表格前後都要保留空白行
- 不要把整份規格書輸出成單一長段落
- 修改處用 `✏️` 標示，並在同一段或同一列加註修改原因

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
        "intellectual_property": ["智財", "智慧財產", "著作權", "授權", "永久", "訂閱", "開源", "第三方", "原始碼", "資料所有權", "移轉", "維護"],
        "pia": ["個資", "個人資料", "隱私", "蒐集", "處理", "利用", "去識別", "跨境", "當事人", "同意", "通報"],
        "sla": ["SLA", "可用性", "回應時間", "修復", "罰則", "維護", "保固", "服務水準", "MTTR", "MTBF", "uptime"],
        "vendor_lockin": ["專有", "獨家", "格式", "標準", "移轉", "匯出", "API", "開放", "原始碼", "文件", "交接"],
        "interoperability": ["HL7", "FHIR", "DICOM", "IHE", "HIS", "PACS", "LIS", "整合", "互通", "介面", "API", "電子病歷", "影像", "檢驗"],
        "isms": ["ISO 27001", "ISMS", "控制措施", "Annex A", "稽核", "政策", "管理制度", "認證", "合規", "安全管理", "資安管理"],
        "bcp_dr": ["RPO", "RTO", "備援", "備份", "災難", "復原", "DR", "BCP", "切換", "failover", "HA", "高可用", "營運持續", "MTPD"],
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
    query_text: str = "",
) -> str:
    from app.database import async_session
    from app.models import KnowledgeBase, KnowledgeChunk

    if knowledge_ids is not None and len(knowledge_ids) == 0:
        return "（未選擇知識庫，請依一般慣例進行審查）"

    async with async_session() as db:
        # Query selected knowledge bases
        query = select(KnowledgeBase).order_by(KnowledgeBase.category)
        if knowledge_ids is not None:
            query = query.where(KnowledgeBase.id.in_(knowledge_ids))
        else:
            query = query.where(KnowledgeBase.enabled == True)
        result = await db.execute(query)
        items = result.scalars().all()

    if not items:
        return "（尚無知識庫資料，請依一般採購法規與慣例進行審查）"

    kb_ids = [item.id for item in items]

    # Try embedding-based retrieval first
    try:
        context = await _embedding_retrieval(kb_ids, analysis_type, query_text)
        if context:
            names = chr(12289).join(item.name for item in items)
            context += f"\n\n---\n本次可引用的法規僅限上述知識庫：{names}。請勿引用上述以外的任何法規條文。若某項發現無法對應上述法規，請填寫「一般審查原則」作為依據。"
            return context
    except Exception as e:
        logging.getLogger(__name__).warning("Embedding retrieval failed, falling back to keywords: %s", e)

    # Fallback: keyword-based extraction
    keywords = get_keywords_for_analysis(analysis_type)
    parts = []
    for item in items:
        snippet = extract_relevant_snippets(item.content, keywords)
        parts.append(f"### 【{item.name}】（{item.source}）\n{snippet}")

    context = "\n\n".join(parts)
    names = chr(12289).join(item.name for item in items)
    context += f"\n\n---\n本次可引用的法規僅限上述 {len(items)} 項：{names}。請勿引用上述以外的任何法規條文。若某項發現無法對應上述法規，請填寫「一般審查原則」作為依據。"
    return context


async def _embedding_retrieval(
    kb_ids: list[str],
    analysis_type: str,
    query_text: str,
    top_k: int = 15,
    max_chars: int = 3000,
) -> str | None:
    from app.database import async_session
    from app.models import KnowledgeBase, KnowledgeChunk
    from app.services.embedding import compute_single_embedding, cosine_similarity_search

    # Build query from analysis keywords + spec content
    keywords = get_keywords_for_analysis(analysis_type)
    search_query = " ".join(keywords)
    if query_text:
        search_query += " " + query_text[:500]

    # Get all chunks for selected knowledge bases
    async with async_session() as db:
        result = await db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.knowledge_id.in_(kb_ids))
            .where(KnowledgeChunk.embedding.isnot(None))
            .order_by(KnowledgeChunk.knowledge_id, KnowledgeChunk.chunk_index)
        )
        chunks = result.scalars().all()

    if not chunks:
        return None  # No embeddings available, use fallback

    # Compute query embedding
    query_emb = compute_single_embedding(search_query)

    # Search
    chunk_embeddings = [c.embedding for c in chunks]
    results = cosine_similarity_search(query_emb, chunk_embeddings, top_k=top_k)

    # Group results by knowledge_id and build context
    async with async_session() as db:
        kb_map = {}
        for kb_id in kb_ids:
            kb = await db.get(KnowledgeBase, kb_id)
            if kb:
                kb_map[kb_id] = kb

    parts_by_kb = {}
    total_chars = 0
    for idx, score in results:
        if score < 0.3:  # Minimum relevance threshold
            continue
        chunk = chunks[idx]
        kb = kb_map.get(chunk.knowledge_id)
        if not kb:
            continue
        if chunk.knowledge_id not in parts_by_kb:
            parts_by_kb[chunk.knowledge_id] = {
                "name": kb.name,
                "source": kb.source,
                "snippets": [],
            }
        if total_chars + len(chunk.chunk_text) > max_chars:
            continue
        parts_by_kb[chunk.knowledge_id]["snippets"].append(
            f"[相關度 {score:.0%}] {chunk.chunk_text}"
        )
        total_chars += len(chunk.chunk_text)

    if not parts_by_kb:
        return None

    output = []
    for kb_id, info in parts_by_kb.items():
        section = f"### 【{info['name']}】（{info['source']}）\n"
        section += "\n\n".join(info["snippets"])
        output.append(section)

    return "\n\n".join(output)

async def analyze_binding(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "binding_check", content[:500])
    return await call_llm(BINDING_CHECK_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_reasonability(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "reasonability", content[:500])
    return await call_llm(REASONABILITY_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_full(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "full", content[:500])
    return await call_llm(FULL_ANALYSIS_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_cost(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "cost", content[:500])
    return await call_llm(COST_ANALYSIS_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_security(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "security", content[:500])
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


async def analyze_intellectual_property(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "intellectual_property", content[:500])
    return await call_llm(INTELLECTUAL_PROPERTY_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_pia(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "pia", content[:500])
    return await call_llm(PIA_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_sla(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "sla", content[:500])
    return await call_llm(SLA_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_vendor_lockin(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "vendor_lockin", content[:500])
    return await call_llm(VENDOR_LOCKIN_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_interoperability(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "interoperability", content[:500])
    return await call_llm(INTEROPERABILITY_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_isms(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "isms", content[:500])
    return await call_llm(ISMS_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_bcp_dr(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "bcp_dr", content[:500])
    return await call_llm(BCP_DR_PROMPT.format(
        knowledge_context=kb, content=content[:8000]
    ))


async def analyze_improvement(content: str, knowledge_ids: list[str] | None = None, document_meta: dict | None = None) -> str:
    kb = await get_knowledge_context(knowledge_ids, "improvement", content[:500])
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
