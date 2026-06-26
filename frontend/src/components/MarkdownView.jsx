import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

export default function MarkdownView({ children }) {
  return (
    <div className="prose prose-sm md:prose-base max-w-none
      prose-headings:text-gray-800 prose-headings:border-b prose-headings:pb-2 prose-headings:mb-3
      prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
      prose-p:text-gray-700 prose-p:leading-relaxed
      prose-table:border-collapse prose-table:w-full prose-table:text-sm
      prose-th:bg-slate-100 prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:border prose-th:border-gray-300
      prose-td:px-3 prose-td:py-2 prose-td:border prose-td:border-gray-200
      prose-li:text-gray-700
      prose-strong:text-gray-900
      prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded prose-code:text-sm
    ">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
