<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { extractSnapshot, saveCompanySnapshot } from '../api'

const router = useRouter()
const items = ref([])
const expanded = ref([])
const savingAll = ref(false)
let queue = Promise.resolve()

function emptyForm() {
  return {
    company: '',
    credit_code: '',
    legal_representative: '',
    registration_status: '',
    founded_at: '',
    registered_capital: '',
    paid_in_capital: '',
    organization_code: '',
    business_registration_no: '',
    taxpayer_id: '',
    company_type: '',
    business_term: '',
    taxpayer_qualification: '',
    insured_count: null,
    employee_count: null,
    approval_date: '',
    region: '',
    registration_authority: '',
    industry: '',
    english_name: '',
    registered_address: '',
    mailing_address: '',
    business_scope: '',
    official_domain: '',
    source_url: '',
    fetched_at: '',
    note: ''
  }
}

function createItem(file) {
  return {
    uid: file.uid || `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    fileName: file.name,
    status: 'pending',
    error: '',
    ocrText: '',
    missing: [],
    warnings: [],
    showText: false,
    form: reactive(emptyForm()),
    saved: null,
    saving: false
  }
}

function detailMessage(err) {
  const detail = err?.response?.data?.detail
  if (detail && typeof detail === 'object') {
    const parts = [detail.message || '操作失败']
    if (detail.similar?.length) parts.push(`相近主体：${detail.similar.join('、')}`)
    if (detail.errors?.length) parts.push(detail.errors.join('；'))
    return parts.join('；')
  }
  return detail || err?.message || '操作失败，请稍后重试'
}

function applyExtraction(form, data) {
  const fields = data.fields || {}
  for (const key of Object.keys(form)) {
    const value = fields[key]
    if (value !== null && value !== undefined && value !== '') {
      form[key] = value
    }
  }
  if (!form.fetched_at) form.fetched_at = data.suggested_fetched_at || ''
}

function handleUpload(uploadFile) {
  const file = uploadFile?.raw
  if (!file) return

  const item = createItem(file)
  items.value.push(item)

  // OCR 逐张串行执行，避免同时加载多个识别任务把内存打满
  queue = queue.then(() => processItem(item, file)).catch(() => {})
}

async function processItem(item, file) {
  item.status = 'loading'
  item.error = ''
  try {
    const data = await extractSnapshot(file)
    item.ocrText = data.text || ''
    item.missing = data.missing_fields || []
    item.warnings = data.warnings || []
    applyExtraction(item.form, data)
    item.status = 'ready'
    if (!expanded.value.length) expanded.value.push(item.uid)
  } catch (err) {
    item.error = detailMessage(err)
    item.status = 'error'
    if (!expanded.value.includes(item.uid)) expanded.value.push(item.uid)
  }
}

function statusText(item) {
  if (item.saved) return '已保存'
  if (item.status === 'pending') return '排队中'
  if (item.status === 'loading') return '识别中…'
  if (item.status === 'error') return '识别失败'
  return '待核对'
}

function statusType(item) {
  if (item.status === 'error') return 'danger'
  if (item.saved) return 'success'
  if (item.status === 'ready') return 'warning'
  return 'info'
}

function requiredMissing(form) {
  const checks = [
    ['company', '企业名称'],
    ['founded_at', '成立日期'],
    ['registered_address', '注册地址'],
    ['business_scope', '经营范围'],
    ['registration_status', '登记状态'],
    ['source_url', '来源 URL'],
    ['fetched_at', '查询日期']
  ]
  const missingLabels = checks
    .filter(([key]) => !String(form[key] || '').trim())
    .map(([, label]) => label)
  if (form.insured_count === null || form.insured_count === undefined) {
    missingLabels.push('参保人数')
  }
  return missingLabels
}

function buildPayload(form) {
  const payload = { ...form }
  payload.insured_count =
    payload.insured_count === null || payload.insured_count === ''
      ? undefined
      : Number(payload.insured_count)
  payload.employee_count =
    payload.employee_count === null || payload.employee_count === ''
      ? undefined
      : Number(payload.employee_count)
  for (const key of Object.keys(payload)) {
    if (payload[key] === '' || payload[key] === null || payload[key] === undefined) {
      delete payload[key]
    }
  }
  return payload
}

async function saveItem(item) {
  const lacking = requiredMissing(item.form)
  if (lacking.length) {
    ElMessage.warning(`${item.form.company || item.fileName} 请补充：${lacking.join('、')}`)
    if (!expanded.value.includes(item.uid)) expanded.value.push(item.uid)
    return false
  }

  item.saving = true
  item.error = ''
  try {
    item.saved = await saveCompanySnapshot(buildPayload(item.form))
    ElMessage.success(`已保存：${item.saved.company}`)
    return true
  } catch (err) {
    item.error = detailMessage(err)
    return false
  } finally {
    item.saving = false
  }
}

async function saveAll() {
  const pending = items.value.filter((item) => item.status === 'ready' && !item.saved)
  if (!pending.length) {
    ElMessage.info('没有待保存的记录')
    return
  }

  const invalid = pending.filter((item) => requiredMissing(item.form).length)
  if (invalid.length) {
    invalid.forEach((item) => {
      if (!expanded.value.includes(item.uid)) expanded.value.push(item.uid)
    })
    ElMessage.warning(`有 ${invalid.length} 条还没填完整，请先补充`)
    return
  }

  savingAll.value = true
  let done = 0
  for (const item of pending) {
    if (await saveItem(item)) done += 1
  }
  savingAll.value = false
  ElMessage.success(`批量保存完成：${done}/${pending.length} 条`)
}

function removeItem(item) {
  items.value = items.value.filter((row) => row.uid !== item.uid)
  expanded.value = expanded.value.filter((uid) => uid !== item.uid)
}

function goAnalyze(item) {
  router.push({ name: 'analyze', query: { company: item.form.company } })
}

const readyCount = computed(
  () => items.value.filter((item) => item.status === 'ready' && !item.saved).length
)
const savedCount = computed(() => items.value.filter((item) => item.saved).length)
</script>

<template>
  <div class="page">
    <section class="hero">
      <span class="hero-kicker">F-02 / F-03 · 公司快照录入</span>
      <h1 class="hero-title">上传多张工商截图，逐个公司核对后保存。</h1>
      <p class="hero-sub">
        每张截图对应一家公司的工商信息。支持企查查、天眼查、国家企业信用信息公示系统的企业详情页；
        OCR 在本机运行，图片不会上传到第三方，识别结果需要你核对后才能保存。
      </p>
    </section>

    <section class="card">
      <div class="card-head">
        <h2>上传截图</h2>
        <span class="muted">可一次选择多张，逐张识别</span>
      </div>

      <el-upload
        class="snapshot-upload"
        drag
        multiple
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*"
        :on-change="handleUpload"
      >
        <div class="upload-hint">
          <strong>点击或拖拽上传多张工商页面截图</strong>
          <p>一张截图对应一家公司；只用于提取公开工商信息，不会把图片发给外部服务。</p>
        </div>
      </el-upload>

      <p v-if="items.length" class="muted" style="margin-top: 14px">
        已添加 {{ items.length }} 张：{{ readyCount }} 条待核对，{{ savedCount }} 条已保存。
      </p>
    </section>

    <section v-if="items.length" class="card">
      <div class="card-head">
        <h2>核对并保存</h2>
        <el-button type="primary" :loading="savingAll" @click="saveAll">
          保存全部待核对
        </el-button>
      </div>
      <p class="muted" style="margin-top: 0">
        展开每一条逐项核对；OCR 结果不是最终数据，请确认来源 URL 和查询日期后再保存。
      </p>

      <el-collapse v-model="expanded" class="snapshot-list">
        <el-collapse-item v-for="item in items" :key="item.uid" :name="item.uid">
          <template #title>
            <span class="snapshot-item-title">
              <strong>{{ item.form.company || item.fileName }}</strong>
              <el-tag :type="statusType(item)" size="small" effect="plain">
                {{ statusText(item) }}
              </el-tag>
              <span class="muted">{{ item.fileName }}</span>
            </span>
          </template>

          <el-alert
            v-if="item.error"
            type="error"
            :title="item.error"
            :closable="false"
            show-icon
            style="margin-bottom: 8px"
          />

          <el-alert
            v-for="warning in item.warnings"
            :key="warning"
            type="warning"
            :title="warning"
            :closable="false"
            show-icon
            style="margin-bottom: 8px"
          />

          <el-alert
            v-if="item.missing.length"
            type="info"
            :title="`截图中未识别到：${item.missing.join('、')}，请手工补充。`"
            :closable="false"
            show-icon
            style="margin-bottom: 8px"
          />

          <div v-if="item.status === 'ready'" class="snapshot-form">
            <p class="form-section field-full">基本信息</p>

            <div class="field field-full">
              <label>企业名称 *</label>
              <el-input v-model="item.form.company" placeholder="工商登记全称" />
            </div>

            <div class="field">
              <label>统一社会信用代码</label>
              <el-input v-model="item.form.credit_code" placeholder="可选" />
            </div>

            <div class="field">
              <label>法定代表人</label>
              <el-input v-model="item.form.legal_representative" placeholder="可选" />
            </div>

            <div class="field">
              <label>登记状态 *</label>
              <el-input v-model="item.form.registration_status" placeholder="存续 / 在业 / 注销" />
            </div>

            <div class="field">
              <label>成立日期 *</label>
              <el-input v-model="item.form.founded_at" placeholder="YYYY-MM-DD" />
            </div>

            <p class="form-section field-full">资本与代码</p>

            <div class="field">
              <label>注册资本</label>
              <el-input v-model="item.form.registered_capital" placeholder="如 316.5万元" />
            </div>

            <div class="field">
              <label>实缴资本</label>
              <el-input v-model="item.form.paid_in_capital" placeholder="如 258.5016万元" />
            </div>

            <div class="field">
              <label>组织机构代码</label>
              <el-input v-model="item.form.organization_code" placeholder="可选" />
            </div>

            <div class="field">
              <label>工商注册号</label>
              <el-input v-model="item.form.business_registration_no" placeholder="可选" />
            </div>

            <div class="field">
              <label>纳税人识别号</label>
              <el-input v-model="item.form.taxpayer_id" placeholder="可选" />
            </div>

            <div class="field">
              <label>企业类型</label>
              <el-input v-model="item.form.company_type" placeholder="如 有限责任公司" />
            </div>

            <div class="field">
              <label>营业期限</label>
              <el-input v-model="item.form.business_term" placeholder="如 2023-08-03 至无固定期限" />
            </div>

            <div class="field">
              <label>纳税人资质</label>
              <el-input v-model="item.form.taxpayer_qualification" placeholder="如 一般纳税人" />
            </div>

            <div class="field">
              <label>参保人数 *</label>
              <el-input-number
                v-model="item.form.insured_count"
                :min="0"
                :controls="false"
                placeholder="整数"
              />
            </div>

            <div class="field">
              <label>核准日期</label>
              <el-input v-model="item.form.approval_date" placeholder="YYYY-MM-DD；VIP 遮挡可留空" />
            </div>

            <p class="form-section field-full">地区与行业</p>

            <div class="field">
              <label>所属地区</label>
              <el-input v-model="item.form.region" placeholder="可选" />
            </div>

            <div class="field">
              <label>登记机关</label>
              <el-input v-model="item.form.registration_authority" placeholder="可选" />
            </div>

            <div class="field">
              <label>国标行业</label>
              <el-input v-model="item.form.industry" placeholder="可选" />
            </div>

            <div class="field">
              <label>英文名</label>
              <el-input v-model="item.form.english_name" placeholder="可选" />
            </div>

            <p class="form-section field-full">地址与经营范围</p>

            <div class="field field-full">
              <label>注册地址 *</label>
              <el-input v-model="item.form.registered_address" />
            </div>

            <div class="field field-full">
              <label>通信地址</label>
              <el-input v-model="item.form.mailing_address" placeholder="可选" />
            </div>

            <div class="field field-full">
              <label>经营范围 *</label>
              <el-input
                v-model="item.form.business_scope"
                type="textarea"
                :rows="5"
                resize="vertical"
              />
            </div>

            <p class="form-section field-full">来源与附加</p>

            <div class="field">
              <label>查询日期 *</label>
              <el-input v-model="item.form.fetched_at" placeholder="YYYY-MM-DD" />
            </div>

            <div class="field">
              <label>员工人数（可选）</label>
              <el-input-number
                v-model="item.form.employee_count"
                :min="0"
                :controls="false"
                placeholder="整数"
              />
            </div>

            <div class="field">
              <label>官网域名（可选）</label>
              <el-input v-model="item.form.official_domain" placeholder="example.com" />
            </div>

            <div class="field field-full">
              <label>来源 URL *</label>
              <el-input
                v-model="item.form.source_url"
                placeholder="https://www.gsxt.gov.cn/ 或企查查详情页 URL"
              />
            </div>

            <div class="field field-full">
              <label>备注</label>
              <el-input v-model="item.form.note" placeholder="可选，例如查询人 / 备注" />
            </div>
          </div>

          <div class="input-actions">
            <el-button
              type="primary"
              :loading="item.saving"
              :disabled="item.status !== 'ready'"
              @click="saveItem(item)"
            >
              保存这条
            </el-button>
            <el-button @click="removeItem(item)">移除</el-button>
            <el-button
              v-if="item.saved"
              size="small"
              type="success"
              @click="goAnalyze(item)"
            >
              去核验 JD
            </el-button>
            <el-button
              v-if="item.ocrText"
              size="small"
              link
              type="primary"
              @click="item.showText = !item.showText"
            >
              {{ item.showText ? '收起 OCR 原文' : '查看 OCR 原文' }}
            </el-button>
          </div>

          <el-alert
            v-if="item.saved"
            type="success"
            :closable="false"
            show-icon
            style="margin-top: 14px"
          >
            <template #title>
              {{ item.saved.action }}成功：{{ item.saved.company }}
            </template>
            <p>可解锁一致性规则：{{ item.saved.unlocked_rules.join('、') || '无' }}</p>
          </el-alert>

          <pre v-if="item.showText" class="ocr-text" style="margin-top: 14px">{{
            item.ocrText
          }}</pre>
        </el-collapse-item>
      </el-collapse>

      <p class="disclaimer">
        这是本地管理入口，部署到公网前必须加鉴权。
        只录入依法公开的信息，不采集身份证号、手机号等非必要个人信息。
      </p>
    </section>
  </div>
</template>
