import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'
import type { components } from '../../shared/api/schema'

export type IngestJob = components['schemas']['IngestJobResponse']
export type VideoMetadata = components['schemas']['VideoMetadataResponse']
export type VideoIngest = components['schemas']['VideoIngestResponse']
export type VideoTranscript = components['schemas']['VideoTranscriptResponse']

export async function createIngestJob(url: string): Promise<IngestJob> {
  return requestJson(`${API_BASE_URL}/ingest-jobs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  }, 'Could not start video ingest.') as Promise<IngestJob>
}

export async function getIngestJob(jobId: string): Promise<IngestJob> {
  return requestJson(`${API_BASE_URL}/ingest-jobs/${jobId}`, {}, 'Could not refresh ingest status.') as Promise<IngestJob>
}

export async function retryIngestJob(jobId: string): Promise<IngestJob> {
  return requestJson(`${API_BASE_URL}/ingest-jobs/${jobId}/retry`, { method: 'POST' }, 'Could not retry ingest.') as Promise<IngestJob>
}

export async function cancelIngestJob(jobId: string): Promise<IngestJob> {
  return requestJson(`${API_BASE_URL}/ingest-jobs/${jobId}/cancel`, { method: 'POST' }, 'Could not cancel ingest.') as Promise<IngestJob>
}

export async function listVideos(): Promise<VideoMetadata[]> {
  return requestJson(`${API_BASE_URL}/videos`, {}, 'Could not load the video library.') as Promise<VideoMetadata[]>
}

export async function getVideo(videoId: string): Promise<VideoMetadata> {
  return requestJson(`${API_BASE_URL}/videos/${videoId}`, {}, 'Could not load this video.') as Promise<VideoMetadata>
}

export async function getVideoTranscript(videoId: string): Promise<VideoTranscript> {
  return requestJson(`${API_BASE_URL}/videos/${videoId}/transcript`, {}, 'Could not load the transcript.') as Promise<VideoTranscript>
}

export async function deleteVideo(videoId: string) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'DELETE',
  }, 'Could not delete this video.')
}

export async function rebuildVideoIndex(videoId: string) {
  return requestJson(`${API_BASE_URL}/videos/${videoId}/rebuild-index`, {
    method: 'POST',
  }, 'Could not rebuild the index.')
}
