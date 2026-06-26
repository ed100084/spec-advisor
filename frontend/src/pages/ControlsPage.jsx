import { useEffect, useState } from 'react'
import { Check, Database, Edit3, Plus, Trash2, Upload, RefreshCcw, X } from 'lucide-react'
import { createControlMeasure, deleteControlMeasure, deleteControlVersion, getControlMeasures, getControlVersions, importControlBaseline, updateControlMeasure } from '../api'

const levels = ['', '普', '中', '高']

export default function ControlsPage() {
  const [versions, setVersions] = useState([])
  const [measures, setMeasures] = useState([])
  const [selectedVersion, setSelectedVersion] = useState('')
  const [selectedLevel, setSelectedLevel] = useState('')
  const [uploading, setUploading] = useState(false)
  const [editingId, setEditingId] = useState('')
  const [editForm, setEditForm] = useState({})
  const [newMeasure, setNewMeasure] = useState({ domain: '', item: '', level: '普', requirement: '', source_text: '' })

  const loadVersions = async () => {
    const { data } = await getControlVersions()
    setVersions(data)
    if (!selectedVersion && data.length > 0) setSelectedVersion(data[0].id)
  }

  const loadMeasures = async () => {
    const params = {}
    if (selectedVersion) params.version_id = selectedVersion
    if (selectedLevel) params.level = selectedLevel
    const { data } = await getControlMeasures(params)
    setMeasures(data)
  }

  useEffect(() => { loadVersions() }, [])
  useEffect(() => { loadMeasures() }, [selectedVersion, selectedLevel])

  const handleUpload = async (e) => {
    e.preventDefault()
    const formEl = e.currentTarget
    setUploading(true)
    try {
      const form = new FormData(formEl)
      const { data } = await importControlBaseline(form)
      const warnings = data.warnings?.length ? `\n\n提醒：\n${data.warnings.join('\n')}` : ''
      alert(`匯入完成，共 ${data.imported_count} 項控制措施${warnings}`)
      formEl.reset()
      await loadVersions()
      setSelectedVersion(data.version_id)
    } catch (err) {
      alert(`匯入失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteVersion = async (version) => {
    if (!confirm(`確定刪除「${version.name}」及其所有控制措施？`)) return
    await deleteControlVersion(version.id)
    setSelectedVersion('')
    await loadVersions()
    await loadMeasures()
  }

  const handleCreateMeasure = async (e) => {
    e.preventDefault()
    if (!selectedVersion) return alert('請先選擇要新增到哪個基準版本')
    if (!newMeasure.requirement.trim()) return alert('請填寫要求')
    await createControlMeasure({ ...newMeasure, version_id: selectedVersion })
    setNewMeasure({ domain: '', item: '', level: '普', requirement: '', source_text: '' })
    await loadVersions()
    await loadMeasures()
  }

  const startEdit = (measure) => {
    setEditingId(measure.id)
    setEditForm({
      domain: measure.domain,
      item: measure.item,
      level: measure.level,
      requirement: measure.requirement,
      source_text: measure.source_text || '',
    })
  }

  const saveEdit = async (measureId) => {
    await updateControlMeasure(measureId, editForm)
    setEditingId('')
    await loadVersions()
    await loadMeasures()
  }

  const handleDeleteMeasure = async (measure) => {
    if (!confirm(`確定刪除「${measure.domain} / ${measure.item} / ${measure.level}」？`)) return
    await deleteControlMeasure(measure.id)
    await loadVersions()
    await loadMeasures()
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">控制措施資料表</h2>

      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h3 className="font-semibold mb-3 flex items-center gap-2"><Upload size={16} /> 匯入資通系統防護基準</h3>
        <p className="text-sm text-gray-500 mb-4">
          上傳 PDF/Word/Excel/TXT，系統會先解析文字，再由 AI 萃取成「控制領域 / 控制項 / 等級 / 要求」資料表。未來法規更新時可匯入新版本並保留舊版本。
        </p>
        <form onSubmit={handleUpload} className="grid grid-cols-1 gap-3 md:grid-cols-5 md:items-end">
          <input name="name" placeholder="版本名稱（如：防護基準 113版）" className="min-w-0 border rounded-lg px-3 py-2" required />
          <input name="source" placeholder="來源（如：數位發展部）" className="min-w-0 border rounded-lg px-3 py-2" />
          <input name="effective_date" placeholder="生效日期" className="min-w-0 border rounded-lg px-3 py-2" />
          <input name="expected_count" type="number" min="1" placeholder="預期項數（如：81）" className="min-w-0 border rounded-lg px-3 py-2" />
          <input name="file" type="file" accept=".pdf,.docx,.xlsx,.xls,.txt" className="min-w-0 text-sm" required />
          <button disabled={uploading} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 md:col-span-5">
            {uploading ? '匯入中，請稍候...' : '開始匯入'}
          </button>
        </form>
      </div>

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center">
        <Database size={16} className="text-gray-400" />
        <select value={selectedVersion} onChange={(e) => setSelectedVersion(e.target.value)} className="min-w-0 border rounded-lg px-3 py-2 text-sm md:min-w-[260px]">
          <option value="">全部版本</option>
          {versions.map((v) => <option key={v.id} value={v.id}>{v.name}（{v.measure_count}項）</option>)}
        </select>
        <select value={selectedLevel} onChange={(e) => setSelectedLevel(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          {levels.map((l) => <option key={l || 'all'} value={l}>{l ? `防護需求 ${l}（含以下）` : '全部等級'}</option>)}
        </select>
        <button onClick={loadMeasures} className="p-2 text-gray-500 hover:text-blue-600" title="重新整理">
          <RefreshCcw size={16} />
        </button>
      </div>

      {versions.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-4 mb-4">
          <h3 className="font-semibold text-sm mb-2">版本管理</h3>
          <div className="space-y-2">
            {versions.map((v) => (
              <div key={v.id} className="flex items-center justify-between border rounded-lg px-3 py-2 text-sm">
                <span>{v.name} · {v.source || '未填來源'} · {v.measure_count} 項</span>
                <button onClick={() => handleDeleteVersion(v)} className="text-red-500 hover:text-red-700"><Trash2 size={14} /></button>
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleCreateMeasure} className="bg-white rounded-xl shadow-sm p-4 mb-4 grid grid-cols-1 gap-3 md:grid-cols-12 md:items-start">
        <div className="col-span-12 flex items-center gap-2 font-semibold text-sm"><Plus size={16} /> 新增控制措施</div>
        <input value={newMeasure.domain} onChange={(e) => setNewMeasure({ ...newMeasure, domain: e.target.value })} placeholder="領域" className="min-w-0 border rounded-lg px-3 py-2 text-sm md:col-span-2" />
        <input value={newMeasure.item} onChange={(e) => setNewMeasure({ ...newMeasure, item: e.target.value })} placeholder="控制項" className="min-w-0 border rounded-lg px-3 py-2 text-sm md:col-span-2" />
        <select value={newMeasure.level} onChange={(e) => setNewMeasure({ ...newMeasure, level: e.target.value })} className="border rounded-lg px-3 py-2 text-sm md:col-span-1">
          {['普', '中', '高'].map((level) => <option key={level} value={level}>{level}</option>)}
        </select>
        <textarea value={newMeasure.requirement} onChange={(e) => setNewMeasure({ ...newMeasure, requirement: e.target.value })} placeholder="要求" className="min-w-0 border rounded-lg px-3 py-2 text-sm min-h-[88px] md:col-span-5 md:min-h-[42px]" required />
        <button className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 md:col-span-2">新增</button>
      </form>

      <div className="space-y-3 md:hidden">
        {measures.map((m) => (
          <div key={m.id} className="rounded-xl bg-white p-4 shadow-sm">
            {editingId === m.id ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <input value={editForm.domain} onChange={(e) => setEditForm({ ...editForm, domain: e.target.value })} className="min-w-0 border rounded px-2 py-2 text-sm" placeholder="領域" />
                  <input value={editForm.item} onChange={(e) => setEditForm({ ...editForm, item: e.target.value })} className="min-w-0 border rounded px-2 py-2 text-sm" placeholder="控制項" />
                </div>
                <select value={editForm.level} onChange={(e) => setEditForm({ ...editForm, level: e.target.value })} className="w-full border rounded px-2 py-2 text-sm">
                  {['普', '中', '高'].map((level) => <option key={level} value={level}>{level}</option>)}
                </select>
                <textarea value={editForm.requirement} onChange={(e) => setEditForm({ ...editForm, requirement: e.target.value })} className="w-full border rounded px-2 py-2 text-sm min-h-[120px]" />
                <div className="flex justify-end gap-2">
                  <button type="button" onClick={() => setEditingId('')} className="px-3 py-2 text-sm text-gray-600">取消</button>
                  <button type="button" onClick={() => saveEdit(m.id)} className="px-3 py-2 text-sm bg-emerald-600 text-white rounded-lg">儲存</button>
                </div>
              </div>
            ) : (
              <>
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-xs text-gray-500 break-words">{m.domain}</div>
                    <div className="font-semibold text-gray-900 break-words">{m.item}</div>
                  </div>
                  <span className="shrink-0 px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs">{m.level}</span>
                </div>
                <p className="whitespace-pre-wrap break-words text-sm leading-6 text-gray-700">{m.requirement}</p>
                <div className="mt-3 flex justify-end gap-3 border-t pt-3">
                  <button onClick={() => startEdit(m)} className="flex items-center gap-1 text-sm text-blue-600" title="編輯"><Edit3 size={15} /> 編輯</button>
                  <button onClick={() => handleDeleteMeasure(m)} className="flex items-center gap-1 text-sm text-red-500" title="刪除"><Trash2 size={15} /> 刪除</button>
                </div>
              </>
            )}
          </div>
        ))}
        {measures.length === 0 && (
          <div className="rounded-xl bg-white px-4 py-10 text-center text-gray-400 shadow-sm">尚無控制措施資料</div>
        )}
      </div>

      <div className="hidden bg-white rounded-xl shadow-sm overflow-hidden md:block">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-4 py-3">領域</th>
              <th className="px-4 py-3">控制項</th>
              <th className="px-4 py-3">等級</th>
              <th className="px-4 py-3">要求</th>
              <th className="px-4 py-3 w-24">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {measures.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50">
                {editingId === m.id ? (
                  <>
                    <td className="px-4 py-3"><input value={editForm.domain} onChange={(e) => setEditForm({ ...editForm, domain: e.target.value })} className="w-full border rounded px-2 py-1" /></td>
                    <td className="px-4 py-3"><input value={editForm.item} onChange={(e) => setEditForm({ ...editForm, item: e.target.value })} className="w-full border rounded px-2 py-1" /></td>
                    <td className="px-4 py-3"><select value={editForm.level} onChange={(e) => setEditForm({ ...editForm, level: e.target.value })} className="border rounded px-2 py-1">{['普', '中', '高'].map((level) => <option key={level} value={level}>{level}</option>)}</select></td>
                    <td className="px-4 py-3"><textarea value={editForm.requirement} onChange={(e) => setEditForm({ ...editForm, requirement: e.target.value })} className="w-full border rounded px-2 py-1 min-h-[72px]" /></td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button onClick={() => saveEdit(m.id)} className="text-emerald-600 hover:text-emerald-800" title="儲存"><Check size={16} /></button>
                        <button onClick={() => setEditingId('')} className="text-gray-500 hover:text-gray-700" title="取消"><X size={16} /></button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-3 whitespace-nowrap">{m.domain}</td>
                    <td className="px-4 py-3 whitespace-nowrap">{m.item}</td>
                    <td className="px-4 py-3"><span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs">{m.level}</span></td>
                    <td className="px-4 py-3 whitespace-pre-wrap">{m.requirement}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button onClick={() => startEdit(m)} className="text-blue-600 hover:text-blue-800" title="編輯"><Edit3 size={16} /></button>
                        <button onClick={() => handleDeleteMeasure(m)} className="text-red-500 hover:text-red-700" title="刪除"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
            {measures.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-10 text-center text-gray-400">尚無控制措施資料</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
