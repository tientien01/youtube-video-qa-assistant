export function VideoResult({ video }) {
  if (!video) {
    return (
      <div className="empty-state">
        <h2>Chưa có video nào được index</h2>
        <p>Nhập URL YouTube để lấy transcript và tạo index RAG.</p>
      </div>
    )
  }

  const embedUrl = `https://www.youtube.com/embed/${video.video_id}`

  return (
    <div className="result-panel">
      <div className="video-frame">
        <iframe
          src={embedUrl}
          title={video.title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>

      <h2>Kết quả ingest</h2>
      <dl>
        <div>
          <dt>Video ID</dt>
          <dd>{video.video_id}</dd>
        </div>
        <div>
          <dt>Title</dt>
          <dd>{video.title}</dd>
        </div>
        <div>
          <dt>Trạng thái</dt>
          <dd>{video.status}</dd>
        </div>
        <div>
          <dt>Chunks</dt>
          <dd>{video.chunk_count}</dd>
        </div>
        <div>
          <dt>Ngôn ngữ transcript</dt>
          <dd>{video.transcript_language || 'Chưa có'}</dd>
        </div>
        <div>
          <dt>Thời lượng</dt>
          <dd>
            {video.duration_seconds === null
              ? 'Chưa có'
              : `${video.duration_seconds} giây`}
          </dd>
        </div>
      </dl>
    </div>
  )
}
