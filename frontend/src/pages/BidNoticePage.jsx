import { useState, useEffect } from 'react'
import { Upload, Trash2, FileCheck, Loader2, Clock } from 'lucide-react'
import {
  getDocuments, getBidTemplates, uploadBidTemplate,
  deleteBidTemplate, generateBidNotice, getBidHistory,
} from '../api'
import MarkdownView from '../components/MarkdownView'

const procurementTypes = [
  { value: 'goods', label: '財物' },
  { value: 'services', label: '勞務' },
  { value: 'engineering', label: '工程' },
]

export default function BidNoticePage() {
  const [docs, setDocs] = useState([])
  const [templates, setTemplates] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [selectedTmpl, setSelectedTmpl] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    getDocuments().then(({ data }) => setDocs(data))
    getBidTemplates().then(({ data }) => setTemplates(data))
  }, [])

  const handleUpload = async (e) => {
    e.preventDefault()
    const formEl = e.currentTarget
    const fd = new FormData(formEl)
    try {
      await uploadBidTemplate(fd)
      const { data } = await getBidTemplates()
      setTemplates(data)
      setShowUpload(false)
      formEl.reset()
    } catch (err) {
      alert(`上傳失敗: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleDelete = async (id, name) => {
    if (!confirm(`確定要刪除範本「${name}」？`)) return
    await deleteBidTemplate(id)
    const { data } = await getBidTemplates()
    setTemplates(data)
  }

  const handleGenerate = async () => {
    if (!selectedDoc || !selectedTmpl) return alert('請選擇規格書和投標須知範本')
    setLoading(true)
    setResult(null)
    try {
      const { data } = await generateBidNotice(selectedDoc, selectedTmpl)
      setResult(data)
    } catch (err) {
      alert(`產生失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleShowHistory = async () => {
    const { data } = await getBidHistory()
    setHistory(data)
    setShowHistory(!showHistory)
  }

  return (
    <div>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between md:mb-6">
        <h2 className="text-xl font-bold md:text-2xl">投標須知產生</h2>
        <div className="grid grid-cols-2 gap-2 sm:flex">
          <button
            type="button"
            onClick={() => setShowUpload(!showUpload)}
            className="flex min-h-11 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-700 sm:px-4"
            aria-expanded={showUpload}
          >
            <Upload size={16} /> 上傳範本
          </button>
          <button
            type="button"
            onClick={handleShowHistory}
            className="flex min-h-11 items-center justify-center gap-2 rounded-lg bg-gray-600 px-3 py-2 text-sm text-white hover:bg-gray-700 sm:px-4"
            aria-expanded={showHistory}
          >
            <Clock size={16} /> 歷史記錄
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-500 mb-6">
        上傳投標須知範本 → 選擇規格書 → AI 依據規格書內容自動填寫投標須知
      </p>

      {/* Upload Template */}
      {showUpload && (
        <form onSubmit={handleUpload} className="mb-6 rounded-xl bg-white p-4 shadow-sm md:p-6">
          <h3 className="font-semibold mb-4">上傳投標須知範本</h3>
          <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3 md:gap-4">
            <input name="name" placeholder="範本名稱（如：財物採購投標須知）" className="border rounded-lg px-3 py-2" required />
            <select name="procurement_type" className="border rounded-lg px-3 py-2" required>
              {procurementTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input name="file" type="file" accept=".pdf,.docx,.xlsx,.xls,.txt" className="min-w-0 text-sm" required />
          </div>
          <button type="submit" className="min-h-11 w-full rounded-lg bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700 sm:w-auto">
            上傳
          </button>
        </form>
      )}

      {/* Template List */}
      {templates.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
          <h3 className="font-semibold mb-3 text-sm text-gray-500">已上傳的範本</h3>
          <div className="flex flex-wrap gap-2">
            {templates.map((t) => (
              <div key={t.id} className="flex min-w-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm">
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                  {t.procurement_type_label}
                </span>
                <span className="min-w-0 break-words">{t.name}</span>
                <button type="button" onClick={() => handleDelete(t.id, t.name)} className="tap-target -my-2 ml-1 inline-flex shrink-0 items-center justify-center rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600" aria-label={`刪除 ${t.name}`}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate */}
      <div className="mb-6 rounded-xl bg-white p-4 shadow-sm md:p-6">
        <h3 className="font-semibold mb-4">產生投標須知</h3>
        <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">選擇規格書</label>
            <select value={selectedDoc} onChange={(e) => setSelectedDoc(e.target.value)} className="w-full border rounded-lg px-3 py-2">
              <option value="">-- 請選擇規格書 --</option>
              {docs.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">選擇投標須知範本</label>
            <select value={selectedTmpl} onChange={(e) => setSelectedTmpl(e.target.value)} className="w-full border rounded-lg px-3 py-2">
              <option value="">-- 請選擇範本 --</option>
              {templates.map((t) => <option key={t.id} value={t.id}>[{t.procurement_type_label}] {t.name}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading || !selectedDoc || !selectedTmpl}
          className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 sm:w-auto"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <FileCheck size={16} />}
          AI 填寫投標須知
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="mb-6 rounded-xl bg-white p-4 shadow-sm md:p-6">
          <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="text-lg font-semibold">產生結果</h3>
            <div className="break-words text-sm text-gray-400">
              規格書: {result.document} · 範本: {result.template}
            </div>
          </div>
          <MarkdownView>{result.result}</MarkdownView>
        </div>
      )}

      {/* History */}
      {showHistory && history.length > 0 && (
        <div className="rounded-xl bg-white p-4 shadow-sm md:p-6">
          <h3 className="font-semibold mb-4">歷史記錄</h3>
          <div className="space-y-3">
            {history.map((h) => (
              <button
                type="button"
                key={h.id}
                className="w-full rounded-lg border p-3 text-left hover:bg-gray-50"
                onClick={() => setResult(h)}
              >
                <div className="flex flex-col gap-1 text-sm sm:flex-row sm:justify-between">
                  <span className="break-words">{h.document} → {h.template}</span>
                  <span className="text-gray-400">{new Date(h.created_at).toLocaleString('zh-TW')}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
