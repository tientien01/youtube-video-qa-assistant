import { API_BASE_URL } from '../../shared/config/api'
import { requestJson } from '../../shared/api/request'
import type { components } from '../../shared/api/schema'

export type RuntimeHealth = components['schemas']['RuntimeHealthResponse']

export async function getRuntimeHealth(): Promise<RuntimeHealth> {
  return requestJson(`${API_BASE_URL}/health`, {}, 'Runtime health is unavailable.') as Promise<RuntimeHealth>
}
