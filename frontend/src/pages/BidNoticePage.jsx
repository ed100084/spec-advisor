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
    const fd = new FormData(e.target)
    try {
      await uploadBidTemplate(fd)
      const { data } = await getBidTemplates()
      setTemplates(data)
      setShowUpload(false)
      e.target.reset()
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
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">投標須知產生</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
          >
            <Upload size={16} /> 上傳範本
          </button>
          <button
            onClick={handleShowHistory}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
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
        <form onSubmit={handleUpload} className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h3 className="font-semibold mb-4">上傳投標須知範本</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <input name="name" placeholder="範本名稱（如：財物採購投標須知）" className="border rounded-lg px-3 py-2" required />
            <select name="procurement_type" className="border rounded-lg px-3 py-2" required>
              {procurementTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input name="file" type="file" accept=".pdf,.docx,.xlsx,.xls,.txt" required />
          </div>
          <button type="submit" className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">
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
              <div key={t.id} className="flex items-center gap-2 border rounded-lg px-3 py-2 text-sm">
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                  {t.procurement_type_label}
                </span>
                <span>{t.name}</span>
                <button onClick={() => handleDelete(t.id, t.name)} className="text-red-400 hover:text-red-600 ml-1">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h3 className="font-semibold mb-4">產生投標須知</h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
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
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <FileCheck size={16} />}
          AI 填寫投標須知
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">產生結果</h3>
            <div className="text-sm text-gray-400">
              規格書: {result.document} · 範本: {result.template}
            </div>
          </div>
          <MarkdownView>{result.result}</MarkdownView>
        </div>
      )}

      {/* History */}
      {showHistory && history.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-semibold mb-4">歷史記錄</h3>
          <div className="space-y-3">
            {history.map((h) => (
              <div
                key={h.id}
                className="border rounded-lg p-3 cursor-pointer hover:bg-gray-50"
                onClick={() => setResult(h)}
              >
                <div className="flex justify-between text-sm">
                  <span>{h.document} → {h.template}</span>
                  <span className="text-gray-400">{new Date(h.created_at).toLocaleString('zh-TW')}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
