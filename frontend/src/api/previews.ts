/** 样本预览、批次确认与分级分类放行下载的接口封装。 */
import { request } from './client'

export type FieldResult = {
  column_index: number
  field: string
  required: boolean
  status: 'passed' | 'failed'
  ok: boolean
  rule_id: number | null
  rule_no: string
  rule_version: string
  algorithm: string
  rule_status: string
  message: string
  outputs: string[]
}

export type CheckItem = {
  code: string
  ok: boolean
  label: string
  message: string
}

export type PreviewTicket = {
  id: number
  batch_no: string
  title: string
  rule_version: string
  requested_version?: string
  confirmed_version?: string
  version_uniform: boolean
  columns: string[]
  required_columns: string[]
  rows: unknown[][]
  row_count: number
  column_count: number
  field_results: FieldResult[]
  all_passed: boolean
  required_passed: boolean
  status: string
  confirmed: boolean
  confirm_message?: string
  confirmed_at?: string
  released: boolean
  release_status: string
  released_at?: string
  created_at?: string
  checks?: CheckItem[]
  can_confirm?: boolean
  can_release?: boolean
  can_download?: boolean
  blocking_reasons?: string[]
}

export type GateState = {
  has_ticket: boolean
  can_confirm: boolean
  can_release?: boolean
  can_download: boolean
  message: string
  active_id?: number
  ticket: PreviewTicket | null
  checks: CheckItem[]
}

export type PreviewPayload = {
  rule_version: string
  columns: Array<string | { field: string; required: boolean; rule_id?: string | number | null }>
  rows: string[][]
}

async function jsonOrThrow(response: Response): Promise<any> {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data?.message || data?.detail || `接口返回 ${response.status}`)
  }
  return data
}

export async function bootstrapScenarioRules(): Promise<{ ok: boolean; message: string; created: number }> {
  const response = await request('/api/mask_rule/scenario/bootstrap', { method: 'POST', body: '{}' })
  return jsonOrThrow(response)
}

export async function publishVersion(version: string): Promise<{ ok: boolean; message: string }> {
  const response = await request('/api/mask_rule/versions/publish', {
    method: 'POST',
    body: JSON.stringify({ version }),
  })
  return jsonOrThrow(response)
}

export async function createPreview(payload: PreviewPayload): Promise<{ ok: boolean; message: string; entry?: PreviewTicket }> {
  const response = await request('/api/mask_rule/previews', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return jsonOrThrow(response)
}

export async function listPreviews(): Promise<{ items: PreviewTicket[]; total: number; active_id: number | null }> {
  const response = await request('/api/mask_rule/previews')
  return jsonOrThrow(response)
}

export async function getPreview(id: number | 'active'): Promise<{ ok: boolean; ticket: PreviewTicket }> {
  const response = await request(`/api/mask_rule/previews/${id}`)
  return jsonOrThrow(response)
}

export async function confirmPreview(id: number): Promise<{ ok: boolean; message: string; entry?: PreviewTicket }> {
  const response = await request(`/api/mask_rule/previews/${id}/confirm`, { method: 'POST', body: '{}' })
  return jsonOrThrow(response)
}

export async function activatePreview(id: number): Promise<{ ok: boolean; message: string }> {
  const response = await request(`/api/mask_rule/previews/${id}/activate`, { method: 'POST', body: '{}' })
  return jsonOrThrow(response)
}

export async function fetchGate(): Promise<GateState> {
  const response = await request('/api/classify_tag/release')
  return jsonOrThrow(response)
}

export async function confirmRelease(ticketId?: number, entryId?: number): Promise<{ ok: boolean; message: string }> {
  const response = await request('/api/classify_tag/release/confirm', {
    method: 'POST',
    body: JSON.stringify({ ticket_id: ticketId, entry_id: entryId }),
  })
  return jsonOrThrow(response)
}

/** 下载指定预览单的交付 CSV；未放行/校验失败时服务端返回 409，这里抛出可读错误。 */
export async function downloadTicket(ticketId: number, filename?: string): Promise<void> {
  const response = await request(`/api/mask_rule/previews/${ticketId}/download`)
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data?.message || data?.detail || `下载失败（${response.status}）`)
  }
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename || `masked-preview-${ticketId}.csv`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

/** 任意预览/放行状态变化后广播，工作台内嵌的两个面板据此互相同步。 */
export const PREVIEW_CHANGED_EVENT = 'mask-preview:changed'

export function notifyPreviewChanged(): void {
  window.dispatchEvent(new CustomEvent(PREVIEW_CHANGED_EVENT))
}
