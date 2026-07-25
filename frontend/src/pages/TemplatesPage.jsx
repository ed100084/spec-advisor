import { useState, useEffect } from 'react'
import { Wand2, Save, Loader2 } from 'lucide-react'
import MarkdownView from '../components/MarkdownView'
import { generateTemplate, saveTemplate, getTemplates, getTemplate } from '../api'

const categories = ['IT設備', '軟體系統', '網路設備', '醫療設備', '工程營建', '辦公設備', '其他']

export default function TemplatesPage() {
  const [category, setCategory] = useState('IT設備')
  const [description, setDescription] = useState('')
  const [generated, setGenerated] = useState('')
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState([])
  const [templateName, setTemplateName] = useState('')

  useEffect(() => {
    getTemplates().then(({ data }) => setTemplates(data))
  }, [])

  const handleGenerate = async () => {
    if (!description) return alert('請輸入需求描述')
    setLoading(true)
    try {
      const { data } = await generateTemplate(category, description)
      setGenerated(data.content)
    } catch (err) {
      alert(`產生失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!templateName || !generated) return
    await saveTemplate({ name: templateName, category, content: generated })
    setTemplateName('')
    const { data } = await getTemplates()
    setTemplates(data)
    alert('範本已儲存')
  }

  const handleLoad = async (id) => {
    const { data } = await getTemplate(id)
    setGenerated(data.content)
    setCategory(data.category)
    setTemplateName(data.name)
  }

  return (
    <div>
      <h2 className="mb-4 text-xl font-bold md:mb-6 md:text-2xl">規格書範本產生</h2>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Generator */}
        <div className="lg:col-span-2">
          <div className="mb-6 rounded-xl bg-white p-4 shadow-sm md:p-6">
            <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">類別</label>
                <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full border rounded-lg px-3 py-2">
                  {categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">需求描述</label>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="例如：採購 10 台桌上型電腦，需支援 AI 運算..."
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>
            </div>
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700 disabled:opacity-50 sm:w-auto"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
              AI 產生範本
            </button>
          </div>

          {generated && (
            <div className="rounded-xl bg-white p-4 shadow-sm md:p-6">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
                <input
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="範本名稱"
                  className="border rounded-lg px-3 py-2 flex-1"
                />
                <button
                  onClick={handleSave}
                  disabled={!templateName.trim()}
                  className="flex min-h-11 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Save size={16} /> 儲存範本
                </button>
              </div>
              <MarkdownView>{generated}</MarkdownView>
            </div>
          )}
        </div>

        {/* Right: Saved Templates */}
        <div>
          <div className="rounded-xl bg-white p-4 shadow-sm md:p-6">
            <h3 className="font-semibold mb-4">已儲存範本</h3>
            {templates.length === 0 ? (
              <p className="text-gray-400 text-sm">尚無儲存的範本</p>
            ) : (
              <div className="space-y-2">
                {templates.map((t) => (
                  <button
                    type="button"
                    key={t.id}
                    onClick={() => handleLoad(t.id)}
                    className="w-full rounded-lg border p-3 text-left hover:bg-gray-50"
                  >
                    <p className="font-medium text-sm">{t.name}</p>
                    <p className="text-xs text-gray-400">{t.category} · {new Date(t.created_at).toLocaleDateString('zh-TW')}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
