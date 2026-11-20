<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { extractSnapshot, saveCompanySnapshot } from '../api'

const router = useRouter()
const ocrLoading = ref(false)
const saveLoading = ref(false)
const error = ref('')
const ocrText = ref('')
const missing = ref([])
const warnings = ref([])
const saved = ref(null)

const form = reactive({
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
})

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

function applyExtraction(data) {
  const fields = data.fields || {}
  for (const key of Object.keys(form)) {
    const value = fields[key]
    if (value !== null && value !== undefined && value !== '') {
      form[key] = value
    }
  }
  if (!form.fetched_at) form.fetched_at = data.suggested_fetched_at || ''
}

async function handleUpload(uploadFile) {
  const file = uploadFile?.raw
  if (!file || ocrLoading.value) return

  ocrLoading.value = true
  error.value = ''
  saved.value = null
  ocrText.value = ''
  missing.value = []
  warnings.value = []

  try {
    const data = await extractSnapshot(file)
    ocrText.value = data.text || ''
    missing.value = data.missing_fields || []
    warnings.value = data.warnings || []
    applyExtraction(data)
    ElMessage.success('已提取候选字段，请核对后保存')
  } catch (err) {
    error.value = detailMessage(err)
  } finally {
    ocrLoading.value = false
  }
}

