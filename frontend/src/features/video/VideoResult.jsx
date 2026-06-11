import { formatDuration } from '../../shared/utils/time'

export function VideoResult({ video, onRebuildIndex, isRebuilding }) {
  if (!video) {
    return (
      <div className="empty-state">
        <h2>No active video</h2>
        <p>Ingest or select a video to open the learning workspace.</p>
      </div>
    )
  }

  const embedUrl = `https://www.youtube.com/embed/${video.video_id}`

  return (
    <section className="result-panel" aria-label="Active video">
      <div className="video-frame">
        <iframe
          src={embedUrl}
          title={video.title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>

      <div className="video-detail-header">
        {video.thumbnail_url ? (
          <img className="video-thumbnail" src={video.thumbnail_url} alt="" />
        ) : null}
        <div>
          <p className="eyebrow">Active video</p>
          <h2>{video.title}</h2>
          <p className="muted-text">{video.channel_title || 'Unknown channel'}</p>
        </div>
      </div>

      <dl className="metadata-grid">
        <div>
          <dt>Status</dt>
          <dd>{video.status || 'cached'}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>{formatDuration(video.duration_seconds)}</dd>
        </div>
        <div>
          <dt>Transcript</dt>
          <dd>{video.transcript_language || 'Unknown'}</dd>
        </div>
        <div>
          <dt>Chunks</dt>
          <dd>{video.chunk_count || 0}</dd>
        </div>
        <div>
          <dt>Video ID</dt>
          <dd>{video.video_id}</dd>
        </div>
      </dl>

      <button
        className="rebuild-index-button"
        type="button"
        onClick={() => onRebuildIndex(video.video_id)}
        disabled={isRebuilding}
      >
        {isRebuilding ? 'Rebuilding index...' : 'Rebuild index'}
      </button>
    </section>
  )
}
