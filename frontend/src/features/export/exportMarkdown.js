import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time.js'

export function buildLearningMarkdown({ video, summary, notes }) {
  if (!video) {
    return ''
  }

  const videoUrl = video.url || `https://www.youtube.com/watch?v=${video.video_id}`
  const lines = [
    `# ${safeText(video.title || `YouTube video ${video.video_id}`)}`,
    '',
    '## Video',
    '',
    `- Video ID: ${safeText(video.video_id)}`,
    `- URL: ${videoUrl}`,
    `- Transcript language: ${safeText(video.transcript_language || 'Unknown')}`,
    `- Chunks: ${safeText(video.chunk_count ?? 'Unknown')}`,
  ]

  if (video.duration_seconds !== null && video.duration_seconds !== undefined) {
    lines.push(`- Duration: ${safeText(video.duration_seconds)} seconds`)
  }

  lines.push('', '## Summary', '')

  if (summary?.summary) {
    lines.push(`Mode: ${safeText(summary.mode || 'unknown')}`, '', summary.summary.trim(), '')
    appendSources(lines, {
      heading: 'Summary sources',
      sources: summary.sources,
      videoId: video.video_id,
    })
  } else {
    lines.push('No summary has been generated yet.', '')
  }

  lines.push('## Study Notes', '')

  if (notes?.notes) {
    lines.push(notes.notes.trim(), '')
    appendSources(lines, {
      heading: 'Study notes sources',
      sources: notes.sources,
      videoId: video.video_id,
    })
  } else {
    lines.push('No study notes have been generated yet.', '')
  }

  return `${lines.join('\n').trim()}\n`
}

export function buildMarkdownFilename(video) {
  const title = video?.title || video?.video_id || 'youtube-learning-notes'
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80)

  return `${slug || 'youtube-learning-notes'}.md`
}

function appendSources(lines, { heading, sources = [], videoId }) {
  if (!sources.length) {
    return
  }

  lines.push(`### ${heading}`, '')

  sources.forEach((source) => {
    const timestamp = formatTimestamp(source.start_seconds)
    const url = buildYouTubeTimestampUrl(videoId, source.start_seconds)
    const text = safeText(source.text).replace(/\s+/g, ' ').trim()
    lines.push(`- [${timestamp}](${url}) - ${text}`)
  })

  lines.push('')
}

function safeText(value) {
  return String(value ?? '').trim()
}
