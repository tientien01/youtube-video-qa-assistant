export function VideoResult({ video }) {
  if (!video) {
    return (
      <div className="empty-state">
        <h2>No video indexed yet</h2>
        <p>Submit a YouTube URL to verify the backend ingest endpoint.</p>
      </div>
    )
  }

  return (
    <div className="result-panel">
      <h2>Ingest Result</h2>
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
          <dt>Status</dt>
          <dd>{video.status}</dd>
        </div>
        <div>
          <dt>Chunks</dt>
          <dd>{video.chunk_count}</dd>
        </div>
        <div>
          <dt>Transcript Language</dt>
          <dd>{video.transcript_language || 'Not available yet'}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>
            {video.duration_seconds === null
              ? 'Not available yet'
              : `${video.duration_seconds} seconds`}
          </dd>
        </div>
      </dl>
    </div>
  )
}
