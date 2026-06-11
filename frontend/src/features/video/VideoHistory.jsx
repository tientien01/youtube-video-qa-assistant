import { formatDuration } from '../../shared/utils/time'

export function VideoHistory({
  videos,
  currentVideoId,
  onSelect,
  onDelete,
  isLoading,
}) {
  return (
    <section className="history-panel" aria-label="Ingested videos">
      <div className="panel-heading compact-heading">
        <h2>Video library</h2>
        <p className="muted-text">Previously indexed videos are ready to use again.</p>
      </div>

      {isLoading ? <p className="muted-text">Loading videos...</p> : null}

      {!isLoading && videos.length === 0 ? (
        <p className="muted-text">No ingested videos yet.</p>
      ) : null}

      {videos.length > 0 ? (
        <div className="history-list">
          {videos.map((video) => {
            const isCurrent = video.video_id === currentVideoId

            return (
              <article className="history-item" key={video.video_id}>
                <button
                  className="history-select"
                  type="button"
                  onClick={() => onSelect(video)}
                  aria-current={isCurrent ? 'true' : undefined}
                >
                  <span className="history-title">{video.title}</span>
                  <span className="history-meta">
                    {video.channel_title || 'Unknown channel'}
                    {' | '}
                    {video.chunk_count || 0} chunks
                    {' | '}
                    {formatDuration(video.duration_seconds)}
                  </span>
                </button>
                <button
                  className="history-delete"
                  type="button"
                  onClick={() => onDelete(video.video_id)}
                >
                  Delete
                </button>
              </article>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
