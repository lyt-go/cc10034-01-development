<template>
  <section class="release-panel" data-testid="release-panel" data-module="classify_tag">
    <div class="preview-head">
      <div>
        <h3>脱敏预览核对与下载放行</h3>
        <p class="preview-sub">
          分级分类人员依据分析员确认的批次预览单核对规则版本与逐字段结果：
          必需字段处理失败时不能确认分级、不能放行，也不能只下载剩余字段。
        </p>
      </div>
      <div class="preview-head-actions">
        <RouterLink class="btn" to="/mask_rule" data-testid="goto-mask-preview">
          去脱敏规则工作台提交预览
        </RouterLink>
        <button class="btn ghost" data-testid="refresh-release" type="button" @click="refresh">刷新核对</button>
      </div>
    </div>

    <p v-if="message" class="form-message" :class="{ error: messageError }" data-testid="release-message">
      {{ message }}
    </p>
    <p
      v-else-if="gate?.has_ticket && ticket && !ticket.can_release"
      class="form-message error"
      data-testid="release-gate-message"
    >
      当前不能放行：{{ gate.message || ticket.blocking_reasons?.join('；') }}
    </p>

    <div v-if="!gate?.has_ticket" class="empty-release" data-testid="release-empty">
      当前还没有任何样本预览单。请先到
      <RouterLink to="/mask_rule">脱敏规则工作台 → 样本预览与批次确认</RouterLink>
      提交两列三行样本并由分析员确认后，再回到本页放行下载。
    </div>

    <template v-else>
      <div class="release-select-bar">
        <label>
          放行依据预览单：
          <select
            :value="selectedId ?? undefined"
            data-testid="release-ticket-select"
            aria-label="选择放行依据预览单"
            @change="onSelect(Number(($event.target as HTMLSelectElement).value))"
          >
            <option v-for="ticket in tickets" :key="ticket.id" :value="ticket.id">
              {{ ticket.batch_no }} · {{ ticket.confirmed_version || ticket.rule_version }} ·
              {{ ticket.status }}{{ ticket.released ? ' · 已开放下载' : '' }}
            </option>
          </select>
        </label>
        <span v-if="ticket" class="version-badge" data-testid="release-version">
          规则版本 {{ ticket.confirmed_version || ticket.rule_version }}
        </span>
        <span v-if="ticket" class="status-badge" :class="ticket.confirmed ? 'ok' : 'pending'">
          {{ ticket.status }}
        </span>
        <span v-if="ticket?.released" class="status-badge ok">已开放下载</span>
      </div>

      <div v-if="ticket" class="release-grid" data-testid="release-detail" :data-ticket-id="ticket.id">
        <table class="data-table" data-testid="release-field-results">
          <thead>
            <tr>
              <th>字段（列）</th>
              <th>处理结果</th>
              <th>命中规则</th>
              <th>规则版本</th>
              <th>算法</th>
              <th>处理后样本</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="field in ticket.field_results"
              :key="field.column_index"
              :data-testid="`release-field-${field.column_index}`"
              :data-status="field.status"
              :class="field.ok ? 'field-ok' : 'field-failed'"
            >
              <td>{{ field.field }}<span v-if="field.required" class="required-tag">必需</span></td>
              <td>
                <span class="result-dot" :class="field.ok ? 'ok' : 'fail'">{{ field.ok ? '通过' : '失败' }}</span>
                <div class="field-message" :class="{ 'error-text': !field.ok }">{{ field.message }}</div>
              </td>
              <td>{{ field.rule_no || '—' }}</td>
              <td :data-testid="`release-field-version-${field.column_index}`">{{ field.rule_version || '—' }}</td>
              <td>{{ field.algorithm || '—' }}</td>
              <td>{{ field.outputs.join(' ｜ ') || '—' }}</td>
            </tr>
          </tbody>
        </table>

        <ul v-if="ticket.checks?.length" class="check-list" data-testid="release-checks">
          <li v-for="check in ticket.checks" :key="check.code" :data-ok="String(check.ok)" :data-code="check.code">
            <span :class="check.ok ? 'check-ok' : 'check-fail'">{{ check.ok ? '✓' : '✕' }}</span>
            <strong>{{ check.label }}：</strong>{{ check.message }}
          </li>
        </ul>

        <div class="release-actions">
          <button
            class="btn primary"
            data-testid="confirm-release"
            type="button"
            :data-can-release="String(Boolean(ticket.can_release))"
            :disabled="releasing"
            @click="doConfirmRelease"
          >
            {{ releasing ? '提交中…' : '确认开放下载（同时完成分级确认）' }}
          </button>
          <button
            class="btn"
            data-testid="download-delivery"
            type="button"
            :data-can-download="String(Boolean(ticket.can_download))"
            :data-blocked="String(!ticket.can_download)"
            :disabled="downloading"
            :title="ticket.can_download ? '下载已确认的脱敏交付样本' : '当前未满足下载条件，点击可查看服务端拦截原因'"
            @click="doDownload"
          >
            {{ downloading ? '准备下载…' : '下载脱敏交付样本（CSV）' }}
          </button>
          <span class="inline-hint">
            放行条件：分析员已确认 + 必需字段全部通过 + 锁定规则仍存在且生效 + 分级分类确认。
          </span>
        </div>
        <p v-if="downloadError" class="form-message error" data-testid="download-error">{{ downloadError }}</p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import {
  activatePreview,
  confirmRelease,
  downloadTicket,
  fetchGate,
  listPreviews,
  notifyPreviewChanged,
  PREVIEW_CHANGED_EVENT,
  type GateState,
  type PreviewTicket,
} from '@/api/previews'

