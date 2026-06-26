# Spec Advisor - 規格書檢視與建議系統

## 功能
- 📄 上傳規格書 (PDF/Word/Excel)
- 🤖 AI 分析規格書內容
- 🔍 綁標/限制性條款檢測
- 💡 規格合理性建議
- 📊 歷史規格書比對
- 👥 多人協作審閱
- 📝 規格書範本產生

## 架構
- **Frontend**: React + Vite + TailwindCSS
- **Backend**: Python FastAPI
- **Database**: SQLite
- **AI**: 透過 CLIProxyAPI 接各 LLM
- **部署**: Docker Compose (樹莓派)

## 開發

```bash
# 啟動開發環境
docker compose up -d

# 僅啟動 backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 僅啟動 frontend
cd frontend && npm install && npm run dev
```

## 部署 (樹莓派)

```bash
docker compose -f docker-compose.yml up -d --build
```
