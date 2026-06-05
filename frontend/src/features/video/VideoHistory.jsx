export function VideoHistory({
  videos,
  currentVideoId,
  onSelect,
  onDelete,
  isLoading,
}) {
  return (
    <section className="history-panel" aria-label="Video đã xử lý">
      <div className="panel-heading">
        <h2>Video đã xử lý</h2>
        <p className="muted-text">Chọn lại video cũ để hỏi tiếp mà không cần dán URL lại.</p>
      </div>

      {isLoading ? <p className="muted-text">Đang tải danh sách video...</p> : null}

      {!isLoading && videos.length === 0 ? (
        <p className="muted-text">Chưa có video nào trong lịch sử.</p>
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
                    {video.chunk_count} chunks
                    {video.transcript_language ? ` - ${video.transcript_language}` : ''}
                  </span>
                </button>
                <button
                  className="history-delete"
                  type="button"
                  onClick={() => onDelete(video.video_id)}
                >
                  Xóa
                </button>
              </article>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