const gate = ref<GateState | null>(null)
const tickets = ref<PreviewTicket[]>([])
const selectedId = ref<number | null>(null)
const message = ref('')
const messageError = ref(false)
const downloadError = ref('')
const releasing = ref(false)
const downloading = ref(false)

const ticket = computed<PreviewTicket | null>(() => {
  if (selectedId.value != null) {
    return tickets.value.find((item) => item.id === selectedId.value) ?? gate.value?.ticket ?? null
  }
  return gate.value?.ticket ?? null
})

async function refresh() {
  try {
    const [gateState, list] = await Promise.all([fetchGate(), listPreviews()])
    gate.value = gateState
    tickets.value = list.items
    if (selectedId.value == null) {
      selectedId.value = gateState.active_id ?? list.active_id ?? list.items[0]?.id ?? null
    }
    message.value = ''
  } catch (error) {
    messageError.value = true
    message.value = error instanceof Error ? error.message : '放行状态读取失败'
  }
}

async function onSelect(id: number) {
  selectedId.value = id
  downloadError.value = ''
  try {
    await activatePreview(id)
    notifyPreviewChanged()
    await refresh()
  } catch (error) {
    messageError.value = true
    message.value = error instanceof Error ? error.message : '切换预览单失败'
  }
}

async function doConfirmRelease() {
  releasing.value = true
  messageError.value = false
  message.value = ''
  try {
    const result = await confirmRelease(selectedId.value ?? undefined)
    if (!result.ok) throw new Error(result.message || '确认放行失败')
    message.value = result.message
    notifyPreviewChanged()
    await refresh()
  } catch (error) {
    messageError.value = true
    message.value = error instanceof Error ? error.message : '确认放行失败'
    await refresh()
  } finally {
    releasing.value = false
  }
}

async function doDownload() {
  downloadError.value = ''
  if (selectedId.value == null) return
  downloading.value = true
  try {
    const version = ticket.value?.confirmed_version || ticket.value?.rule_version || ''
    const batch = ticket.value?.batch_no || selectedId.value
    await downloadTicket(selectedId.value, `masked-${batch}-${version}.csv`)
  } catch (error) {
    downloadError.value = error instanceof Error ? error.message : '下载失败'
  } finally {
    downloading.value = false
  }
}

function handleExternalChange() {
  void refresh()
}

onMounted(() => {
  void refresh()
  window.addEventListener(PREVIEW_CHANGED_EVENT, handleExternalChange)
})

onBeforeUnmount(() => {
  window.removeEventListener(PREVIEW_CHANGED_EVENT, handleExternalChange)
})
</script>