function requiredMissing() {
  const checks = [
    ['company', '公司全称'],
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

function buildPayload() {
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

async function save() {
  const lacking = requiredMissing()
  if (lacking.length) {
    ElMessage.warning(`请补充：${lacking.join('、')}`)
    return
  }

  saveLoading.value = true
  saved.value = null
  try {
    saved.value = await saveCompanySnapshot(buildPayload())
    ElMessage.success('工商快照已保存')
  } catch (err) {
    ElMessage.error(detailMessage(err))
  } finally {
    saveLoading.value = false
  }
}

function goAnalyze() {
  router.push({ name: 'analyze', query: { company: form.company } })
}
</script>

<template>
  <div class="page">
    <section class="hero">
      <span class="hero-kicker">F-02 / F-03 · 公司快照录入</span>
      <h1 class="hero-title">上传一张工商页面截图，自动提取关键字段。</h1>
      <p class="hero-sub">
        支持企查查、天眼查、国家企业信用信息公示系统的企业详情页截图。
        OCR 在本机运行，图片不会上传到第三方；识别结果需要你核对后才能保存。
      </p>
    </section>

    <section class="card">
      <div class="card-head">
        <h2>上传截图</h2>
        <span class="muted">本地 OCR，约需数秒</span>
      </div>

      <el-upload
        class="snapshot-upload"
        drag
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*"
        :on-change="handleUpload"
      >
        <div class="upload-hint">
          <strong>{{ ocrLoading ? '正在识别…' : '点击或拖拽上传工商页面截图' }}</strong>
          <p>只用于提取公开工商信息，不会把图片发给外部服务。</p>
        </div>
      </el-upload>

      <el-alert
        v-if="error"
        type="error"
        :title="error"
        :closable="false"
        show-icon
        style="margin-top: 14px"
      />
    </section>

    <section v-if="ocrText || missing.length || saved" class="card">
      <div class="card-head">
        <h2>核对并保存</h2>
        <span class="muted">OCR 结果不是最终数据，请逐项确认</span>
      </div>

      <el-alert
        v-for="warning in warnings"
        :key="warning"
        type="warning"
        :title="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 8px"
      />

      <el-alert
        v-if="missing.length"
        type="info"
        :title="`截图中未识别到：${missing.join('、')}，请手工补充。`"
        :closable="false"
        show-icon
        style="margin-bottom: 8px"
      />

      <div class="snapshot-form">
        <p class="form-section field-full">基本信息</p>

        <div class="field field-full">
          <label for="snap-company">企业名称 *</label>
          <el-input id="snap-company" v-model="form.company" placeholder="工商登记全称" />
        </div>

        <div class="field">
          <label for="snap-credit-code">统一社会信用代码</label>
          <el-input id="snap-credit-code" v-model="form.credit_code" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-legal-rep">法定代表人</label>
          <el-input id="snap-legal-rep" v-model="form.legal_representative" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-status">登记状态 *</label>
          <el-input id="snap-status" v-model="form.registration_status" placeholder="存续 / 在业 / 注销" />
        </div>

        <div class="field">
          <label for="snap-founded">成立日期 *</label>
          <el-input id="snap-founded" v-model="form.founded_at" placeholder="YYYY-MM-DD" />
        </div>

        <p class="form-section field-full">资本与代码</p>

        <div class="field">
          <label for="snap-reg-capital">注册资本</label>
          <el-input id="snap-reg-capital" v-model="form.registered_capital" placeholder="如 316.5万元" />
        </div>

        <div class="field">
          <label for="snap-paid-capital">实缴资本</label>
          <el-input id="snap-paid-capital" v-model="form.paid_in_capital" placeholder="如 258.5016万元" />
        </div>

        <div class="field">
          <label for="snap-org-code">组织机构代码</label>
          <el-input id="snap-org-code" v-model="form.organization_code" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-reg-no">工商注册号</label>
          <el-input id="snap-reg-no" v-model="form.business_registration_no" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-taxpayer-id">纳税人识别号</label>
          <el-input id="snap-taxpayer-id" v-model="form.taxpayer_id" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-company-type">企业类型</label>
          <el-input id="snap-company-type" v-model="form.company_type" placeholder="如 有限责任公司" />
        </div>

        <div class="field">
          <label for="snap-business-term">营业期限</label>
          <el-input id="snap-business-term" v-model="form.business_term" placeholder="如 2023-08-03 至无固定期限" />
        </div>

        <div class="field">
          <label for="snap-taxpayer-qual">纳税人资质</label>
          <el-input id="snap-taxpayer-qual" v-model="form.taxpayer_qualification" placeholder="如 一般纳税人" />
        </div>

        <div class="field">
          <label for="snap-insured">参保人数 *</label>
          <el-input-number
            id="snap-insured"
            v-model="form.insured_count"
            :min="0"
            :controls="false"
            placeholder="整数"
          />
        </div>

        <div class="field">
          <label for="snap-approval">核准日期</label>
          <el-input id="snap-approval" v-model="form.approval_date" placeholder="YYYY-MM-DD；VIP 遮挡可留空" />
        </div>

        <p class="form-section field-full">地区与行业</p>

        <div class="field">
          <label for="snap-region">所属地区</label>
          <el-input id="snap-region" v-model="form.region" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-authority">登记机关</label>
          <el-input id="snap-authority" v-model="form.registration_authority" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-industry">国标行业</label>
          <el-input id="snap-industry" v-model="form.industry" placeholder="可选" />
        </div>

        <div class="field">
          <label for="snap-english">英文名</label>
          <el-input id="snap-english" v-model="form.english_name" placeholder="可选" />
        </div>

        <p class="form-section field-full">地址与经营范围</p>

        <div class="field field-full">
          <label for="snap-address">注册地址 *</label>
          <el-input id="snap-address" v-model="form.registered_address" />
        </div>

        <div class="field field-full">
          <label for="snap-mailing">通信地址</label>
          <el-input id="snap-mailing" v-model="form.mailing_address" placeholder="可选" />
        </div>

        <div class="field field-full">
          <label for="snap-scope">经营范围 *</label>
          <el-input
            id="snap-scope"
            v-model="form.business_scope"
            type="textarea"
            :rows="5"
            resize="vertical"
          />
        </div>

        <p class="form-section field-full">来源与附加</p>

        <div class="field">
          <label for="snap-fetched">查询日期 *</label>
          <el-input id="snap-fetched" v-model="form.fetched_at" placeholder="YYYY-MM-DD" />
        </div>

        <div class="field">
          <label for="snap-employee">员工人数（可选）</label>
          <el-input-number
            id="snap-employee"
            v-model="form.employee_count"
            :min="0"
            :controls="false"
            placeholder="整数"
          />
        </div>

        <div class="field">
          <label for="snap-domain">官网域名（可选）</label>
          <el-input id="snap-domain" v-model="form.official_domain" placeholder="example.com" />
        </div>

        <div class="field field-full">
          <label for="snap-source">来源 URL *</label>
          <el-input
            id="snap-source"
            v-model="form.source_url"
            placeholder="https://www.gsxt.gov.cn/ 或企查查详情页 URL"
          />
        </div>

        <div class="field field-full">
          <label for="snap-note">备注</label>
          <el-input id="snap-note" v-model="form.note" placeholder="可选，例如查询人 / 备注" />
        </div>
      </div>

      <div class="input-actions">
        <el-button type="primary" :loading="saveLoading" @click="save">
          保存快照
        </el-button>
        <span class="muted">保存后重新分析，系统会自动使用这条工商信息。</span>
      </div>

      <el-alert
        v-if="saved"
        type="success"
        :closable="false"
        show-icon
        style="margin-top: 14px"
      >
        <template #title>
          {{ saved.action }}成功：{{ saved.company }}
        </template>
        <p>可解锁一致性规则：{{ saved.unlocked_rules.join('、') || '无' }}</p>
        <el-button size="small" type="success" @click="goAnalyze">
          去核验 JD
        </el-button>
      </el-alert>

      <el-collapse v-if="ocrText" style="margin-top: 14px">
        <el-collapse-item title="查看 OCR 原文" name="ocr">
          <pre class="ocr-text">{{ ocrText }}</pre>
        </el-collapse-item>
      </el-collapse>

      <p class="disclaimer">
        这是本地管理入口，部署到公网前必须加鉴权。
        只录入依法公开的信息，不采集身份证号、手机号等非必要个人信息。
      </p>
    </section>
  </div>
</template>
