import { useState, useEffect } from 'react'
import { BookOpen, Upload, Plus, Trash2, ToggleLeft, ToggleRight, Eye } from 'lucide-react'
import {
  getKnowledgeList, createKnowledge, uploadKnowledge,
  deleteKnowledge, updateKnowledge, getKnowledge,
} from '../api'
import MarkdownView from '../components/MarkdownView'

const categories = [
  { value: 'law', label: '政府法規', color: 'bg-blue-100 text-blue-800' },
  { value: 'internal_rule', label: '院內規章', color: 'bg-green-100 text-green-800' },
  { value: 'standard', label: '產業標準', color: 'bg-purple-100 text-purple-800' },
  { value: 'custom', label: '自訂規則', color: 'bg-orange-100 text-orange-800' },
]

const categoryColor = Object.fromEntries(categories.map((c) => [c.value, c.color]))

export default function KnowledgePage() {
  const [items, setItems] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [viewItem, setViewItem] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [form, setForm] = useState({ name: '', category: 'law', source: '', content: '' })

  const load = async () => {
    const { data } = await getKnowledgeList()
    setItems(data)
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    await createKnowledge(form)
    setForm({ name: '', category: 'law', source: '', content: '' })
    setShowAdd(false)
    await load()
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    const formEl = e.currentTarget
    const fd = new FormData(formEl)
    setUploading(true)
    try {
      await uploadKnowledge(fd)
      setShowUpload(false)
      formEl.reset()
      await load()
    } catch (err) {
      alert(`上傳失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
      setUploading(false)
    }
  }

  const handleToggle = async (item) => {
    await updateKnowledge(item.id, { enabled: !item.enabled })
    await load()
  }

  const handleDelete = async (item) => {
    if (!confirm(`確定要刪除「${item.name}」？`)) return
    await deleteKnowledge(item.id)
    await load()
  }

  const handleView = async (item) => {
    const { data } = await getKnowledge(item.id)
    setViewItem(data)
  }

  // Group by category
  const grouped = categories.map((cat) => ({
    ...cat,
    items: items.filter((i) => i.category === cat.value),
  }))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">知識庫管理</h2>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowUpload(false); setShowAdd(!showAdd) }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus size={16} /> 手動新增
          </button>
          <button
            onClick={() => { setShowAdd(false); setShowUpload(!showUpload) }}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
          >
            <Upload size={16} /> 上傳文件
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-500 mb-6">
        AI 分析時會自動引用已啟用的知識庫內容作為審查依據。可上傳法規、院內規章、產業標準等文件。
      </p>

      {/* Manual Add Form */}
      {showAdd && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h3 className="font-semibold mb-4">手動新增知識</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="名稱（如：政府採購法）"
              className="border rounded-lg px-3 py-2"
              required
            />
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="border rounded-lg px-3 py-2"
            >
              {categories.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <input
              value={form.source}
              onChange={(e) => setForm({ ...form, source: e.target.value })}
              placeholder="來源（如：全國法規資料庫）"
              className="border rounded-lg px-3 py-2"
            />
          </div>
          <textarea
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            placeholder="貼上法規或規章內容..."
            className="w-full border rounded-lg px-3 py-2 mb-4 resize-none"
            rows={8}
            required
          />
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            儲存
          </button>
        </form>
      )}

      {/* Upload Form */}
      {showUpload && (
        <form onSubmit={handleUpload} className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h3 className="font-semibold mb-4">上傳文件為知識庫</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <input name="name" placeholder="名稱" className="border rounded-lg px-3 py-2" required />
            <select name="category" className="border rounded-lg px-3 py-2">
              {categories.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <input name="source" placeholder="來源說明" className="border rounded-lg px-3 py-2" />
          </div>
          <input name="file" type="file" accept=".md,.markdown,.txt,.pdf,.docx,.xlsx,.xls" className="mb-4" required />
          <br />
          <button type="submit" disabled={uploading} className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50">
            {uploading ? '上傳解析中...' : '上傳並解析'}
          </button>
        </form>
      )}

      {/* Knowledge List by Category */}
      {grouped.map((group) => (
        <div key={group.value} className="mb-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase mb-3 flex items-center gap-2">
            <BookOpen size={16} />
            {group.label}
            <span className="text-xs font-normal">({group.items.length})</span>
          </h3>
          {group.items.length === 0 ? (
            <p className="text-gray-400 text-sm ml-6">尚無項目</p>
          ) : (
            <div className="space-y-2">
              {group.items.map((item) => (
                <div key={item.id} className="bg-white rounded-lg shadow-sm px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColor[item.category]}`}>
                      {item.category_label}
                    </span>
                    <span className="font-medium">{item.name}</span>
                    {item.source && <span className="text-xs text-gray-400">({item.source})</span>}
                    <span className="text-xs text-gray-400">{(item.content_length / 1000).toFixed(1)}K 字</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => handleView(item)} className="text-gray-400 hover:text-blue-600 p-1" title="檢視">
                      <Eye size={16} />
                    </button>
                    <button onClick={() => handleToggle(item)} className={`p-1 ${item.enabled ? 'text-green-600' : 'text-gray-400'}`} title={item.enabled ? '已啟用' : '已停用'}>
                      {item.enabled ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                    </button>
                    <button onClick={() => handleDelete(item)} className="text-gray-400 hover:text-red-600 p-1" title="刪除">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {/* View Modal */}
      {viewItem && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setViewItem(null)}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[80vh] overflow-auto p-6 m-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">{viewItem.name}</h3>
              <button onClick={() => setViewItem(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="text-sm text-gray-500 mb-4">
              {viewItem.category_label} · {viewItem.source}
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-sm whitespace-pre-wrap max-h-[60vh] overflow-auto">
              {viewItem.content}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
