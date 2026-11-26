<template>
  <section
    class="preview-panel"
    data-testid="preview-panel"
    data-module="mask_rule"
  >
    <div class="preview-head">
      <div>
        <h3>样本预览与批次确认</h3>
        <p class="preview-sub">
          分析员提交一小批样本与规则版本，服务端返回逐字段处理结果和批次预览单；
          确认后版本与字段结果冻结，分级分类人员据此决定是否开放下载。
        </p>
      </div>
      <div class="preview-head-actions">
        <button class="btn" data-testid="bootstrap-rules" type="button" @click="bootstrap">
          补齐第3/4版演练规则
        </button>
        <button class="btn" data-testid="fill-sample" type="button" @click="fillSample">
          填充两列三行样本
        </button>
        <button class="btn ghost" data-testid="toggle-preview" type="button" @click="collapsed = !collapsed">
          {{ collapsed ? '展开面板' : '收起面板' }}
        </button>
      </div>
    </div>

    <div v-show="!collapsed" class="preview-body">
      <div class="preview-form">
        <label class="version-field">
          <span>规则版本（整单锁定）</span>
          <input
            v-model="version"
            list="mask-rule-version-options"
            data-testid="preview-version"
            placeholder="例如 v3"
          />
          <datalist id="mask-rule-version-options">
            <option v-for="item in versionOptions" :key="item" :value="item" />
          </datalist>
        </label>
        <button class="btn" data-testid="publish-version" type="button" :disabled="publishing" @click="publishCurrentVersion">
          {{ publishing ? '发布中…' : `发布${version || '该'}版规则（标记生效）` }}
        </button>
        <span class="inline-hint">单次预览中的所有字段必须按同一版规则生成；v3 与 v4 不会混用。</span>
      </div>

      <div class="bulk-edit">
        <label class="bulk-text-field">
          <span>批量样本（可直接粘贴 TSV / CSV；列与下方表格双向对应）</span>
          <textarea
            v-model="bulkText"
            rows="4"
            data-testid="preview-sample"
            aria-label="批量样本数据，首行可作为字段名"
            :placeholder="bulkPlaceholder"
            @input="bulkDirty = true"
          />
        </label>
        <div class="bulk-actions">
          <label class="required-check">
            <input v-model="headerFirst" type="checkbox" data-testid="preview-header-first" />
            首行为字段名
          </label>
          <button class="btn" type="button" data-testid="apply-bulk" @click="applyBulk">应用文本到表格</button>
        </div>
      </div>

      <table class="data-table preview-grid" data-testid="preview-grid">
        <thead>
          <tr>
            <th class="row-index-col">#</th>
            <th v-for="(column, index) in columns" :key="index">
              <input
                v-model="column.field"
                class="col-name-input"
                :data-testid="`preview-column-${index}`"
                :aria-label="`第${index + 1}列字段名（目标字段）`"
                placeholder="目标字段，如 身份证号"
              />
              <div class="col-meta">
                <label class="required-check">
                  <input
                    v-model="column.required"
                    type="checkbox"
                    :data-testid="`preview-required-${index}`"
                  />
                  必需字段
                </label>
                <select
                  v-model="column.ruleRef"
                  :data-testid="`preview-rule-${index}`"
                  :aria-label="`第${index + 1}列规则选择`"
                >
                  <option value="">自动匹配（字段 + 版本）</option>
                  <option value="__missing__">找不到规则（模拟缺失）</option>
                  <option v-for="rule in ruleOptions" :key="rule.id" :value="String(rule.id)">
                    {{ rule['规则编号'] }} · {{ rule['目标字段'] }} · {{ rule['规则版本'] }} · {{ rule.status }}
                  </option>
                </select>
              </div>
            </th>
            <th class="row-index-col">
              <button class="link" data-testid="add-column" type="button" @click="addColumn">+ 加一列</button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rowCount" :key="`row-${r - 1}`">
            <td class="row-index-col">第{{ r }}行</td>
            <td v-for="(column, c) in columns" :key="c">
              <input
                v-model="sampleRows[r - 1][c]"
                :data-testid="`preview-cell-${r - 1}-${c}`"
                :aria-label="`第${r}行第${c + 1}列样本值`"
              />
            </td>
            <td class="row-index-col" />
          </tr>
        </tbody>
      </table>

      <div class="preview-submit-bar">
        <button class="btn" data-testid="add-row" type="button" @click="addRow">+ 加一行</button>
        <button
          class="btn primary"
          data-testid="submit-preview"
          type="button"
          :disabled="submitting"
          @click="submit"
        >
          {{ submitting ? '服务端处理中…' : '提交预览（生成逐字段结果与批次单）' }}
        </button>
        <span v-if="formMessage" class="form-message" data-testid="submit-message">{{ formMessage }}</span>
        <button
          v-if="lastSubmitMissing"
          class="btn primary"
          data-testid="bootstrap-and-retry"
          type="button"
          :disabled="submitting"
          @click="bootstrapAndRetry"
        >
          一键补齐第3/4版规则并用当前样本重试
        </button>
      </div>

      <div
        v-if="current"
        class="preview-result"
        data-testid="preview-result"
        :data-ticket-id="current.id"
        :data-passed="String(current.required_passed)"
      >
        <div class="result-title-row">
          <h4>
            <span data-testid="preview-batch-no">{{ current.batch_no }}</span>
            <span class="version-badge" data-testid="preview-batch-version">
              锁定版本 {{ current.confirmed_version || current.rule_version }}
            </span>
            <span
              class="status-badge"
              :class="current.confirmed ? 'ok' : 'pending'"
              :data-testid="`preview-status-${current.id}`"
            >
              {{ current.status }}
            </span>
            <span v-if="current.released" class="status-badge ok">已开放下载</span>
          </h4>
          <div class="result-actions">
            <button
              class="btn primary"
              data-testid="confirm-preview"
              type="button"
              :data-can-confirm="String(Boolean(current.can_confirm) && !current.confirmed)"
              :disabled="confirming"
              @click="confirm(current.id)"
            >
              {{ current.confirmed ? `已按 ${current.confirmed_version} 确认（可重复查看结论）` : `确认第${versionLabel(current)}版预览单` }}
            </button>
            <button class="btn" data-testid="activate-preview" type="button" @click="activate(current.id)">
              设为分级分类放行依据
            </button>
          </div>
        </div>
        <p v-if="actionMessage" class="form-message" :class="{ error: actionError }" data-testid="confirm-message">
          {{ actionMessage }}
        </p>
        <p v-if="current.confirmed" class="freeze-note">
          本单已于 {{ current.confirmed_at }} 按 <strong>{{ current.confirmed_version }}</strong>
          确认并冻结；之后发布的新版本不会替换本单内容，交付下载始终使用下列字段结果。
        </p>
        <p v-if="upgradeHint" class="upgrade-hint" data-testid="upgrade-hint">
          检测到更新的生效规则版本 <strong>{{ upgradeHint }}</strong>。
          本旧版预览在其规则未废弃前仍可继续确认与交付，且不会被换版；
          若要求按最新版开放下载，请
          <button class="link" type="button" data-testid="repreview-latest" @click="repreviewWithLatest">
            用 {{ upgradeHint }} 重新预览并重新确认
          </button>
          。
        </p>

        <table class="data-table field-table" data-testid="field-results">
          <thead>
            <tr>
              <th>字段（列）</th>
              <th>处理结果</th>
              <th>命中规则</th>
              <th>规则版本</th>
              <th>算法</th>
              <th>处理后样本（逐行）</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="field in current.field_results"
              :key="field.column_index"
              :data-testid="`field-result-${field.column_index}`"
              :data-status="field.status"
              :data-field="field.field"
              :class="field.ok ? 'field-ok' : 'field-failed'"
            >
              <td>
                {{ field.field }}
                <span v-if="field.required" class="required-tag">必需</span>
              </td>
              <td>
                <span class="result-dot" :class="field.ok ? 'ok' : 'fail'">
                  {{ field.ok ? '通过' : '失败' }}
                </span>
                <div class="field-message" :class="{ 'error-text': !field.ok }">{{ field.message }}</div>
              </td>
              <td>{{ field.rule_no || '—' }}<div class="rule-state">{{ field.rule_status }}</div></td>
              <td :data-testid="`field-version-${field.column_index}`">{{ field.rule_version || '—' }}</td>
              <td>{{ field.algorithm || '—' }}</td>
              <td>
                <ul v-if="field.outputs.length" class="output-list">
                  <li v-for="(out, i) in field.outputs" :key="i" :data-testid="`field-output-${field.column_index}-${i}`">
                    {{ out === '' ? '（空）' : out }}
                  </li>
                </ul>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </table>

        <ul v-if="current.checks?.length" class="check-list" data-testid="preview-checks">
          <li v-for="check in current.checks" :key="check.code" :data-ok="String(check.ok)">
            <span :class="check.ok ? 'check-ok' : 'check-fail'">{{ check.ok ? '✓' : '✕' }}</span>
            <strong>{{ check.label }}：</strong>{{ check.message }}
          </li>
        </ul>
      </div>

      <div class="ticket-list" data-testid="preview-batches">
        <h4>批次预览单列表（确认前后都可展开核对规则版本与逐字段结果）</h4>
        <p v-if="!tickets.length" class="inline-hint">还没有预览单，填入样本后点击“提交样本并生成预览”。</p>
        <article
          v-for="ticket in tickets"
          :key="ticket.id"
          class="ticket-card"
          :data-testid="`preview-batch-${ticket.id}`"
          :data-active="String(ticket.id === activeId)"
        >
          <header class="ticket-card-head">
            <button class="link ticket-view" type="button" :data-testid="`view-preview-${ticket.id}`" @click="view(ticket.id)">
              {{ ticket.batch_no }}
            </button>
            <span class="version-badge">{{ ticket.confirmed_version || ticket.rule_version || '未锁定版本' }}</span>
            <span class="status-badge" :class="ticket.confirmed ? 'ok' : 'pending'">{{ ticket.status }}</span>
            <span v-if="ticket.released" class="status-badge ok">已开放下载</span>
            <span v-if="ticket.id === activeId" class="active-tag">当前分级分类依据</span>
            <span class="ticket-meta">{{ ticket.column_count }} 列 × {{ ticket.row_count }} 行 · {{ ticket.created_at }}</span>
            <span class="ticket-card-actions">
              <button
                class="link"
                type="button"
                :data-testid="`confirm-preview-${ticket.id}`"
                :data-can-confirm="String(Boolean(ticket.can_confirm) && !ticket.confirmed)"
                @click="confirm(ticket.id)"
              >
                {{ ticket.confirmed ? '已确认（重复点击查看结论）' : '确认该版预览' }}
              </button>
              <button
                class="link"
                type="button"
                :data-testid="`activate-preview-${ticket.id}`"
                @click="activate(ticket.id)"
              >
                设为放行依据
              </button>
            </span>
          </header>
          <div class="ticket-field-line" data-testid="`batch-fields-${ticket.id}`">
            <span
              v-for="field in ticket.field_results"
              :key="field.column_index"
              class="field-chip"
              :data-status="field.status"
              :data-testid="`batch-field-${ticket.id}-${field.column_index}`"
            >
              {{ field.field }} · {{ field.rule_version || '无版本' }} · {{ field.ok ? '通过' : '失败：' + field.message }}
            </span>
          </div>
          <details v-if="viewingId === ticket.id" open class="ticket-detail" data-testid="`batch-detail-${ticket.id}`">
            <summary>收起逐字段结果</summary>
            <table class="data-table">
              <thead>
                <tr><th>字段</th><th>状态</th><th>规则编号</th><th>版本</th><th>算法</th><th>输出</th></tr>
              </thead>
              <tbody>
                <tr v-for="field in ticket.field_results" :key="field.column_index" :data-status="field.status">
                  <td>{{ field.field }}</td>
                  <td :class="field.ok ? 'check-ok' : 'check-fail'">{{ field.ok ? '通过' : field.message }}</td>
                  <td>{{ field.rule_no || '—' }}</td>
                  <td>{{ field.rule_version || '—' }}</td>
                  <td>{{ field.algorithm || '—' }}</td>
                  <td>{{ field.outputs.join(' ｜ ') || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </details>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { listEntries } from '@/api/backend-service'
import {
  activatePreview,
  bootstrapScenarioRules,
  confirmPreview,
  createPreview,
  listPreviews,
  notifyPreviewChanged,
  PREVIEW_CHANGED_EVENT,
  publishVersion,
  type PreviewTicket,
} from '@/api/previews'
import type { EntryRow } from '@/data/types'

type ColumnDraft = { field: string; required: boolean; ruleRef: string }

const collapsed = ref(false)
const version = ref('v3')
const columns = ref<ColumnDraft[]>([
  { field: '身份证号', required: true, ruleRef: '' },
  { field: '手机号码', required: true, ruleRef: '' },
])
const sampleRows = ref<string[][]>([
  ['110101199003071234', '13812345678'],
  ['310104198811224321', '13987654321'],
  ['440305200101015678', '13700001111'],
])
const bulkText = ref(
  '身份证号,手机号码\n' +
  '110101199003071234,13812345678\n' +
  '310104198811224321,13987654321\n' +
  '440305200101015678,13700001111',
)
const bulkDirty = ref(false)
const headerFirst = ref(true)
const bulkPlaceholder = [
  '身份证号,手机号码',
  '110101199003071234,13812345678',
  '310104198811224321,13987654321',
  '440305200101015678,13700001111',
].join('\n')

function syncBulkFromGrid() {
  const escape = (value: unknown) => {
    const text = String(value ?? '')
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  const lines = [
    columns.value.map((column) => escape(column.field)).join(','),
    ...sampleRows.value.map((row) => columns.value.map((_, i) => escape(row[i])).join(',')),
  ]
  bulkText.value = lines.join('\n')
  bulkDirty.value = false
}

function parseCsvLine(line: string): string[] {
  if (line.includes('\t')) return line.split('\t').map((cell) => cell.trim())
  const out: string[] = []
  let cur = ''
  let quoted = false
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    if (ch === '"' && line[i + 1] === '"') { cur += '"'; i += 1; continue }
    if (ch === '"') { quoted = !quoted; continue }
    if (ch === ',' && !quoted) { out.push(cur.trim()); cur = ''; continue }
    cur += ch
  }
  out.push(cur.trim())
  return out
}

function applyBulk() {
  const lines = bulkText.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  if (!lines.length) {
    formMessage.value = '批量样本为空，请至少输入一行'
    return
  }
  const parsed = lines.map(parseCsvLine)
  const header = headerFirst.value ? parsed[0].map((h) => h.trim()) : []
  const dataLines = headerFirst.value ? parsed.slice(1) : parsed
  const colCount = Math.max(
    columns.value.length,
    header.length,
    ...parsed.map((row) => row.length),
    1,
  )
  const old = columns.value
  columns.value = Array.from({ length: colCount }, (_, i) => ({
    field: header[i] ?? old[i]?.field ?? '',
    required: old[i]?.required ?? true,
    ruleRef: old[i]?.ruleRef ?? '',
  }))
  sampleRows.value = (dataLines.length ? dataLines : [[]]).map((row) =>
    Array.from({ length: colCount }, (_, i) => row[i] ?? ''),
  )
  bulkDirty.value = false
  formMessage.value = `已把批量文本应用为 ${colCount} 列 × ${sampleRows.value.length} 行样本`
}

watch([columns, sampleRows], () => {
  if (!bulkDirty.value) syncBulkFromGrid()
}, { deep: true })

const rules = ref<EntryRow[]>([])
const tickets = ref<PreviewTicket[]>([])
const activeId = ref<number | null>(null)
const current = ref<PreviewTicket | null>(null)
const viewingId = ref<number | null>(null)

const submitting = ref(false)
const confirming = ref(false)
const publishing = ref(false)
const formMessage = ref('')
const actionMessage = ref('')
const actionError = ref(false)
const lastSubmitMissing = ref(false)

const rowCount = computed(() => sampleRows.value.length)
const ruleOptions = computed(() => rules.value)
const versionOptions = computed(() => {
  const values = rules.value.map((rule) => String(rule['规则版本'] || '')).filter(Boolean)
  return Array.from(new Set(['v3', 'v4', ...values]))
})

function majorOf(value: unknown): number {
  const match = String(value ?? '').match(/\d+/)
  return match ? Number(match[0]) : -1
}

/** 当前单使用旧大版本、且已有更新的生效版本时，提示分析员可新版重预演并重新确认。 */
const upgradeHint = computed(() => {
  const ticket = current.value
  if (!ticket) return ''
  const currentMajor = majorOf(ticket.confirmed_version || ticket.rule_version)
  if (currentMajor < 0) return ''
  const effectiveMajors = rules.value
    .filter((rule) => rule.status === '已生效')
    .map((rule) => majorOf(rule['规则版本']))
    .filter((n) => n >= 0)
  const newest = Math.max(...effectiveMajors, -1)
  return newest > currentMajor ? `v${newest}` : ''
})

async function repreviewWithLatest() {
  if (!upgradeHint.value) return
  version.value = upgradeHint.value
  await submit()
}

function versionLabel(ticket: PreviewTicket): string {
  const raw = ticket.rule_version || ticket.confirmed_version || version.value
  const match = String(raw).match(/\d+/)
  return match ? match[0] : String(raw)
}

function fillSample() {
  columns.value = [
    { field: '身份证号', required: true, ruleRef: '' },
    { field: '手机号码', required: true, ruleRef: '' },
  ]
  sampleRows.value = [
    ['110101199003071234', '13812345678'],
    ['310104198811224321', '13987654321'],
    ['440305200101015678', '13700001111'],
  ]
  version.value = 'v3'
  headerFirst.value = true
  syncBulkFromGrid()
  formMessage.value = '已填入两列三行样本，可直接提交预览'
}

function addRow() {
  sampleRows.value.push(columns.value.map(() => ''))
}

function addColumn() {
  columns.value.push({ field: '', required: true, ruleRef: '' })
  sampleRows.value.forEach((row) => row.push(''))
}

async function loadRules() {
  try {
    const page = await listEntries('mask_rule', { size: '200' })
    rules.value = page.items
  } catch {
    rules.value = []
  }
}

async function loadTickets(selectId?: number) {
  try {
    const payload = await listPreviews()
    tickets.value = payload.items
    activeId.value = payload.active_id
    const targetId = selectId ?? current.value?.id ?? payload.active_id ?? payload.items[0]?.id
    if (targetId != null) {
      const fresh = payload.items.find((item) => item.id === targetId)
      if (fresh) {
        current.value = fresh
        viewingId.value = fresh.id
      }
    }
  } catch (error) {
    formMessage.value = error instanceof Error ? error.message : '预览单读取失败'
  }
}

async function bootstrap() {
  formMessage.value = ''
  try {
    const result = await bootstrapScenarioRules()
    formMessage.value = result.message
    await loadRules()
    notifyPreviewChanged()
  } catch (error) {
    formMessage.value = error instanceof Error ? error.message : '演练规则补齐失败'
  }
}

async function publishCurrentVersion() {
  publishing.value = true
  formMessage.value = ''
  try {
    const result = await publishVersion(version.value)
    formMessage.value = result.message
    await loadRules()
    notifyPreviewChanged()
  } catch (error) {
    formMessage.value = error instanceof Error ? error.message : '版本发布失败'
  } finally {
    publishing.value = false
  }
}

async function submit() {
  submitting.value = true
  formMessage.value = ''
  lastSubmitMissing.value = false
  try {
    if (bulkDirty.value) applyBulk()
    const payloadColumns = columns.value.map((column) => ({
      field: column.field.trim(),
      required: column.required,
      rule_id: column.ruleRef || null,
    }))
    const result = await createPreview({
      rule_version: version.value.trim(),
      columns: payloadColumns,
      rows: sampleRows.value,
    })
    if (!result.ok || !result.entry) throw new Error(result.message || '预览生成失败')
    current.value = result.entry
    viewingId.value = result.entry.id
    formMessage.value = result.message
    lastSubmitMissing.value = result.entry.field_results.some(
      (field) => !field.ok && field.message.includes('找不到规则'),
    )
    await loadTickets(result.entry.id)
    notifyPreviewChanged()
  } catch (error) {
    formMessage.value = error instanceof Error ? error.message : '预览提交失败'
  } finally {
    submitting.value = false
  }
}

async function bootstrapAndRetry() {
  await bootstrap()
  await submit()
}

async function confirm(id: number) {
  confirming.value = true
  actionError.value = false
  actionMessage.value = ''
  try {
    const result = await confirmPreview(id)
    if (!result.ok) throw new Error(result.message || '确认失败')
    actionMessage.value = result.message
    await loadTickets(id)
    notifyPreviewChanged()
  } catch (error) {
    actionError.value = true
    actionMessage.value = error instanceof Error ? error.message : '确认失败'
    await loadTickets(id)
  } finally {
    confirming.value = false
  }
}

async function activate(id: number) {
  actionError.value = false
  try {
    const result = await activatePreview(id)
    if (!result.ok) throw new Error(result.message)
    actionMessage.value = result.message
    await loadTickets(id)
    notifyPreviewChanged()
  } catch (error) {
    actionError.value = true
    actionMessage.value = error instanceof Error ? error.message : '设置放行依据失败'
  }
}

function view(id: number) {
  viewingId.value = viewingId.value === id ? null : id
  const ticket = tickets.value.find((item) => item.id === id)
  if (ticket) current.value = ticket
}

function expandAndScroll() {
  collapsed.value = false
  window.setTimeout(() => {
    document.querySelector('[data-testid="preview-panel"]')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, 0)
}

function handleExternalChange() {
  void loadRules()
  void loadTickets()
}

onMounted(() => {
  void loadRules()
  void loadTickets()
  window.addEventListener(PREVIEW_CHANGED_EVENT, handleExternalChange)
})

onBeforeUnmount(() => {
  window.removeEventListener(PREVIEW_CHANGED_EVENT, handleExternalChange)
})

defineExpose({ expandAndScroll })
</script>
