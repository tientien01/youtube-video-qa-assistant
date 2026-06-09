import { useMemo, useState } from 'react'
import { buildLearningMarkdown, buildMarkdownFilename, defaultExportOptions } from './exportMarkdown'

export function ExportPanel({ video, summary, notes, quiz, selectedMessages = [] }) {
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [exportOptions, setExportOptions] = useState(() => defaultExportOptions())
  const markdown = useMemo(
    () => buildLearningMarkdown({
      video,
      summary,
      notes,
      quiz,
      selectedMessages,
      exportOptions,
    }),
    [video, summary, notes, quiz, selectedMessages, exportOptions],
  )

  if (!video) {
    return (
      <section className="export-panel" aria-label="Khu vực export Markdown">
        <h2>Export Markdown</h2>
        <p className="muted-text">Ingest một video trước khi export tài liệu học tập.</p>
      </section>
    )
  }

  async function handleCopy() {
    setStatus('')
    setError('')

    try {
      await navigator.clipboard.writeText(markdown)
      setStatus('Đã copy Markdown vào clipboard.')
    } catch {
      setError('Không thể copy Markdown trong trình duyệt hiện tại.')
    }
  }

  function handleDownload() {
    setStatus('')
    setError('')

    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = buildMarkdownFilename(video)
    link.click()
    URL.revokeObjectURL(url)
    setStatus('Đã tạo file Markdown để tải xuống.')
  }

  function updateExportOption(optionName) {
    setExportOptions((currentOptions) => ({
      ...currentOptions,
      [optionName]: !currentOptions[optionName],
    }))
    setStatus('')
    setError('')
  }

  return (
    <section className="export-panel" aria-label="Khu vực export Markdown">
      <div className="panel-heading">
        <h2>Export Markdown</h2>
        <p className="muted-text">
          Xuất metadata video, nội dung học tập và các Q&A đã chọn ra Markdown.
        </p>
      </div>

      <fieldset className="export-options">
        <legend>Nội dung export</legend>
        <label>
          <input
            type="checkbox"
            checked={exportOptions.summary}
            onChange={() => updateExportOption('summary')}
          />
          <span>Summary</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={exportOptions.notes}
            onChange={() => updateExportOption('notes')}
          />
          <span>Study Notes</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={exportOptions.quiz}
            onChange={() => updateExportOption('quiz')}
          />
          <span>Quiz</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={exportOptions.chat}
            onChange={() => updateExportOption('chat')}
          />
          <span>Selected Q&A ({selectedMessages.length})</span>
        </label>
      </fieldset>

      <div className="export-actions">
        <button type="button" onClick={handleCopy}>Copy Markdown</button>
        <button type="button" onClick={handleDownload}>Download Markdown</button>
      </div>

      {status ? <p className="success-message">{status}</p> : null}
      {error ? <p className="error-message">{error}</p> : null}

      <details className="export-preview">
        <summary>Xem Markdown</summary>
        <pre>{markdown}</pre>
      </details>
    </section>
  )
}
