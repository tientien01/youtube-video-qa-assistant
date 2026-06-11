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
      <section className="export-panel" aria-label="Export Markdown">
        <h2>Export Markdown</h2>
        <p className="muted-text">Select an ingested video before exporting a study pack.</p>
      </section>
    )
  }

  async function handleCopy() {
    setStatus('')
    setError('')

    try {
      await navigator.clipboard.writeText(markdown)
      setStatus('Markdown copied to clipboard.')
    } catch {
      setError('This browser could not copy Markdown to the clipboard.')
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
    setStatus('Markdown download started.')
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
    <section className="export-panel" aria-label="Export Markdown">
      <div className="panel-heading">
        <h2>Export Markdown</h2>
        <p className="muted-text">Build a portable study pack from generated content and selected Q&A.</p>
      </div>

      <fieldset className="export-options">
        <legend>Included content</legend>
        <label>
          <input
            type="checkbox"
            checked={exportOptions.summary}
            onChange={() => updateExportOption('summary')}
          />
          <span>Summary {summary ? '' : '(empty)'}</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={exportOptions.notes}
            onChange={() => updateExportOption('notes')}
          />
          <span>Study Notes {notes ? '' : '(empty)'}</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={exportOptions.quiz}
            onChange={() => updateExportOption('quiz')}
          />
          <span>Quiz {quiz ? '' : '(empty)'}</span>
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
        <summary>Markdown preview</summary>
        <pre>{markdown}</pre>
      </details>
    </section>
  )
}
