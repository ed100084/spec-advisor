import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

function preprocess(text) {
  if (!text) return ''
  let result = text
  // Ensure headings have blank line before them
  result = result.replace(/([^\n])\n(#{1,3} )/g, '$1\n\n$2')
  // Keep numbered spec sections from collapsing into one paragraph.
  result = result.replace(/([^\n|])\n(\*\*\d+(?:\.\d+)*[.、 ]|\d+(?:\.\d+)+[.、 ]|\d+[.、 ]\S)/g, '$1\n\n$2')
  // Ensure blank line before the FIRST row of a table block (not between table rows)
  // A table starts when a non-pipe line is followed by a pipe line
  result = result.replace(/([^\n|])\n(\|)/g, '$1\n\n$2')
  return result
}

export default function MarkdownView({ children }) {
  return (
    <div className="prose prose-sm md:prose-base max-w-none
      prose-headings:text-gray-800 prose-headings:border-b prose-headings:border-gray-200 prose-headings:pb-2 prose-headings:mb-3
      prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-h3:border-0
      prose-p:text-gray-700 prose-p:leading-relaxed prose-p:my-2
      prose-table:border-collapse prose-table:w-full prose-table:text-sm
      prose-thead:bg-slate-100
      prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:border prose-th:border-gray-300 prose-th:font-semibold
      prose-td:px-3 prose-td:py-2 prose-td:border prose-td:border-gray-200 prose-td:align-top
      prose-tr:even:bg-gray-50
      prose-li:text-gray-700 prose-li:my-0.5
      prose-ul:my-2 prose-ol:my-2
      prose-strong:text-blue-800
      prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded prose-code:text-sm
      prose-blockquote:border-l-4 prose-blockquote:border-blue-300 prose-blockquote:bg-blue-50 prose-blockquote:py-1 prose-blockquote:px-4
    ">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
        {preprocess(children)}
      </ReactMarkdown>
    </div>
  )
}
